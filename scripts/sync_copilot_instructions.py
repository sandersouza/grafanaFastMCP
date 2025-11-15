#!/usr/bin/env python3
"""Sync COPILOT.md into the workspace Copilot Chat instructions setting.

This script reads COPILOT.md from the repository root and updates
the workspace `.vscode/settings.json` key
`github.copilot.chat.instructions` with the file contents. Other settings
are preserved. The workspace settings file may contain comments (JSONC);
the script tolerates // and /* */ style comments when reading.

Run from the repo root:
  python3 scripts/sync_copilot_instructions.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path


def _strip_jsonc_comments(text: str) -> str:
    # Remove /* ... */ block comments
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # Remove // line comments
    text = re.sub(r"(^|\n)\s*//.*(?=\n|$)", "\1", text)
    return text


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    copilot_md = repo_root / "COPILOT.md"
    if not copilot_md.exists():
        print(f"COPILOT.md not found at {copilot_md}", file=sys.stderr)
        return 2

    vscode_dir = repo_root / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    settings_path = vscode_dir / "settings.json"

    # Read COPILOT.md
    copilot_text = copilot_md.read_text(encoding="utf-8")

    # Load existing settings (JSONC tolerant)
    settings: dict = {}
    if settings_path.exists():
        raw = settings_path.read_text(encoding="utf-8")
        # Backup the existing settings file before making modifications
        try:
            ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            backup_path = settings_path.with_name(f"{settings_path.name}.{ts}.bak")
            backup_path.write_text(raw, encoding="utf-8")
            print(f"Backed up {settings_path} -> {backup_path}")
        except Exception as exc:  # pragma: no cover - defensive
            print(f"Warning: could not create backup of {settings_path}: {exc}", file=sys.stderr)
        try:
            settings = json.loads(_strip_jsonc_comments(raw))
        except json.JSONDecodeError as exc:
            print(f"Warning: could not parse existing {settings_path}: {exc}", file=sys.stderr)
            # Fallback: perform a textual replacement/insert so we don't lose comments or other keys.
            json_value = json.dumps(copilot_text, ensure_ascii=False)

            def replace_or_insert(raw_text: str, key: str, json_str: str) -> str:
                # Try to find the key occurrence
                key_pattern = re.compile(r'("' + re.escape(key) + r'"\s*:\s*)', re.MULTILINE)
                m = key_pattern.search(raw_text)
                if m:
                    # position after the colon
                    i = m.end()
                    # skip whitespace
                    while i < len(raw_text) and raw_text[i].isspace():
                        i += 1
                    if i < len(raw_text) and raw_text[i] == '"':
                        # Find the end of the JSON string value, handling escapes
                        j = i + 1
                        while j < len(raw_text):
                            if raw_text[j] == '"' and raw_text[j - 1] != '\\':
                                break
                            j += 1
                        if j < len(raw_text):
                            return raw_text[:m.end()] + json_str + raw_text[j + 1:]
                    # Otherwise, try to replace until next top-level comma or closing brace
                    end = i
                    depth = 0
                    while end < len(raw_text):
                        ch = raw_text[end]
                        if ch == '{':
                            depth += 1
                        elif ch == '}':
                            if depth == 0:
                                break
                            depth -= 1
                        elif ch == ',' and depth == 0:
                            break
                        end += 1
                    return raw_text[:m.end()] + json_str + raw_text[end:]
                else:
                    # Insert before final closing brace
                    idx = raw_text.rfind('}')
                    if idx == -1:
                        # Give up and return a simple JSON with only our key
                        return '{\n  "' + key + '": ' + json_str + '\n}\n'
                    before = raw_text[:idx].rstrip()
                    sep = ',' if not before.endswith('{') and not before.endswith(',') else ''
                    insertion = sep + '\n  "' + key + '": ' + json_str + '\n'
                    return raw_text[:idx] + insertion + raw_text[idx:]

            new_raw = replace_or_insert(raw, "github.copilot.chat.instructions", json_value)
            # Write back the text-preserving file
            settings_path.write_text(new_raw, encoding="utf-8")
            print(f"Updated {settings_path} (textual merge) with COPILOT.md content")
            return 0

    # Update the Copilot Chat instructions key (parsed path)
    settings["github.copilot.chat.instructions"] = copilot_text

    # Write back pretty JSON (no comments). Keep UTF-8 and final newline.
    settings_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {settings_path} with COPILOT.md content")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
