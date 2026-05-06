#!/usr/bin/env python3
"""Check instruction-file hygiene before tokenomics data collection."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


INSTRUCTION_FILES = {
    "AGENTS.md",
    "COPILOT.md",
    "CLAUDE.md",
    "instructions.md",
    "instructions-long.md",
}


def main() -> int:
    args = parse_args()
    files = set(list_files(args.ref))

    if args.mode == "generic":
        leaked = sorted(files.intersection(INSTRUCTION_FILES))
        if leaked:
            print(
                "INVALID: generic branch exposes instruction files: "
                f"{', '.join(leaked)}"
            )
            return 1
        print("OK: generic branch does not expose instruction files")
        return 0

    if "AGENTS.md" not in files:
        print("INVALID: specialized branch does not expose AGENTS.md")
        return 1

    content = read_file(args.ref, "AGENTS.md")
    required_terms = ("grafanaFastMCP", "app/tools", "MCP")
    missing = [term for term in required_terms if term not in content]
    if missing:
        print(f"INVALID: specialized AGENTS.md is missing terms: {', '.join(missing)}")
        return 1

    print("OK: specialized branch exposes grafanaFastMCP AGENTS.md")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("generic", "specialized"))
    parser.add_argument(
        "ref",
        help="Git ref or branch to inspect. Use WORKTREE for local files.",
    )
    return parser.parse_args()


def list_files(ref: str) -> list[str]:
    if ref == "WORKTREE":
        return sorted(path for path in INSTRUCTION_FILES if Path(path).is_file())
    return list_ref_files(ref)


def list_ref_files(ref: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ref],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def read_file(ref: str, path: str) -> str:
    if ref == "WORKTREE":
        return Path(path).read_text(encoding="utf-8")
    return show_ref_file(ref, path)


def show_ref_file(ref: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{ref}:{Path(path).as_posix()}"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return result.stdout


if __name__ == "__main__":
    raise SystemExit(main())
