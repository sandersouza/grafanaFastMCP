from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tokenomics.experiment" / "scripts" / "normalize_agent_logs.py"


def load_module():
    spec = importlib.util.spec_from_file_location("normalize_agent_logs", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_normalizes_totals_by_branch_task_and_stage() -> None:
    module = load_module()
    fixture = ROOT / "tests" / "fixtures" / "tokenomics" / "raw-log.json"

    records = module.normalize_inputs([fixture], result="unknown")
    summary = module.summarize(records)

    assert len(records) == 2
    assert summary["total_tokens"] == 185
    assert (
        summary["by_branch"]["test/tokenomics-tests-with-instructions"][
            "total_tokens"
        ]
        == 185
    )
    assert summary["by_task"]["task-001"]["record_count"] == 2
    assert summary["by_stage"]["DESIGN"]["reasoning_tokens"] == 5
    assert summary["by_stage"]["TESTING"]["reasoning_tokens"] is None
    assert summary["by_stage"]["TESTING"]["input_tokens"] == 50


def test_missing_reasoning_tokens_stay_null_not_zero() -> None:
    module = load_module()
    fixture = ROOT / "tests" / "fixtures" / "tokenomics" / "raw-log.json"

    records = module.normalize_inputs([fixture])
    testing_record = records[1]

    assert testing_record.reasoning_tokens is None
    assert testing_record.total_tokens == 60
    summary = module.summarize(records)
    assert summary["reasoning_tokens"] == 5
    assert summary["by_stage"]["TESTING"]["missing_reasoning_records"] == 1
