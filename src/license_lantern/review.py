"""Explicit SPDX parsing and provenance-preserving attribution review."""

from __future__ import annotations

import copy
import json
from typing import Any

from license_expression import ExpressionError, get_spdx_licensing  # type: ignore[import-untyped]

LICENSING = get_spdx_licensing()


def expression_info(value: str) -> dict[str, Any]:
    if value in ("NOASSERTION", "NONE"):
        return {"original": value, "normalized": value, "valid": value == "NONE", "errors": []}
    try:
        parsed = LICENSING.parse(value, validate=True, strict=True)
        return {
            "original": value,
            "normalized": str(parsed) if parsed is not None else None,
            "valid": parsed is not None,
            "errors": [],
            "unknownSymbols": [],
        }
    except ExpressionError as exc:
        return {
            "original": value,
            "normalized": None,
            "valid": False,
            "errors": [str(exc)],
            "unknownSymbols": [],
        }


def apply_overrides(components: list[dict[str, Any]], overrides: Any) -> list[dict[str, Any]]:
    if not isinstance(overrides, list):
        raise TypeError("overrides must be an array")
    result = copy.deepcopy(components)
    seen = set()
    for index, item in enumerate(overrides):
        fields = (
            "name",
            "version",
            "source",
            "license_declared",
            "evidence",
            "reviewer",
            "reviewed_at",
        )
        if not isinstance(item, dict) or any(
            not isinstance(item.get(k), str) or not item[k].strip() for k in fields
        ):
            raise ValueError(
                f"overrides[{index}] requires text identity, license_declared, evidence, reviewer and reviewed_at"
            )
        from datetime import date

        date.fromisoformat(item["reviewed_at"])
        key = tuple(item[k] for k in ("name", "version", "source"))
        if key in seen:
            raise ValueError("Duplicate override identity")
        seen.add(key)
        matches = [c for c in result if tuple(c[k] for k in ("name", "version", "source")) == key]
        if len(matches) != 1:
            raise ValueError("Override must match exactly one component identity")
        record = matches[0]
        record["override"] = {"original_license": record["license_declared"], **item}
        record["license_declared"] = item["license_declared"]
    for record in result:
        record["expression"] = expression_info(record["license_declared"])
    return result


def inventory_diff(current: list[dict[str, Any]], baseline: Any) -> dict[str, Any]:
    if not isinstance(baseline, dict) or not isinstance(baseline.get("components"), list):
        raise TypeError("baseline must contain a components array")

    def indexed(items: list[Any]) -> dict[str, Any]:
        result = {}
        for item in items:
            if not isinstance(item, dict) or any(
                not isinstance(item.get(k), str)
                for k in ("name", "version", "source", "license_declared")
            ):
                raise TypeError("baseline component identity and license must be strings")
            key = json.dumps([item[k] for k in ("name", "version", "source")])
            if key in result:
                raise ValueError("Duplicate baseline component identity")
            result[key] = item
        return result

    old, new = indexed(baseline["components"]), indexed(current)
    changed = [
        key
        for key in sorted(old.keys() & new.keys())
        if old[key]["license_declared"] != new[key]["license_declared"]
        or old[key].get("override") != new[key].get("override")
    ]
    return {
        "added": [new[k] for k in sorted(new.keys() - old.keys())],
        "removed": [old[k] for k in sorted(old.keys() - new.keys())],
        "changed": [{"before": old[k], "after": new[k]} for k in changed],
    }
