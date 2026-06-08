"""StashDB Sync — push performer/studio favorites from Stash up to stash-boxes.

Runs as a Stash plugin. On a Performer/Studio update hook (or the "Sync All
Favorites" task) it reads the entity's current `favorite` state and its
`stash_ids`, then calls `favoritePerformer` / `favoriteStudio` on every
configured stash-box whose endpoint matches one of those stash_ids.

One-directional (Stash -> stash-box). Entities with no matching stash_id are
skipped gracefully. Uses the API keys already configured in
Stash -> Settings -> Stash-boxes, so no separate credentials are needed.
"""

import json
import sys

import requests
from stashapi import log
from stashapi.stashapp import StashInterface

PLUGIN_ID = "stashDBSync"

# Per-entity GraphQL against the local Stash server.
FIND_PERFORMER = """
query FindPerformer($id: ID!) {
  findPerformer(id: $id) { id name favorite stash_ids { stash_id endpoint } }
}
"""
FIND_STUDIO = """
query FindStudio($id: ID!) {
  findStudio(id: $id) { id name favorite stash_ids { stash_id endpoint } }
}
"""

# Paging queries for the syncAll backfill task.
FIND_PERFORMERS_PAGE = """
query AllPerformers($filter: FindFilterType!) {
  findPerformers(filter: $filter) {
    count
    performers { id name favorite stash_ids { stash_id endpoint } }
  }
}
"""
FIND_STUDIOS_PAGE = """
query AllStudios($filter: FindFilterType!) {
  findStudios(filter: $filter) {
    count
    studios { id name favorite stash_ids { stash_id endpoint } }
  }
}
"""

# Stash mutations to set favorite locally (used by the reverse pull task).
PERFORMER_UPDATE = """
mutation PerformerUpdate($id: ID!, $favorite: Boolean!) {
  performerUpdate(input: { id: $id, favorite: $favorite }) { id }
}
"""
STUDIO_UPDATE = """
mutation StudioUpdate($id: ID!, $favorite: Boolean!) {
  studioUpdate(input: { id: $id, favorite: $favorite }) { id }
}
"""

# Mutations against the stash-box (StashDB and compatible).
FAVORITE_PERFORMER = """
mutation FavoritePerformer($id: ID!, $favorite: Boolean!) {
  favoritePerformer(id: $id, favorite: $favorite)
}
"""
FAVORITE_STUDIO = """
mutation FavoriteStudio($id: ID!, $favorite: Boolean!) {
  favoriteStudio(id: $id, favorite: $favorite)
}
"""

# Stash-box queries for the reverse pull: who has the current user favorited.
QUERY_FAV_PERFORMERS = """
query FavPerformers($page: Int!, $per_page: Int!) {
  queryPerformers(input: { is_favorite: true, page: $page, per_page: $per_page }) {
    count
    performers { id }
  }
}
"""
QUERY_FAV_STUDIOS = """
query FavStudios($page: Int!, $per_page: Int!) {
  queryStudios(input: { is_favorite: true, page: $page, per_page: $per_page }) {
    count
    studios { id }
  }
}
"""

# Per kind: which Stash query, which stash-box mutation, and its root field name.
KINDS = {
    "performer": {
        "find_one": FIND_PERFORMER,
        "find_one_root": "findPerformer",
        "page_query": FIND_PERFORMERS_PAGE,
        "page_root": "findPerformers",
        "page_items": "performers",
        "mutation": FAVORITE_PERFORMER,
        "stashbox_fav_query": QUERY_FAV_PERFORMERS,
        "stashbox_fav_root": "queryPerformers",
        "stashbox_fav_items": "performers",
        "stash_update": PERFORMER_UPDATE,
    },
    "studio": {
        "find_one": FIND_STUDIO,
        "find_one_root": "findStudio",
        "page_query": FIND_STUDIOS_PAGE,
        "page_root": "findStudios",
        "page_items": "studios",
        "mutation": FAVORITE_STUDIO,
        "stashbox_fav_query": QUERY_FAV_STUDIOS,
        "stashbox_fav_root": "queryStudios",
        "stashbox_fav_items": "studios",
        "stash_update": STUDIO_UPDATE,
    },
}

PAGE_SIZE = 100
REQUEST_TIMEOUT = 30


def parse_bool(raw, default):
    """Coerce a plugin setting (bool or string) into a bool."""
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    return str(raw).lower() not in ("false", "0", "no", "")


def normalize_endpoint(endpoint):
    """Normalize a stash-box endpoint for matching (case + trailing slash)."""
    if not endpoint:
        return ""
    return endpoint.strip().rstrip("/").lower()


def load_stash_boxes(stash):
    """Return {normalized_endpoint: {"endpoint", "api_key", "name"}} from Stash config."""
    config = stash.get_configuration() or {}
    boxes = (config.get("general") or {}).get("stashBoxes") or []
    result = {}
    for box in boxes:
        key = normalize_endpoint(box.get("endpoint"))
        if key:
            result[key] = box
    return result


def stashbox_call(endpoint, api_key, query, variables):
    """POST a GraphQL op to a stash-box. Returns `data` or raises on transport/GraphQL error."""
    resp = requests.post(
        endpoint,
        json={"query": query, "variables": variables},
        headers={"ApiKey": api_key, "Content-Type": "application/json"},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("errors"):
        raise RuntimeError(body["errors"])
    return body.get("data")


def sync_entity(kind, entity, boxes, verbose):
    """Push `entity`'s favorite state to every configured stash-box it is linked to."""
    spec = KINDS[kind]
    name = entity.get("name") or entity.get("id")
    favorite = bool(entity.get("favorite"))
    stash_ids = entity.get("stash_ids") or []

    if not stash_ids:
        if verbose:
            log.info(f"Skip {kind} '{name}': no stash_ids")
        return

    synced = 0
    for sid in stash_ids:
        remote_id = sid.get("stash_id")
        box = boxes.get(normalize_endpoint(sid.get("endpoint")))
        if not box:
            if verbose:
                log.info(f"Skip {kind} '{name}' @ {sid.get('endpoint')}: no matching configured stash-box")
            continue
        if not box.get("api_key"):
            log.warning(f"Skip {kind} '{name}' @ {box.get('name') or box.get('endpoint')}: stash-box has no API key configured")
            continue
        try:
            stashbox_call(box["endpoint"], box["api_key"], spec["mutation"], {"id": remote_id, "favorite": favorite})
            synced += 1
            log.info(f"{'Favorited' if favorite else 'Unfavorited'} {kind} '{name}' on {box.get('name') or box['endpoint']}")
        except Exception as e:
            log.error(f"Failed to sync {kind} '{name}' to {box.get('name') or box['endpoint']}: {e}")
    return synced


def handle_hook(stash, hook_ctx, boxes, sync_performers, sync_studios, verbose):
    entity_id = hook_ctx.get("id")
    hook_type = hook_ctx.get("type", "")
    if not entity_id:
        log.error("No entity id in hook context")
        return

    if hook_type.startswith("Performer"):
        kind = "performer"
        enabled = sync_performers
    elif hook_type.startswith("Studio"):
        kind = "studio"
        enabled = sync_studios
    else:
        return

    if not enabled:
        if verbose:
            log.info(f"Skip {kind} sync: disabled in settings")
        return

    spec = KINDS[kind]
    entity = (stash.call_GQL(spec["find_one"], {"id": entity_id}) or {}).get(spec["find_one_root"])
    if not entity:
        log.error(f"Could not load {kind} {entity_id}")
        return
    sync_entity(kind, entity, boxes, verbose)


def sync_all_kind(stash, kind, boxes, verbose):
    """Backfill: page through all entities of `kind` and sync the favorited ones."""
    spec = KINDS[kind]
    page = 1
    total_synced = 0
    while True:
        result = (stash.call_GQL(
            spec["page_query"],
            {"filter": {"page": page, "per_page": PAGE_SIZE, "sort": "id", "direction": "ASC"}},
        ) or {}).get(spec["page_root"]) or {}
        items = result.get(spec["page_items"]) or []
        if not items:
            break
        for entity in items:
            if entity.get("favorite"):
                total_synced += sync_entity(kind, entity, boxes, verbose) or 0
        if len(items) < PAGE_SIZE:
            break
        page += 1
    log.info(f"Sync All: pushed {total_synced} favorite link(s) for {kind}s")


def fetch_stashbox_favorites(box, spec):
    """Return the set of remote ids the user has favorited on one stash-box."""
    favorited = set()
    page = 1
    while True:
        data = stashbox_call(
            box["endpoint"], box["api_key"], spec["stashbox_fav_query"],
            {"page": page, "per_page": PAGE_SIZE},
        ) or {}
        result = data.get(spec["stashbox_fav_root"]) or {}
        items = result.get(spec["stashbox_fav_items"]) or []
        if not items:
            break
        favorited.update(item["id"] for item in items)
        if len(items) < PAGE_SIZE:
            break
        page += 1
    return favorited


def pull_favorites_kind(stash, kind, boxes, verbose):
    """Reverse sync: mark local entities favorite when favorited upstream (additive only)."""
    spec = KINDS[kind]

    # endpoint(normalized) -> set of remote ids favorited on that box
    favorited_by_endpoint = {}
    for box in boxes.values():
        if not box.get("api_key"):
            continue
        try:
            ids = fetch_stashbox_favorites(box, spec)
        except Exception as e:
            log.error(f"Failed to read {kind} favorites from {box.get('name') or box['endpoint']}: {e}")
            continue
        favorited_by_endpoint[normalize_endpoint(box["endpoint"])] = ids
        log.info(f"{box.get('name') or box['endpoint']}: {len(ids)} favorited {kind}(s) upstream")

    if not any(favorited_by_endpoint.values()):
        return

    updated = 0
    page = 1
    while True:
        result = (stash.call_GQL(
            spec["page_query"],
            {"filter": {"page": page, "per_page": PAGE_SIZE, "sort": "id", "direction": "ASC"}},
        ) or {}).get(spec["page_root"]) or {}
        items = result.get(spec["page_items"]) or []
        if not items:
            break
        for entity in items:
            if entity.get("favorite"):
                continue  # additive: never unfavorite
            matched = any(
                sid.get("stash_id") in favorited_by_endpoint.get(normalize_endpoint(sid.get("endpoint")), ())
                for sid in (entity.get("stash_ids") or [])
            )
            if not matched:
                continue
            name = entity.get("name") or entity.get("id")
            try:
                stash.call_GQL(spec["stash_update"], {"id": entity["id"], "favorite": True})
                updated += 1
                log.info(f"Favorited {kind} '{name}' locally (favorited upstream)")
            except Exception as e:
                log.error(f"Failed to favorite {kind} '{name}' locally: {e}")
        if len(items) < PAGE_SIZE:
            break
        page += 1
    log.info(f"Pull Favorites: marked {updated} {kind}(s) favorite locally")


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        log.error(f"Could not parse stdin: {raw!r}")
        sys.exit(1)

    stash = StashInterface(payload["server_connection"])

    settings = stash.get_configuration().get("plugins", {}).get(PLUGIN_ID, {})
    sync_performers = parse_bool(settings.get("sync_performers"), True)
    sync_studios = parse_bool(settings.get("sync_studios"), True)
    verbose = parse_bool(settings.get("verbose"), False)

    boxes = load_stash_boxes(stash)
    if not boxes:
        log.warning("No stash-boxes configured in Stash; nothing to sync to.")
        return

    args = payload.get("args", {})
    mode = args.get("mode")

    if mode == "syncAll":
        if sync_performers:
            sync_all_kind(stash, "performer", boxes, verbose)
        if sync_studios:
            sync_all_kind(stash, "studio", boxes, verbose)
        return

    if mode == "pullFavorites":
        if sync_performers:
            pull_favorites_kind(stash, "performer", boxes, verbose)
        if sync_studios:
            pull_favorites_kind(stash, "studio", boxes, verbose)
        return

    handle_hook(stash, args.get("hookContext", {}), boxes, sync_performers, sync_studios, verbose)


if __name__ == "__main__":
    main()
