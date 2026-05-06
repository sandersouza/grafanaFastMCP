# Context Packs

Pick one row. Read `SEMANTIC-MAP.md`, then the listed owner/test. Avoid full docs scans.

| Task | Owner input | Test input | Validation | Traps |
| --- | --- | --- | --- | --- |
| Runtime tool change | `app/tools/<domain>.py`; `app/tools/__init__.py` only for registration | `tests/test_tools_<domain>.py`; capability tests only if gated | focused pytest, then `uv run ruff check .` | use `get_grafana_config(ctx)`; no direct HTTPX; preserve consolidated list responses |
| Bug fix | owner from `SEMANTIC-MAP.md` | closest regression test | focused pytest, then Ruff | no neighboring refactor; raise on unexpected Grafana payloads |
| Test-only | closest `tests/test_*.py`; runtime owner only for contract | same test file | focused pytest | no real Grafana calls; no runtime change unless a real bug is exposed |
| Docs-only | touched doc plus `README.md` or `TOKENOMICS-APPLICABILITY.md` if linked | link/terminology check | no Python tests unless scripts changed | keep docs compact; do not call experiment controls runtime behavior |
| Tokenomics harness | `tokenomics.experiment/scripts/*`, schema, plan as needed | `tests/test_tokenomics_normalize.py` | `uv run pytest tests/test_tokenomics_normalize.py`; Ruff on scripts/tests | keep phase runner intact; raw and cache-aware metrics stay separate |

## Phase Budgets

- `DESIGN`: one pack, semantic map, owner file, closest test. Stop after owner, test target, validation, risks.
- `CODE_COMPLETION`: start from `git diff` and failing checks. Patch only missing integration details. No broad docs.
- `CODE_REVIEW`: diff, focused Ruff, focused pytest, payload contract, capability gate, bounded-context file list.
