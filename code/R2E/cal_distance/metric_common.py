"""Shared helpers for per-level automatic-summary metric scripts."""

import json
from pathlib import Path


LEVELS = range(1, 10)


def load_level_records(metric_dir: str, metric_name: str, level: int):
    """Read one prepared metric input file and validate its required fields."""
    input_path = Path(metric_dir) / f"{metric_name}_L{level}.json"
    with input_path.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError(f"{input_path} must contain a JSON array")
    for index, record in enumerate(records):
        if not all(key in record for key in ("summary", "reference", "sample_id")):
            raise ValueError(f"{input_path}, record {index}: missing summary/reference/sample_id")
    return input_path, records


def save_level_scores(metric_dir: str, metric_name: str, level: int, records, score_field: str, scores):
    """Write a scored copy without altering the original prepared input file."""
    if len(records) != len(scores):
        raise ValueError("Record and score counts differ")
    output = []
    for record, score in zip(records, scores):
        output.append({
            "summary": record["summary"],
            "reference": record["reference"],
            "sample_id": record["sample_id"],
            score_field: float(score),
        })

    output_path = Path(metric_dir) / f"{metric_name}_L{level}_scored.json"
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)
        file.write("\n")
    return output_path


def save_summary(metric_dir: str, metric_name: str, score_field: str, level_means: dict):
    output_path = Path(metric_dir) / f"{metric_name}_summary.json"
    output = {
        "metric": score_field,
        "levels": {
            f"L{level}": {"mean": float(level_means[level]), "count": 5000}
            for level in LEVELS
        },
    }
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)
        file.write("\n")
    return output_path
