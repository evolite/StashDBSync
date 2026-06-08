# StashDB Sync

A [Stash](https://stashapp.cc) plugin that keeps your **performer and studio favorites**
in sync with StashDB (and other stash-boxes).

- Favorite someone in Stash → they get favorited on StashDB too.
- Favorited them on the StashDB website? Pull those back into Stash with one click.

It uses the stash-box API keys you've already set up in Stash, so there's nothing extra to
configure. A read-only API key is enough.

## Install

1. In Stash, go to **Settings → Plugins → Available Plugins** and click **Add Source**.
2. Add this source URL (Name and Local Path can be anything):
   ```
   https://surging9143.codeberg.page/index.yml
   ```
3. Find **StashDB Sync** under the new source, click **Install**, then turn on
   **Sync Performers** and **Sync Studios** in its settings.

## Use

Once enabled, favoriting a performer or studio in Stash syncs upstream automatically.

Two tasks are available under **Settings → Tasks** (and in the plugin's settings):

- **Sync All Favorites** — push all your current Stash favorites up to StashDB. Run once
  after installing.
- **Pull Favorites from StashDB** — bring favorites you made on the StashDB website into
  Stash. Run it whenever you want; it only adds favorites, never removes them.

## Settings

- **Sync Performers / Sync Studios** — turn each on or off.
- **Verbose Logging** — also log items that were skipped (e.g. not linked to StashDB).
