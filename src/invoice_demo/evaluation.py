from __future__ import annotations

import math
import re
from typing import Any

from invoice_demo.models import AnalysisReport


def _flatten(value: Any, path: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        flattened: dict[str, Any] = {}
        for key, item in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            flattened.update(_flatten(item, child_path))
        return flattened
    if isinstance(value, list):
        flattened = {}
        for index, item in enumerate(value):
            flattened.update(_flatten(item, f"{path}[{index}]"))
        return flattened
    return {path: value}


def _normalize_string(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def values_match(actual: Any, expected: Any, *, numeric_tolerance: float = 0.01) -> bool:
    if actual is None or expected is None:
        return actual is expected
    if isinstance(expected, bool):
        return actual is expected
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return math.isclose(float(actual), float(expected), abs_tol=numeric_tolerance)
    if isinstance(expected, str):
        return _normalize_string(str(actual)) == _normalize_string(expected)
    return actual == expected


def evaluate_report(report: AnalysisReport, ground_truth: dict[str, Any]) -> dict[str, Any]:
    if not report.documents:
        return {
            "matched": 0,
            "expected": len(_flatten(ground_truth.get("fields", {}))),
            "accuracy": 0.0,
            "missing": sorted(_flatten(ground_truth.get("fields", {}))),
            "mismatched": [],
        }

    expected = _flatten(ground_truth.get("fields", {}))
    actual_fields = {name: field.value for name, field in report.documents[0].fields.items()}
    actual = _flatten(actual_fields)
    missing: list[str] = []
    mismatched: list[dict[str, Any]] = []
    matched = 0

    for path, expected_value in expected.items():
        if path not in actual or actual[path] is None:
            missing.append(path)
        elif values_match(actual[path], expected_value):
            matched += 1
        else:
            mismatched.append({"path": path, "expected": expected_value, "actual": actual[path]})

    total = len(expected)
    return {
        "matched": matched,
        "expected": total,
        "accuracy": round(matched / total, 4) if total else 1.0,
        "missing": missing,
        "mismatched": mismatched,
    }
