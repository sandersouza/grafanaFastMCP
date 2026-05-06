---
description: "Use for GitHub issue, PR, milestone, branch, and local GitHub mirror work."
name: "GitHub Project Management"
applyTo:
  - ".github/**"
  - "docs/issues/**"
  - "docs/milestones/**"
---
# GitHub Project Management Instructions

## Purpose

Standardize GitHub work for `grafanaFastMCP`, including issues, milestones, branches, pull requests, local documentation, and synchronization with the remote repository.

These instructions apply to:

- new issues;
- feature and bugfix branches;
- umbrella issues and umbrella branches;
- pull request creation and review;
- local project documentation updates;
- the tokenomics experiment workflow in this branch.

## Repository

- Repository: `sandersouza/grafanaFastMCP`
- Main integration branch: `main`
- Tokenomics specialized branch: `test/tokenomics-tests-with-instructions`
- Tokenomics generic branch: `test/tokenomics-tests-without-instructions`

## Tooling

Prefer the GitHub app connector when available for issue, PR, and repository operations. Use `gh` as a fallback or for local workflows that require the GitHub CLI.

When using `gh`, avoid long inline issue or PR bodies. Prepare the body in a Markdown file and publish it with `--body-file`.

## Local Documentation Mirrors

Use the following local documentation areas:

- `.github/docs/issues/` for local issue mirrors and work notes.
- `docs/project-documentation/` for structural and architectural project documentation.
- `tokenomics.experiment/` for token-cost experiment plans, schemas, tasks, fixtures, and scripts.

Issue mirror convention:

```text
.github/docs/issues/
  <milestone-or-area>/
    ISSUE-<number>-<slug>.md
```

Milestone folders may include:

- `README.md` with the milestone objective;
- one file per issue;
- supporting diagrams or checklists when useful.

## Issue Rules

- Every issue must include objective, scope, definition of ready, definition of done, validation plan, and progress checklist.
- Link issues to milestones when a milestone exists.
- Use labels to indicate type and status.
- Keep issue scope small enough for reviewable PRs.
- If an issue depends on another issue, make the dependency explicit.

Recommended labels:

- `type:bug`
- `type:feature`
- `type:docs`
- `type:test`
- `type:refactor`
- `area:mcp`
- `area:grafana`
- `area:tokenomics`
- `status:blocked`
- `status:ready`

## Branch Hygiene

- Run `git fetch --prune` before deciding whether a local or remote branch is current.
- Do not remove orphaned local branches without explicit user confirmation.
- Keep branch names linked to the issue or purpose.
- Follow `AGENTS.md` for tokenomics/runtime separation rules.

Recommended branch names:

```text
feat/<issue-number>-<short-slug>
fix/<issue-number>-<short-slug>
docs/<issue-number>-<short-slug>
test/<issue-number>-<short-slug>
experiment/<short-slug>
```

Protected or special branches:

- `main`: primary integration branch.
- `release/<version>`: release branch when the project uses one.
- `test/tokenomics-tests-with-instructions`: specialized experimental branch.
- `test/tokenomics-tests-without-instructions`: generic comparison branch.

## Tokenomics Branch Rules

Follow `AGENTS.md` and `tokenomics.experiment/experiment-plan.md` for agent behavior, runtime separation, and experiment validity rules.

GitHub-specific requirements:

- Keep `test/tokenomics-tests-with-instructions` and `test/tokenomics-tests-without-instructions` explicit in issue and PR descriptions when the work affects the experiment.
- Record branch hygiene validation before using a run in a report.
- Link tokenomics PRs to the experiment task or issue that owns the measurement.

## Umbrella Issues and Branches

Use an umbrella issue when a feature requires multiple independently reviewable sub-issues.

Umbrella issue requirements:

- clear final outcome;
- list of sub-issues;
- shared validation criteria;
- release or integration target;
- explicit branch strategy.

If an umbrella branch exists, use it as the base for sub-issue branches:

```bash
git fetch --prune
git checkout -B <umbrella-branch> origin/<umbrella-branch>
git checkout -b <sub-issue-branch>
```

PR targeting:

- PRs for sub-issues target the umbrella branch.
- The final umbrella PR targets `main`.

## Pull Request Rules

- Every PR should come from a branch linked to an active issue, except explicitly authorized administrative changes.
- PRs must describe what changed, why it changed, and how it was validated.
- PRs that modify behavior must include tests or justify why tests were not added.
- Documentation-only PRs should still include a review checklist.
- PRs must not include unrelated cleanup.

Suggested PR body:

```markdown
## Summary
- 

## Validation
- [ ] Project validation completed according to `AGENTS.md` and `.github/instructions/good-pratices.instructions.md`

## Scope Notes
- 

Closes #<issue-number>
```

CLI fallback:

```bash
gh pr create \
  --base <main-or-umbrella-branch> \
  --head <issue-branch> \
  --title "<title>" \
  --body-file <body-file.md>
```

## Documentation Rules

Update documentation when changing:

- setup or installation commands;
- runtime flags;
- environment variables;
- MCP transports;
- tool behavior or response schemas;
- testing commands;
- tokenomics experiment procedure.

Documentation targets:

- Root `README.md` for user-facing setup and usage.
- `README-PTBR.md` for the Portuguese README mirror.
- `CHANGELOG.md` for release history.
- `docs/project-documentation/` for project architecture and onboarding.
- `tokenomics.experiment/` for experiment-specific material.

## Status Flow

Use the following issue status model:

- `Backlog`: created but not ready for execution.
- `Ready`: scope is clear and prerequisites are satisfied.
- `In progress`: branch exists and work has started.
- `Blocked`: work is waiting on an external decision or dependency.
- `Review`: PR is open.
- `Done`: PR is merged and follow-up work is tracked or not needed.

## Validation Expectations

Use `AGENTS.md` and `.github/instructions/good-pratices.instructions.md` as the source of truth for default Python validation commands.

Additional validation may be required for:

- transport changes;
- Grafana API response changes;
- packaging changes;
- CI workflow changes;
- tokenomics parser or schema changes.

## Release Notes

When changing `__version__.py`, also update `CHANGELOG.md`.

Release notes should include:

- added behavior;
- changed behavior;
- fixed bugs;
- removed or deprecated behavior;
- security impact;
- performance impact;
- documentation updates;
- build or CI updates;
- tests added or changed.

## Review Discipline

During review:

- prioritize correctness, regressions, security, and missing tests;
- reference files and lines when possible;
- distinguish blocking issues from suggestions;
- keep style-only feedback secondary unless it affects maintainability;
- avoid asking for unrelated refactors.

## Closing Work

Before closing an issue or branch:

- confirm the branch has no unexpected unrelated changes;
- confirm required documentation is updated;
- confirm validation results are recorded;
- confirm any skipped checks are explained;
- link the final PR or commit back to the issue;
- document assumptions that affected the implementation.
