# StashDB Sync

A Stash plugin that keeps your performer and studio favorites in sync with StashDB (and other stash-boxes). There’s some other plugin that does the same, but i don’t think they sync to other stashbox instances or fetch from stashbox instances.

## Use

Once enabled, favoriting a performer or studio in Stash syncs upstream automatically.

Two tasks are available under Settings → Tasks (and in the plugin's settings):

- Sync All Favorites — push all your current Stash favorites up to StashDB. Run once after installing.
- Pull Favorites from StashDB — bring favorites you made on the StashDB website into Stash. Run it whenever you want; it only adds favorites, never removes them. Pulling works with StashDB-compatible boxes; boxes that don't expose favorites over GraphQL (e.g. ThePornDB) are skipped. Pushing favorites upstream still works for every box.

## Settings

- Sync Performers / Sync Studios — turn each on or off.
- Verbose Logging — also log items that were skipped (e.g. not linked to StashDB).