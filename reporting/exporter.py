"""Export simulation reports to JSON, CSV, and text files."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def export_json(report: dict[str, Any], path: str | Path) -> Path:
    """Export the full report to a JSON file."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def export_csv(analytics: dict[str, Any], path: str | Path) -> Path:
    """Export metric tables to one CSV file."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["section", "key", "value"])
        writer.writeheader()
        for key, value in analytics["general"].items():
            writer.writerow({"section": "general", "key": key, "value": value})
        _write_metric_rows(writer, "stage", analytics["stages"])
        _write_metric_rows(writer, "machine", analytics["machines"])
        _write_metric_rows(writer, "batch", analytics["batches"])
    return output_path


def export_text(summary: str, path: str | Path) -> Path:
    """Export a human-readable summary to a text file."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary, encoding="utf-8")
    return output_path


def export_rows_csv(rows: list[dict[str, Any]], path: str | Path) -> Path:
    """Export homogeneous rows to a CSV file."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames or ["value"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return output_path


def _write_metric_rows(
    writer: csv.DictWriter[str],
    section: str,
    rows: list[dict[str, Any]],
) -> None:
    for index, row in enumerate(rows, start=1):
        row_id = row.get(f"{section}_id", row.get("batch_id", index))
        for key, value in row.items():
            writer.writerow(
                {
                    "section": f"{section}:{row_id}",
                    "key": key,
                    "value": value,
                }
            )
