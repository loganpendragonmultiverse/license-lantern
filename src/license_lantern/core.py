from __future__ import annotations

import hashlib
import json
import re
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from .review import apply_overrides, inventory_diff


@dataclass(frozen=True, order=True)
class Component:
    name: str
    version: str
    license_declared: str
    source: str


def _mapping(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _license(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, list):
        names = [_license(item) for item in value]
        return " AND ".join(f"({name})" for name in names) or "NOASSERTION"
    data = _mapping(value)
    return str(data.get("expression") or data.get("id") or data.get("name") or "NOASSERTION")


def _dependency_name(specification: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9_.-]+)", specification)
    return match.group(1) if match else specification.strip()


def read_components(path: Path) -> list[Component]:
    name = path.name.lower()
    if name == "package-lock.json":
        data = _mapping(json.loads(path.read_text(encoding="utf-8")))
        components = []
        for location, raw in _mapping(data.get("packages")).items():
            if not location:
                continue
            item = _mapping(raw)
            package_name = str(item.get("name") or location.rsplit("node_modules/", 1)[-1])
            components.append(
                Component(
                    package_name,
                    str(item.get("version", "UNKNOWN")),
                    _license(item.get("license")),
                    path.name,
                )
            )
        return components
    if name == "pyproject.toml":
        data = _mapping(tomllib.loads(path.read_text(encoding="utf-8")))
        dependencies = _mapping(data.get("project")).get("dependencies", [])
        return [
            Component(_dependency_name(str(item)), "UNKNOWN", "NOASSERTION", path.name)
            for item in dependencies
            if isinstance(item, str)
        ]
    if name.endswith("requirements.txt") or name == "requirements.txt":
        components = []
        for line in path.read_text(encoding="utf-8").splitlines():
            clean = line.split("#", 1)[0].strip()
            if not clean or clean.startswith("-"):
                continue
            version = clean.split("==", 1)[1] if "==" in clean else "UNKNOWN"
            components.append(Component(_dependency_name(clean), version, "NOASSERTION", path.name))
        return components
    data = _mapping(json.loads(path.read_text(encoding="utf-8")))
    if data.get("bomFormat") == "CycloneDX":
        components = []
        pending = list(data.get("components", []))
        while pending:
            raw = pending.pop(0)
            item = _mapping(raw)
            nested = item.get("components", [])
            if not isinstance(nested, list):
                raise TypeError("CycloneDX nested components must be an array")
            pending.extend(nested)
            licenses = [
                _license(_mapping(entry).get("license", entry))
                for entry in item.get("licenses", [])
            ]
            components.append(
                Component(
                    str(item.get("name", "UNKNOWN")),
                    str(item.get("version", "UNKNOWN")),
                    (
                        licenses[0]
                        if len(licenses) == 1
                        else " AND ".join(f"({value})" for value in licenses)
                    )
                    or "NOASSERTION",
                    path.name,
                )
            )
        return components
    raise ValueError(f"unsupported dependency input: {path.name}")


def build_inventory(
    paths: list[Path], *, overrides: Any = None, baseline: Any = None
) -> dict[str, object]:
    components = sorted({component for path in paths for component in read_components(path)})
    records = apply_overrides([asdict(component) for component in components], overrides or [])
    unresolved = sum(not record["expression"]["valid"] for record in records)
    fingerprint = hashlib.sha256(
        json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "schemaVersion": 1,
        "componentCount": len(components),
        "unresolvedLicenseCount": unresolved,
        "inventorySha256": fingerprint,
        "components": records,
        "comparison": inventory_diff(records, baseline) if baseline is not None else None,
        "provenance": "Local declarations and explicit reviewer overrides; no remote license lookup or legal conclusion",
        "reviewRequired": bool(unresolved),
    }


def build_spdx(inventory: dict[str, object], document_name: str) -> dict[str, object]:
    packages = []
    components = inventory["components"]
    assert isinstance(components, list)
    for index, raw in enumerate(components, start=1):
        assert isinstance(raw, dict)
        packages.append(
            {
                "SPDXID": f"SPDXRef-Package-{index}",
                "name": raw["name"],
                "versionInfo": raw["version"],
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": raw["expression"]["normalized"]
                if raw.get("expression", {}).get("valid")
                else "NOASSERTION",
                "copyrightText": "NOASSERTION",
            }
        )
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": document_name,
        "documentNamespace": f"https://loganpendragonmultiverse.github.io/license-lantern/inventory/{inventory['inventorySha256']}",
        "creationInfo": {
            "creators": ["Tool: License-Lantern-1.0.0"],
            "created": "1970-01-01T00:00:00Z",
        },
        "packages": packages,
    }


def build_notice(inventory: dict[str, object]) -> str:
    lines = [
        "THIRD-PARTY LICENSE REVIEW DRAFT",
        "",
        "Verify every entry and include required license text before distribution.",
        "",
    ]
    components = inventory["components"]
    assert isinstance(components, list)
    for raw in components:
        assert isinstance(raw, dict)
        lines.append(f"- {raw['name']} {raw['version']} — {raw['license_declared']}")
    return "\n".join(lines) + "\n"
