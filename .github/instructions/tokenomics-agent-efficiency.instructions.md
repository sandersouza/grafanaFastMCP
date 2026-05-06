---
description: "Tokenomics-oriented agent rules for compact specialized context, Code Completion control, and static review loops."
name: "Tokenomics Agent Efficiency"
applyTo:
  - "**"
---
# Tokenomics Agent Efficiency

These rules are for specialized tokenomics runs. They reduce input while keeping project context.

## Design Budget

- Read `docs/project-documentation/CONTEXT-PACKS.md`.
- Read `docs/project-documentation/SEMANTIC-MAP.md`.
- Read only the owner file and closest test named by the selected pack.
- Stop when you can name: owner, test target, validation command, risk.
- Do not load the full docs folder during `DESIGN`.

## Code Completion Budget

- Start from `git diff`, touched files, and test/lint output.
- Patch only missing imports, registration, schema wiring, tests, or clear edge cases.
- Do not reopen architecture docs unless a concrete unresolved contract is missing.
- Do not add neighboring cleanup.

## Review Gate

Before another agentic review loop, check: diff, focused Ruff, focused pytest, payload contract, capability gate, bounded-context file list.
