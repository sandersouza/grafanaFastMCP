# Tokenomics Applicability

This page maps the tokenomics paper analysis to `grafanaFastMCP`. It is project documentation for agent onboarding and experiment design. It is not MCP runtime behavior.

## Applicability Summary

The paper's strongest practical conclusion is that agent cost is dominated by coordination, repeated context loading, review loops, testing loops, and documentation synthesis rather than initial code generation.

For this repository, the most applicable techniques are:

- precise project instructions;
- compact architecture and directory maps;
- narrow task scope;
- deterministic validation with tests and lint before conversational review;
- stable stage labels and normalized run metrics;
- branch hygiene checks to keep specialized and generic experiments separate.

The existing documentation and harness are mostly aligned with this. The main purpose of `docs/project-documentation/` is context compression: it lets agents jump to the relevant module, helper, and test without rediscovering the whole repository.

The first phased comparison showed that specialization can still increase raw input during `DESIGN` and `CODE_COMPLETION`. The mitigation is not more documentation; it is stricter routing:

- `DESIGN` reads only `CONTEXT-PACKS.md`, `SEMANTIC-MAP.md`, one owner file, and one closest test unless blocked.
- `CODE_COMPLETION` starts from `git diff`, touched files, and failing checks, not from architecture docs.
- Deep references remain available, but they are opt-in, not the default path.

## Paper Idea To Repository Mapping

| Paper idea | `grafanaFastMCP` application | Primary artifact | Status |
| --- | --- | --- | --- |
| Baseline vs specialized agent | Compare generic and specialized branches from the same base commit. | `tokenomics.experiment/experiment-plan.md` | Covered |
| Teach the architecture | Document the local runtime architecture and code pattern. | `ARCHITECTURE.md`, `PATTERNS.md` | Covered |
| Explicit specialization | State this project's domain: FastMCP, Grafana APIs, async Python HTTP, MCP transports. | `AGENTS.md`, `BASELINE.md` | Covered |
| Auto-discovery of patterns | Maintain durable maps generated from the current codebase. | `SEMANTIC-MAP.md`, `PATTERNS.md`, `CODE_STYLE.md` | Covered |
| Context compression | Replace broad scans with task-specific compact packages, maps, matrices, and task entrypoints. | `CONTEXT-PACKS.md`, `README.md`, `DIRECTORY-TREE.md`, `TOOL-MODULES.md`, `SEMANTIC-MAP.md` | Covered |
| Worktree or bounded-context isolation | Keep edits localized to one subsystem and matching tests. | `WORKTREE-ISOLATION.md`, `ONBOARDING.md` | Covered |
| Review agent vs static analysis | Prefer `uv run pytest` and `uv run ruff check .` before broad review loops. | `TEST-QUALITY.md` | Covered |
| Long context vs retrieval | Use narrow `rg` searches and targeted file reads instead of loading the repository. | `ONBOARDING.md`, `SEMANTIC-MAP.md` | Covered |
| Incremental memory | Persist stable decisions, maps, contracts, known traps, and experiment results. | `MEMORY.md`, `docs/project-documentation/`, `tokenomics.experiment/` | Covered |

## What Should Not Be Applied Literally

The paper examples mention patterns such as Hexagonal Architecture, Repository Pattern, CQRS, immutable DTOs, stateless services, FastAPI, SQLAlchemy, and React. Those are not the current shape of this repository.

The local project pattern is **Capability-Gated MCP Tool Facade**:

- `app/main.py` and `app/server.py` create and run the MCP application;
- `app/config.py` and `app/context.py` resolve configuration;
- `app/grafana_client.py` centralizes Grafana HTTP access;
- `app/tools/*.py` expose focused Grafana capability groups;
- `app/tools/__init__.py` conditionally registers capability-dependent tools;
- tests live near the subsystem contract they validate.

Do not introduce unrelated architecture vocabulary into runtime code or agent instructions unless the codebase actually adopts that pattern.

## Measurement Expectations

Tokenomics runs should evaluate both token totals and workflow friction:

| Measurement | Why it matters |
| --- | --- |
| `input_tokens` | Captures context and communication tax. |
| `output_tokens` | Captures generation cost. |
| `reasoning_tokens` | Captures hidden reasoning cost when provider data is available. Use `null` when unavailable. |
| `total_tokens` | Supports branch and task comparisons. |
| elapsed time | Captures operational efficiency, not only token volume. |
| human prompt count | Measures coordination failures and clarification loops. |
| files changed | Detects excessive scope. |
| repeated edits per file | Detects correction loops. |
| test and lint loop count | Detects deterministic validation friction. |
| final result | Prevents optimizing token cost at the expense of task success. |

Stage-specific claims should use the stable labels from `tokenomics.experiment/experiment-plan.md`: `DESIGN`, `CODING`, `CODE_COMPLETION`, `CODE_REVIEW`, `TESTING`, and `DOCUMENTATION`.

## Documentation Adequacy Checklist

Before claiming the project documentation is suitable for token-cost reduction, confirm that it answers these questions:

- Where does the requested behavior enter the runtime?
- Which file owns the relevant tool, config, transport, or test behavior?
- What local pattern should a new change follow?
- Which tests are closest to the touched behavior?
- Which files should usually be ignored for this task?
- Is the change runtime behavior, experiment harness work, or documentation-only work?
- Can the task be completed with targeted reads instead of a full repository scan?

The current documentation set answers these questions for the main runtime areas. If a future subsystem is added, update the relevant map before using it as specialized context in tokenomics comparisons.

## Maintenance Rule

Keep project documentation concise and stable. Long narrative documentation can increase the same input-token cost it is meant to reduce. Prefer compact tables, entrypoint maps, decision rules, and validation commands.
