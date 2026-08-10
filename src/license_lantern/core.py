from __future__ import annotations

import hashlib
import json
import re
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast


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
        return " AND ".join(name for name in names if name != "NOASSERTION") or "NOASSERTION"
    data = _mapping(value)
    return str(data.get("id") or data.get("name") or "NOASSERTION")


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
            package_name = location.rsplit("node_modules/", 1)[-1]
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
        for raw in data.get("components", []):
            item = _mapping(raw)
            licenses = [
                _license(_mapping(entry).get("license", entry))
                for entry in item.get("licenses", [])
            ]
            components.append(
                Component(
                    str(item.get("name", "UNKNOWN")),
                    str(item.get("version", "UNKNOWN")),
                    " AND ".join(licenses) or "NOASSERTION",
                    path.name,
                )
            )
        return components
    raise ValueError(f"unsupported dependency input: {path.name}")


def build_inventory(paths: list[Path]) -> dict[str, object]:
    components = sorted({component for path in paths for component in read_components(path)})
    unresolved = sum(component.license_declared == "NOASSERTION" for component in components)
    fingerprint = hashlib.sha256(
        "\n".join(
            f"{c.name}|{c.version}|{c.license_declared}|{c.source}" for c in components
        ).encode()
    ).hexdigest()
    return {
        "schemaVersion": 1,
        "componentCount": len(components),
        "unresolvedLicenseCount": unresolved,
        "inventorySha256": fingerprint,
        "components": [asdict(component) for component in components],
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
                "licenseDeclared": raw["license_declared"],
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
