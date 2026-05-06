# Tokenomics Experiment Plan

## Objective

Measure whether project-specific agent instructions reduce token cost and iteration loops during software engineering work in `grafanaFastMCP`.

## Branch Role

The current branch, `test/tokenomics-tests-with-instructions`, is the dedicated instrumentation branch for token-cost reduction work. All techniques intended to reduce token usage should be designed, documented, instrumented, and validated here before being compared against the generic branch or promoted elsewhere.

This branch may contain project-specific instructions, context-compression artifacts, semantic maps, log normalization tools, stage labeling conventions, and other agent workflow optimizations. Those assets are intentional experimental controls, not runtime MCP features.

## Hypothesis

A specialized agent, guided by repository-specific architecture and workflow instructions, will use fewer total tokens and fewer review/test loops than a generic agent doing the same task from the same starting commit.

The expected reduction should appear mostly in:

- input tokens, because less repeated context needs to be rediscovered;
- repeated edits to the same files;
- human prompts needed to correct scope, architecture, or test strategy.

## Experiment V1

Name: **Generic Agent vs Specialized Agent**

Primary data source: real exported agent logs.

Compared branches:

- `test/tokenomics-tests-with-instructions`: specialized branch.
- `test/tokenomics-tests-without-instructions`: generic branch.

The two branches must start from the same base commit before each task. A run is invalid if the generic branch exposes project-specific agent instruction files or if the specialized branch uses instructions for another project.

## SDLC Stage Labels

Every normalized record must use one of these stages:

- `DESIGN`
- `CODING`
- `CODE_COMPLETION`
- `CODE_REVIEW`
- `TESTING`
- `DOCUMENTATION`

If a raw log does not expose a stage, the normalizer may infer it only from an explicit stage marker in the message text, such as `[TESTING]`. Otherwise the record must use `UNKNOWN` and be excluded from stage-specific claims.

## Metrics

Required token metrics:

- `input_tokens`
- `output_tokens`
- `reasoning_tokens`
- `total_tokens`

Required workflow metrics:

- elapsed seconds;
- human prompt count;
- files changed;
- repeated edits per file;
- test and lint loop count;
- final result: `pass`, `fail`, or `invalid`.

`reasoning_tokens` must be recorded as `null` when unavailable. It must not be converted to `0`, because `0` means the provider explicitly reported no reasoning tokens.

## Initial Task Set

The first run uses the tasks in `tasks/generic-vs-specialized.md`:

- a small bug fix in one existing tool module;
- a unit test addition for existing behavior;
- a documentation update.

Each task must use the same prompt on both branches and the same acceptance checks.

## Execution Protocol

1. Reset each branch to the agreed base commit.
2. Confirm branch hygiene:
   - the specialized branch has a valid `AGENTS.md` for `grafanaFastMCP`;
   - the generic branch does not expose `AGENTS.md`, `COPILOT.md`, `CLAUDE.md`, `instructions.md`, or `instructions-long.md` to the agent.
3. Run one task at a time.
4. Export the raw agent log for each run.
5. Normalize logs with `scripts/normalize_agent_logs.py`.
6. Compare totals by branch, task, and stage.
7. Mark a run invalid if instructions are missing, incorrect, or leaked across branches.

## Acceptance Criteria

The experiment is ready to collect data when:

- the plan, schema, fixed tasks, and normalizer exist under `tokenomics.experiment/`;
- the normalizer can aggregate totals by branch, task, and stage;
- missing reasoning tokens remain `null`;
- parser tests pass;
- branch hygiene can identify instruction contamination before data collection.
