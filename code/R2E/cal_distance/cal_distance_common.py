"""Shared I/O helpers for RQ1 semantic-metric scripts."""

from __future__ import annotations

import json
from pathlib import Path


LEVELS = range(1, 10)


def load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    return data


def subset_ids(sample_file: Path) -> list[object]:
    records = load_json(sample_file)
    ids = [record.get("sample_id") for record in records]
    if any(sample_id is None for sample_id in ids):
        raise ValueError(f"{sample_file} contains a record without sample_id")
    if len(ids) != len(set(ids)):
        raise ValueError(f"{sample_file} contains duplicate sample_id values")
    return ids


def load_level_records(
    input_dir: Path,
    input_prefix: str,
    level: int,
    selected_ids: list[object],
) -> list[dict]:
    path = input_dir / f"{input_prefix}_L{level}.json"
    records = load_json(path)
    by_id = {}
    for record in records:
        sample_id = record.get("sample_id")
        if sample_id in by_id:
            raise ValueError(f"{path} contains duplicate sample_id {sample_id!r}")
        if not all(key in record for key in ("sample_id", "summary", "reference")):
            raise ValueError(f"{path} has a record missing sample_id/summary/reference")
        by_id[sample_id] = record
    missing = [sample_id for sample_id in selected_ids if sample_id not in by_id]
    if missing:
        raise ValueError(f"{path} is missing {len(missing)} selected IDs: {missing[:10]}")
    return [by_id[sample_id] for sample_id in selected_ids]


def save_level_scores(
    output_dir: Path,
    metric_name: str,
    level: int,
    records: list[dict],
    score_field: str,
    scores: list[float],
) -> Path:
    if len(records) != len(scores):
        raise ValueError("Record and score counts differ")
    output_dir.mkdir(parents=True, exist_ok=True)
    output = []
    for record, score in zip(records, scores):
        output.append(
            {
                "sample_id": record["sample_id"],
                "summary": record["summary"],
                "reference": record["reference"],
                score_field: float(score),
            }
        )
    path = output_dir / f"{metric_name}_L{level}_scored.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return path


def save_summary(
    output_dir: Path,
    metric_name: str,
    score_field: str,
    means: dict[int, float],
    count: int,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{metric_name}_summary.json"
    payload = {
        "metric": score_field,
        "levels": {
            f"L{level}": {"mean": float(means[level]), "count": count}
            for level in LEVELS
        },
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return path


def batches(items: list, batch_size: int):
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def method_code(record: dict) -> str:
    code = record.get("code") or record.get("raw_code") or record.get("method_body")
    if code:
        return code
    signature = record.get("method_signature", "")
    body = record.get("method_body_no_sig", "")
    if signature and body:
        return f"{signature} {{\n{body}\n}}"
    return signature or body
