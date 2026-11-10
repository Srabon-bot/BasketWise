"""
validate_exports.py
===================
Checks the four JSON files produced by the BasketWise notebook against the
data contracts, and exits non-zero on any mismatch.

Usage
-----
    python scripts/validate_exports.py
    python scripts/validate_exports.py --dir export
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REQUIRED_FILES = ["rules.json", "recommendations.json", "items.json", "stats.json"]
EPSILON = 1e-6


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def load(path: Path):
    if not path.exists():
        fail(f"missing file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path.name}: {exc}")


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def is_probability(value) -> bool:
    return is_number(value) and 0.0 <= float(value) <= 1.0


def check_float_rounding(value, label: str) -> None:
    if not is_number(value):
        fail(f"{label} is not a finite number: {value!r}")
    if abs(round(float(value), 4) - float(value)) > EPSILON:
        fail(f"{label} has more than 4 decimal places: {value!r}")


def validate_rules(payload) -> None:
    if not isinstance(payload, list):
        fail("rules.json must be a JSON array")
    if len(payload) > 500:
        fail(f"rules.json has {len(payload)} rules (max 500)")
    for i, rule in enumerate(payload):
        where = f"rules.json[{i}]"
        if not isinstance(rule, dict):
            fail(f"{where} must be an object")
        if set(rule) != {"antecedents", "consequents", "support", "confidence", "lift"}:
            fail(f"{where} has wrong keys: {sorted(rule)}")
        for side in ("antecedents", "consequents"):
            value = rule[side]
            if not isinstance(value, list) or not value or not all(isinstance(x, str) and x for x in value):
                fail(f"{where}.{side} must be a non-empty list of strings")
            if value != sorted(value):
                fail(f"{where}.{side} must be sorted")
        for metric in ("support", "confidence", "lift"):
            check_float_rounding(rule[metric], f"{where}.{metric}")
        if not is_probability(rule["support"]):
            fail(f"{where}.support must be between 0 and 1")
        if not is_probability(rule["confidence"]):
            fail(f"{where}.confidence must be between 0 and 1")
        if float(rule["lift"]) <= 1.0:
            fail(f"{where}.lift must be > 1")
    # Verify it is sorted by lift descending.
    lifts = [float(rule["lift"]) for rule in payload]
    if lifts != sorted(lifts, reverse=True):
        fail("rules.json must be sorted by lift descending")


def validate_recommendations(payload) -> None:
    if not isinstance(payload, dict) or not payload:
        fail("recommendations.json must be a non-empty object")
    for item, recs in payload.items():
        where = f"recommendations.json[{item!r}]"
        if not isinstance(item, str) or not item:
            fail(f"{where}: key must be a non-empty string")
        if not isinstance(recs, list) or not recs:
            fail(f"{where} must be a non-empty array")
        if len(recs) > 5:
            fail(f"{where} has {len(recs)} recommendations (max 5)")
        seen = set()
        for i, rec in enumerate(recs):
            spot = f"{where}[{i}]"
            if not isinstance(rec, dict):
                fail(f"{spot} must be an object")
            if set(rec) != {"item", "confidence", "lift", "support"}:
                fail(f"{spot} has wrong keys: {sorted(rec)}")
            if not isinstance(rec["item"], str) or not rec["item"]:
                fail(f"{spot}.item must be a non-empty string")
            if rec["item"] == item:
                fail(f"{spot} recommends the item itself")
            if rec["item"] in seen:
                fail(f"{spot} duplicates a recommendation for {item!r}")
            seen.add(rec["item"])
            for metric in ("support", "confidence", "lift"):
                check_float_rounding(rec[metric], f"{spot}.{metric}")
            if not is_probability(rec["support"]):
                fail(f"{spot}.support must be between 0 and 1")
            if not is_probability(rec["confidence"]):
                fail(f"{spot}.confidence must be between 0 and 1")
            if float(rec["lift"]) <= 0:
                fail(f"{spot}.lift must be positive")
        keys = [(-float(r["lift"]), -float(r["confidence"])) for r in recs]
        if keys != sorted(keys):
            fail(f"{where} must be ranked by lift then confidence")


def validate_items(payload, recommendations: dict) -> None:
    if not isinstance(payload, list) or not payload:
        fail("items.json must be a non-empty array")
    seen = set()
    for i, row in enumerate(payload):
        where = f"items.json[{i}]"
        if not isinstance(row, dict) or set(row) != {"item", "count"}:
            fail(f"{where} must have exactly item and count")
        if not isinstance(row["item"], str) or not row["item"]:
            fail(f"{where}.item must be a non-empty string")
        if not isinstance(row["count"], int) or isinstance(row["count"], bool) or row["count"] < 0:
            fail(f"{where}.count must be a non-negative integer")
        if row["item"] in seen:
            fail(f"{where} duplicates item {row['item']!r}")
        seen.add(row["item"])
    if seen != set(recommendations):
        missing = sorted(set(recommendations) - seen)
        extra = sorted(seen - set(recommendations))
        fail(f"items.json must match recommendations.json keys (missing={missing[:5]}, extra={extra[:5]})")
    counts = [row["count"] for row in payload]
    if counts != sorted(counts, reverse=True):
        fail("items.json must be sorted by count descending")


def validate_stats(payload) -> None:
    if not isinstance(payload, dict):
        fail("stats.json must be an object")
    required = {
        "total_transactions", "total_items", "total_members", "date_range",
        "top_items", "monthly_counts", "basket_size_distribution",
        "algorithm_comparison", "parameters", "data_source",
    }
    missing = required - set(payload)
    if missing:
        fail(f"stats.json is missing keys: {sorted(missing)}")

    for key in ("total_transactions", "total_items", "total_members"):
        if not isinstance(payload[key], int) or isinstance(payload[key], bool) or payload[key] < 0:
            fail(f"stats.json.{key} must be a non-negative integer")

    date_range = payload["date_range"]
    if not isinstance(date_range, dict) or set(date_range) != {"start", "end"}:
        fail("stats.json.date_range must have start and end")
    for key in ("start", "end"):
        value = date_range[key]
        if not isinstance(value, str) or len(value) != 10 or value[4] != "-" or value[7] != "-":
            fail(f"stats.json.date_range.{key} must be YYYY-MM-DD")
    if date_range["start"] > date_range["end"]:
        fail("stats.json.date_range.start must not be after end")

    if not isinstance(payload["top_items"], list) or not payload["top_items"]:
        fail("stats.json.top_items must be a non-empty array")
    for i, row in enumerate(payload["top_items"]):
        if not isinstance(row, dict) or set(row) != {"item", "count"}:
            fail(f"stats.json.top_items[{i}] must have item and count")
        if not isinstance(row["item"], str) or not row["item"]:
            fail(f"stats.json.top_items[{i}].item must be a non-empty string")
        if not isinstance(row["count"], int) or row["count"] < 0:
            fail(f"stats.json.top_items[{i}].count must be a non-negative integer")

    if not isinstance(payload["monthly_counts"], list) or not payload["monthly_counts"]:
        fail("stats.json.monthly_counts must be a non-empty array")
    for i, row in enumerate(payload["monthly_counts"]):
        if not isinstance(row, dict) or set(row) != {"month", "count"}:
            fail(f"stats.json.monthly_counts[{i}] must have month and count")
        month = row["month"]
        if not isinstance(month, str) or len(month) != 7 or month[4] != "-":
            fail(f"stats.json.monthly_counts[{i}].month must be YYYY-MM")
        if not isinstance(row["count"], int) or row["count"] < 0:
            fail(f"stats.json.monthly_counts[{i}].count must be a non-negative integer")

    if not isinstance(payload["basket_size_distribution"], list) or not payload["basket_size_distribution"]:
        fail("stats.json.basket_size_distribution must be a non-empty array")
    for i, row in enumerate(payload["basket_size_distribution"]):
        if not isinstance(row, dict) or set(row) != {"size", "count"}:
            fail(f"stats.json.basket_size_distribution[{i}] must have size and count")
        if not isinstance(row["size"], int) or row["size"] < 1:
            fail(f"stats.json.basket_size_distribution[{i}].size must be >= 1")
        if not isinstance(row["count"], int) or row["count"] < 0:
            fail(f"stats.json.basket_size_distribution[{i}].count must be a non-negative integer")

    comparison = payload["algorithm_comparison"]
    if not isinstance(comparison, dict):
        fail("stats.json.algorithm_comparison must be an object")
    for algorithm in ("apriori", "fpgrowth"):
        block = comparison.get(algorithm)
        if not isinstance(block, dict) or set(block) != {"itemsets", "runtime_sec"}:
            fail(f"stats.json.algorithm_comparison.{algorithm} must have itemsets and runtime_sec")
        if not isinstance(block["itemsets"], int) or block["itemsets"] < 0:
            fail(f"stats.json.algorithm_comparison.{algorithm}.itemsets must be a non-negative integer")
        check_float_rounding(block["runtime_sec"], f"stats.json.algorithm_comparison.{algorithm}.runtime_sec")
    if not isinstance(comparison.get("identical_results"), bool):
        fail("stats.json.algorithm_comparison.identical_results must be a boolean")

    parameters = payload["parameters"]
    if not isinstance(parameters, dict) or set(parameters) != {"min_support", "min_confidence"}:
        fail("stats.json.parameters must have min_support and min_confidence")
    for key in ("min_support", "min_confidence"):
        check_float_rounding(parameters[key], f"stats.json.parameters.{key}")
        if not is_probability(parameters[key]):
            fail(f"stats.json.parameters.{key} must be between 0 and 1")

    if payload["data_source"] not in {"real", "synthetic"}:
        fail("stats.json.data_source must be 'real' or 'synthetic'")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate BasketWise JSON exports.")
    parser.add_argument("--dir", default="export", help="Directory containing the JSON files")
    args = parser.parse_args()

    export_dir = Path(args.dir)
    payloads = {name: load(export_dir / name) for name in REQUIRED_FILES}

    validate_rules(payloads["rules.json"])
    validate_recommendations(payloads["recommendations.json"])
    validate_items(payloads["items.json"], payloads["recommendations.json"])
    validate_stats(payloads["stats.json"])

    rules = payloads["rules.json"]
    recs = payloads["recommendations.json"]
    items = payloads["items.json"]
    stats = payloads["stats.json"]
    print("PASS: all four export files match the data contracts.")
    print(f"  rules.json            : {len(rules):,} rules")
    print(f"  recommendations.json  : {len(recs):,} items")
    print(f"  items.json            : {len(items):,} items")
    print(f"  stats.json            : {stats['total_transactions']:,} baskets, "
          f"{stats['total_items']:,} items, source={stats['data_source']}")


if __name__ == "__main__":
    main()
