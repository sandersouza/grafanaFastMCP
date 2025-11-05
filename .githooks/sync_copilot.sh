#!/usr/bin/env sh
# Optional helper git hook script to sync COPILOT.md into workspace settings.
# Not enabled automatically; copy or symlink into .git/hooks/ to use.

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
python3 "$REPO_ROOT/scripts/sync_copilot_instructions.py"
