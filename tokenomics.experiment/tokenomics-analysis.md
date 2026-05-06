# Technical Ideas From the Tokenomics Paper

This document captures the working interpretation used to design the `grafanaFastMCP` tokenomics experiments. It is an analysis document, not runtime MCP behavior.

## 1. The Main Cost Is Not Code Generation

The central insight is that agentic development does not spend most of its token budget on writing code.

| Stage | Typical cost profile |
| --- | --- |
| Coding | Moderate input and output usage |
| Code completion | Often low cost |
| Code review | Very high cost |
| Testing/debugging | High iterative cost |
| Documentation | High input/context cost |

The real cost of agentic development is iterative refinement: reading, re-reading, reviewing, testing, correcting, and re-establishing context.

This matters because the intuitive model is usually:

```text
expensive LLM usage = generating code
```

The paper suggests a more accurate model:

```text
expensive LLM usage = repeatedly coordinating around code
```

## 2. Input Tokens Dominate Output Tokens

The most important metric is not only generated output. A large share of token cost comes from input context: files, previous messages, tool outputs, logs, diffs, test failures, and repeated explanations.

That means token-cost reduction should focus on:

- reducing unnecessary file reads;
- reducing repeated architectural rediscovery;
- keeping task scope narrow;
- summarizing stable project knowledge;
- avoiding repeated review loops;
- making branch and task state explicit.

## 3. Iteration Is the Cost Multiplier

Every loop increases token cost:

- the agent reads context again;
- the agent reinterprets prior decisions;
- the agent edits the same files again;
- tests or lint run again;
- the human provides another prompt;
- the agent must synchronize state again.

The experiment should therefore count file revisits, test/lint loops, human prompts, and final outcome, not only raw tokens.

## 4. Each SDLC Stage Has a Token Signature

Different stages consume tokens differently.

| Stage | Expected token signature |
| --- | --- |
| `DESIGN` | High input usage due to exploration and planning |
| `CODING` | Mixed input/output usage |
| `CODE_COMPLETION` | Usually lower output-oriented usage |
| `CODE_REVIEW` | High input usage from diffs, context, and comments |
| `TESTING` | Iterative input spikes from failures and logs |
| `DOCUMENTATION` | High input usage from project context and consistency checks |

This is why the experiment uses explicit stage labels.

## 5. Agents Lose More Cost To Coordination Than Intelligence

The bottleneck is often architectural rather than cognitive. Current agents waste context because they lack cheap, persistent coordination primitives.

The expensive parts are:

- coordination;
- repetition;
- context transfer;
- state synchronization;
- branch and task ambiguity;
- repeated discovery of project structure.

Specialized project instructions, architecture summaries, directory maps, and stable task protocols are expected to reduce this communication tax.

## Practical Implication For Codex/Copilot

The useful hypothesis is:

```text
Specialized instructions reduce communication tax.
```

For this repository, that means a specialized branch should provide:

- an accurate `AGENTS.md`;
- project architecture documentation;
- code pattern documentation;
- directory and module maps;
- fixed experiment tasks;
- log normalization tools;
- branch hygiene checks.

## Experiment 1: Generic Agent vs Specialized Agent

### Setup

Compare two branches:

- Branch A: `test/tokenomics-tests-without-instructions`
- Branch B: `test/tokenomics-tests-with-instructions`

Branch A should not expose project-specific instructions. Branch B should expose correct `grafanaFastMCP` instructions and project documentation.

### Tasks

Use the same fixed tasks on both branches:

- a small bug fix;
- a unit test for existing behavior;
- a documentation update.

### Metrics

Track:

- input tokens;
- output tokens;
- reasoning tokens when available;
- total tokens;
- elapsed time;
- number of human prompts;
- number of changed files;
- number of edits per file;
- test and lint loops;
- final outcome.

### Expected Result

| Metric | Generic branch | Specialized branch |
| --- | --- | --- |
| Input tokens | Higher | Lower |
| Total tokens | Higher | Lower |
| Human prompts | More | Fewer |
| File revisits | More | Fewer |
| Consistency | Lower | Higher |

The result is valid only if both branches start from the same base commit and the generic branch is not contaminated by specialized instructions.

## Experiment 2: Project Rule Compression

Create a compact rules document with only the highest-value project rules:

- language and tooling;
- runtime entrypoint;
- tool registration pattern;
- response envelope expectations;
- test commands;
- documentation update rules.

Measure whether the compact rules reduce exploration time and input tokens compared with full documentation.

## Experiment 3: Specialist Persona

Add a focused specialist instruction:

```text
You are a senior specialist in FastMCP, Grafana APIs, Python async HTTP clients, and MCP transport compatibility.
```

Expected effect:

- less random exploration;
- fewer inconsistent edits;
- faster identification of relevant modules.

This must be tested carefully because a persona alone may not outperform concrete project maps.

## Experiment 4: Self-Generated Project Map

Ask the agent to generate a durable project map, then require future agents to use that map before coding.

Measure whether this reduces:

- future communication;
- redundant analysis;
- repeated directory scans;
- repeated architectural explanations.

This is the purpose of `docs/project-documentation/`.

## Experiment 5: Force An Architectural Pattern

If a project does not clearly follow a known pattern, derive a local pattern from the current codebase.

For this repository, the pattern is:

```text
Capability-Gated MCP Tool Facade
```

Expected effect:

- more consistent edits;
- fewer cross-module surprises;
- less unnecessary refactoring;
- faster onboarding for agents.

## Experiment 6: Context Compression

Because input tokens dominate cost, context compression may have a large effect.

Examples:

- short architecture summaries;
- directory maps;
- tool-to-file maps;
- code pattern tables;
- stage-specific task templates;
- concise branch rules.

Expected impact:

- less full-project scanning;
- fewer repeated file reads;
- lower input-token totals.

## Experiment 7: Narrow Context Scope

Constrain each task to an explicit scope:

- one feature area;
- one tool module;
- one test file;
- one documentation page;
- one worktree.

Expected effect:

- less unrelated reading;
- lower risk of broad refactors;
- fewer review comments;
- lower total cost.

## Experiment 8: Hybrid Review Pipeline

Code review is expected to be one of the highest token consumers.

Compare:

- conversational review by an agent;
- a hybrid pipeline that uses deterministic lint/test checks first and reserves the agent for semantic review.

Expected effect:

- lower review token cost;
- fewer repeated review loops;
- clearer distinction between mechanical and semantic problems.

## Experiment 9: Symbolic Map Instead Of Raw Context

Use a compact map of relevant symbols instead of repeatedly loading large files.

Examples:

- module responsibility table;
- function-to-tool table;
- environment variable table;
- response schema table.

Hypothesis:

```text
less raw context can improve efficiency when the substitute map is accurate.
```

## Experiment 10: Incremental Memory

Maintain durable project memory:

- decisions made;
- patterns discovered;
- rejected approaches;
- module ownership;
- experiment results.

Expected effect:

- fewer repeated decisions;
- cheaper future prompts;
- faster continuation after context compaction.

## Additional Instruction Ideas

High-value instructions for token reduction:

1. Read only files directly related to the task.
2. Avoid full project scans unless the task requires them.
3. Never refactor outside the requested scope without explicit need.
4. Keep changes localized.
5. Stop and reassess if the same file is edited more than three times.
6. Maintain a concise architectural memory.
7. Prefer localized patches over complete rewrites.
8. Use deterministic tools before asking the LLM to reason over noisy output.

## Technical Conclusion

The future of cost-efficient agents is not only better code generation. It is better coordination:

- better context selection;
- better project memory;
- better task scoping;
- better deterministic validation;
- better handoff between human, agent, and tools.

The most valuable first experiment for this repository is **Generic Agent vs Specialized Agent**, using real agent logs and fixed tasks across the two tokenomics branches.
