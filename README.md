# StashDB Sync

A [Stash](https://stashapp.cc) plugin that keeps your **performer and studio favorites**
in sync with StashDB (and other stash-boxes).

- Favorite someone in Stash → they get favorited on StashDB too.
- Favorited them on the StashDB website? Pull those back into Stash with one click.

It uses the stash-box API keys you've already set up in Stash, so there's nothing extra to
configure. A read-only API key is enough.

## Install

1. Symlink (or copy) this folder into your Stash `plugins` directory:
   ```
   ln -s /path/to/StashDBSync ~/.stash/plugins/StashDBSync
   ```
2. In Stash, go to **Settings → Plugins** and click **Reload Plugins**.
3. Open **StashDB Sync** in that list and turn on **Sync Performers** and **Sync Studios**.

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
