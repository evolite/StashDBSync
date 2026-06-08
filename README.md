# StashDB Sync

A [Stash](https://stashapp.cc) plugin that pushes **performer and studio favorites**
from your local Stash up to the stash-boxes they're linked to (StashDB, ThePornDB,
FansDB, etc.).

Favorite a performer or studio in Stash → it gets favorited on the matching stash-box.
Unfavorite it → it gets unfavorited upstream. The sync is one-directional
(Stash → stash-box) and idempotent.

## How it works

On every `Performer.Update.Post` / `Studio.Update.Post` hook, the plugin:

1. Reads the entity's current `favorite` state and its `stash_ids`.
2. For each `stash_id`, finds the configured stash-box with a matching `endpoint`.
3. Calls `favoritePerformer` / `favoriteStudio` on that box with the current state.

It uses the API keys you've already configured under
**Stash → Settings → Metadata Providers → Stash-boxes**, so there's nothing extra to
set up. Entities with no `stash_ids` (or no matching configured box) are skipped
silently — enable **Verbose Logging** to see those skips.

> A read-only (READ role) stash-box API key is sufficient — favorites are per-user data,
> not database edits.

## Install

1. Copy or symlink this directory into your Stash `plugins` folder, e.g.:
   ```
   ln -s /path/to/StashDBSync ~/.stash/plugins/StashDBSync
   ```
2. In Stash: **Settings → Plugins → Reload Plugins**.
3. Configure under **Settings → Plugins → StashDB Sync**:
   - **Sync Performers** / **Sync Studios** — enable each entity type.
   - **Verbose Logging** — log skipped entities too.

Requires the Python deps in `requirements.txt` (`stashapp-tools`, `requests`), which are
present in the official Stash Docker image.

## Tasks

- **Sync All Favorites** — backfill: pushes the current favorite state of every linked
  performer and studio upstream. Run it once after install, then the hooks keep things
  in sync.
- **Pull Favorites from StashDB** — reverse sync: marks local performers/studios as
  favorite when you've favorited them on a stash-box. This is **additive** — it only sets
  favorites, never removes them, so it won't fight the forward push or undo local state.
  Hooks can't fire on stash-box-side changes, so run this manually (or via Stash's
  scheduled tasks) whenever you want to pull in favorites made on the StashDB website.

Together the hook (Stash → stash-box) and this task (stash-box → Stash) make favorites
two-way.

## Notes

- No feedback loop: writing to a stash-box never triggers a local Stash hook.
- Multiple stash-boxes per entity are all synced.
