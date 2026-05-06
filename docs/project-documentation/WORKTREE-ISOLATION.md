# Worktree Isolation

This guide translates the tokenomics worktree/bounded-context experiment into concrete repository rules. It is workflow documentation, not MCP runtime behavior.

## Isolation Goal

Keep each agent task inside the smallest subsystem that can satisfy the request. This reduces context scanning, unrelated file churn, and review loops.

## Bounded Contexts

| Context | Main edit area | Matching validation |
| --- | --- | --- |
| Tool domain | `app/tools/<domain>.py` | `tests/test_tools_<domain>.py` |
| Capability registration | `app/tools/__init__.py`, `app/tools/availability.py` | `tests/test_tool_availability.py`, `tests/test_tools_registration.py` |
| Config and auth | `app/config.py`, `app/context.py`, `env.example` | `tests/test_config*.py`, `tests/test_context.py` |
| Transport and app factory | `app/server.py`, `app/patches.py` | `tests/test_server.py`, `tests/test_patches*.py` |
| CLI startup | `app/main.py` | `tests/test_main*.py` |
| MCP shim | `mcp/server/` | `tests/test_fastmcp*.py`, `tests/test_streamable_http_accept.py` |
| Tokenomics harness | `tokenomics.experiment/` | `tests/test_tokenomics_normalize.py` |
| Project documentation | `docs/project-documentation/` | Link checks or targeted markdown review |

## Worktree Rules

- Use a separate branch or worktree for comparison runs when measuring tokenomics outcomes.
- Start generic and specialized runs from the same base commit.
- Keep instruction artifacts out of `test/tokenomics-tests-without-instructions`.
- Do not mix runtime behavior changes and experiment harness changes unless the task explicitly asks for both.
- If a task crosses more than one bounded context, document why before expanding the edit scope.

## Scope Checks

Before editing, identify:

- the owning context;
- the primary file;
- the closest test;
- any capability gate or response contract involved.

After editing, check file churn. Unexpected edits outside the owning context should be justified or removed before comparison data is collected.
