#!/usr/bin/env python3
"""Normalize exported agent token logs for the tokenomics experiment."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


STAGES = {
    "DESIGN",
    "CODING",
    "CODE_COMPLETION",
    "CODE_REVIEW",
    "TESTING",
    "DOCUMENTATION",
    "UNKNOWN",
}
STAGE_PATTERN = re.compile(
    r"\b("
    r"DESIGN|CODING|CODE_COMPLETION|CODE REVIEW|CODE_REVIEW|TESTING|"
    r"DOCUMENTATION"
    r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NormalizedRecord:
    run_id: str
    branch: str
    task_id: str
    stage: str
    message_index: int
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int | None
    total_tokens: int
    elapsed_seconds: float | None
    human_prompt_count: int
    files_changed: list[str]
    repeated_file_edits: int
    test_loop_count: int
    lint_loop_count: int
    result: str
    source_file: str


def main() -> int:
    args = parse_args()
    records = normalize_inputs(
        inputs=args.input,
        branch=args.branch,
        task_id=args.task_id,
        run_id=args.run_id,
        result=args.result,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    normalized = [asdict(record) for record in records]
    write_json(args.output_dir / "normalized.json", normalized)
    write_csv(args.output_dir / "normalized.csv", records)
    write_json(args.output_dir / "summary.json", summarize(records))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        type=Path,
        help="Raw log file or directory. May be passed multiple times.",
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--branch", default="", help="Branch name fallback.")
    parser.add_argument("--task-id", default="", help="Task id fallback.")
    parser.add_argument("--run-id", default="", help="Run id fallback.")
    parser.add_argument(
        "--result",
        choices=("pass", "fail", "invalid", "unknown"),
        default="unknown",
        help="Result fallback when the raw log does not include one.",
    )
    return parser.parse_args()


def normalize_inputs(
    inputs: list[Path],
    branch: str = "",
    task_id: str = "",
    run_id: str = "",
    result: str = "unknown",
) -> list[NormalizedRecord]:
    records: list[NormalizedRecord] = []
    for path in collect_files(inputs):
        events = read_events(path)
        for index, event in enumerate(events):
            records.append(
                normalize_event(
                    event=event,
                    source_file=str(path),
                    message_index=index,
                    branch=branch,
                    task_id=task_id,
                    run_id=run_id,
                    result=result,
                )
            )
    return records


def collect_files(inputs: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in inputs:
        if path.is_dir():
            files.extend(
                candidate
                for candidate in sorted(path.rglob("*"))
                if candidate.is_file()
                and candidate.suffix.lower() in {".json", ".jsonl", ".ndjson"}
            )
        else:
            files.append(path)
    return files


def read_events(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    data = json.loads(text)
    if isinstance(data, list):
        return [ensure_mapping(item) for item in data]
    if isinstance(data, dict):
        for key in ("records", "messages", "events", "calls"):
            value = data.get(key)
            if isinstance(value, list):
                return [ensure_mapping(item) for item in value]
        return [data]
    raise ValueError(f"Unsupported log root in {path}: {type(data).__name__}")


def ensure_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Expected object event, got {type(value).__name__}")
    return value


def normalize_event(
    event: dict[str, Any],
    source_file: str,
    message_index: int,
    branch: str,
    task_id: str,
    run_id: str,
    result: str,
) -> NormalizedRecord:
    usage = mapping_at(event, "usage")
    input_tokens = int_from(event, usage, "input_tokens", "prompt_tokens", default=0)
    output_tokens = int_from(
        event,
        usage,
        "output_tokens",
        "completion_tokens",
        default=0,
    )
    reasoning_tokens = reasoning_from(event, usage)
    total_tokens = int_from(event, usage, "total_tokens", default=-1)
    if total_tokens < 0:
        total_tokens = input_tokens + output_tokens + (reasoning_tokens or 0)

    files_changed = list_from(event, "files_changed", "changed_files")

    return NormalizedRecord(
        run_id=str(
            first_value(
                event,
                "run_id",
                "run",
                default=run_id or Path(source_file).stem,
            )
        ),
        branch=str(first_value(event, "branch", default=branch or "unknown")),
        task_id=str(
            first_value(event, "task_id", "task", default=task_id or "unknown")
        ),
        stage=stage_from(event),
        message_index=int(
            first_value(event, "message_index", "index", default=message_index)
        ),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens,
        total_tokens=total_tokens,
        elapsed_seconds=float_or_none(
            first_value(event, "elapsed_seconds", "duration_seconds", default=None)
        ),
        human_prompt_count=int(
            first_value(event, "human_prompt_count", "human_prompts", default=0)
        ),
        files_changed=files_changed,
        repeated_file_edits=int(
            first_value(
                event,
                "repeated_file_edits",
                default=count_repeated(files_changed),
            )
        ),
        test_loop_count=int(
            first_value(event, "test_loop_count", "test_loops", default=0)
        ),
        lint_loop_count=int(
            first_value(event, "lint_loop_count", "lint_loops", default=0)
        ),
        result=str(first_value(event, "result", default=result)),
        source_file=source_file,
    )


def mapping_at(event: dict[str, Any], key: str) -> dict[str, Any]:
    value = event.get(key)
    return value if isinstance(value, dict) else {}


def int_from(
    event: dict[str, Any],
    nested: dict[str, Any],
    *keys: str,
    default: int,
) -> int:
    value = first_value(event, *keys, default=None)
    if value is None:
        value = first_value(nested, *keys, default=default)
    if value is None:
        return default
    return int(value)


def reasoning_from(event: dict[str, Any], usage: dict[str, Any]) -> int | None:
    value = first_value(event, "reasoning_tokens", default=None)
    if value is None:
        value = first_value(usage, "reasoning_tokens", default=None)
    if value is None:
        details = mapping_at(usage, "output_tokens_details")
        value = first_value(details, "reasoning_tokens", default=None)
    if value is None:
        details = mapping_at(usage, "completion_tokens_details")
        value = first_value(details, "reasoning_tokens", default=None)
    return None if value is None else int(value)


def first_value(mapping: dict[str, Any], *keys: str, default: Any) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return default


def list_from(event: dict[str, Any], *keys: str) -> list[str]:
    value = first_value(event, *keys, default=[])
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def count_repeated(paths: list[str]) -> int:
    return sum(count - 1 for count in Counter(paths).values() if count > 1)


def float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def stage_from(event: dict[str, Any]) -> str:
    raw_stage = first_value(event, "stage", "phase", default="")
    stage = normalize_stage(str(raw_stage))
    if stage != "UNKNOWN":
        return stage

    text = " ".join(
        str(value)
        for key, value in event.items()
        if key in {"message", "content", "prompt", "response"}
        and isinstance(value, str)
    )
    match = STAGE_PATTERN.search(text)
    if not match:
        return "UNKNOWN"
    return normalize_stage(match.group(1))


def normalize_stage(value: str) -> str:
    stage = value.strip().upper().replace(" ", "_").replace("-", "_")
    return stage if stage in STAGES else "UNKNOWN"


def summarize(records: list[NormalizedRecord]) -> dict[str, Any]:
    totals: dict[str, Any] = {
        "record_count": len(records),
        "total_tokens": sum(record.total_tokens for record in records),
        "input_tokens": sum(record.input_tokens for record in records),
        "output_tokens": sum(record.output_tokens for record in records),
        "reasoning_tokens": nullable_sum(record.reasoning_tokens for record in records),
        "by_branch": defaultdict(counter_dict),
        "by_task": defaultdict(counter_dict),
        "by_stage": defaultdict(counter_dict),
    }
    for record in records:
        add_record(totals["by_branch"][record.branch], record)
        add_record(totals["by_task"][record.task_id], record)
        add_record(totals["by_stage"][record.stage], record)

    for group_name in ("by_branch", "by_task", "by_stage"):
        for bucket in totals[group_name].values():
            if bucket["missing_reasoning_records"] == bucket["record_count"]:
                bucket["reasoning_tokens"] = None

    return json.loads(json.dumps(totals))


def counter_dict() -> dict[str, Any]:
    return {
        "record_count": 0,
        "total_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "missing_reasoning_records": 0,
        "human_prompt_count": 0,
        "repeated_file_edits": 0,
        "test_loop_count": 0,
        "lint_loop_count": 0,
    }


def add_record(bucket: dict[str, Any], record: NormalizedRecord) -> None:
    bucket["record_count"] += 1
    bucket["total_tokens"] += record.total_tokens
    bucket["input_tokens"] += record.input_tokens
    bucket["output_tokens"] += record.output_tokens
    if record.reasoning_tokens is None:
        bucket["missing_reasoning_records"] += 1
    else:
        bucket["reasoning_tokens"] += record.reasoning_tokens
    bucket["human_prompt_count"] += record.human_prompt_count
    bucket["repeated_file_edits"] += record.repeated_file_edits
    bucket["test_loop_count"] += record.test_loop_count
    bucket["lint_loop_count"] += record.lint_loop_count


def nullable_sum(values: Any) -> int | None:
    seen = False
    total = 0
    for value in values:
        if value is None:
            continue
        seen = True
        total += value
    return total if seen else None


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, records: list[NormalizedRecord]) -> None:
    fieldnames = list(NormalizedRecord.__dataclass_fields__)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = asdict(record)
            row["files_changed"] = json.dumps(row["files_changed"])
            writer.writerow(row)


if __name__ == "__main__":
    raise SystemExit(main())
