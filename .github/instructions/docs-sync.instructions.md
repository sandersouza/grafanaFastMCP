---
description: "Use to keep documentation, handoff notes, context files, and local mirrors synchronized with code and GitHub."
name: "grafanaFastMCP Docs Sync"
applyTo:
  - "docs/**"
  - "AGENTS.md"
  - "CONTEXT.md"
---
# grafanaFastMCP Docs Sync

## General Rule

- Relevant code changes must update the minimum applicable documentation.
- Batch documentation updates at a stable checkpoint when doing so reduces noise without losing traceability.

## Handoff and Context

- Keep `docs/handoff/<branch>.md` as persistent branch context when a handoff file exists or is required.
- Keep `CONTEXT.md` pointing to the active handoff when the project uses that file.
- Record technical decisions with context, trade-offs, impact, and verifiable risks or next steps.

## Issues and Milestones

- Follow `github-project-management.md` for local mirror structure.
- Create or update `docs/issues/**` or `docs/milestones/**` in the same cycle as the relevant remote change when those mirrors are being used.

## Quality

- Avoid redundant text and excessive historical detail.
- Reference consulted files, classes, or modules when they materially influence the implementation.
- Reflect guardrail or workflow changes in `AGENTS.md` only when they change the canonical rule for humans or agents.
