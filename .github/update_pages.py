import os
import re

version = os.environ['VERSION']
hash_   = os.environ['HASH']
date    = os.environ['DATE']
url     = os.environ['URL']

path = "/tmp/pages/index.yml"
with open(path) as f:
    content = f.read()

entry = (
    "- id: stashDBSync\n"
    "  name: StashDB Sync\n"
    "  metadata:\n"
    "    description: Syncs performer and studio favorites between Stash and StashDB\n"
    f"  version: {version}\n"
    f'  date: "{date}"\n'
    f"  path: {url}\n"
    f"  sha256: {hash_}"
)

if "id: stashDBSync" in content:
    content = re.sub(
        r'- id: stashDBSync\b.*?(?=\n- |\Z)',
        entry,
        content, flags=re.DOTALL
    )
else:
    content = content.rstrip('\n') + '\n' + entry + '\n'

with open(path, "w") as f:
    f.write(content)
