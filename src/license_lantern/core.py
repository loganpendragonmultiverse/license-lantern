from __future__ import annotations

import hashlib
import json
import re
import tomllib
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from . import __version__
from ._io import load_json, read_text
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


def _cyclonedx_licenses(value: object) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(entry, dict) for entry in value):
        raise TypeError("CycloneDX licenses must be an array of objects")
    result = []
    for entry in value:
        if "expression" in entry:
            if len(value) != 1 or set(entry) - {"expression", "bom-ref"}:
                raise ValueError("CycloneDX expression must be the sole license choice")
            declaration = entry["expression"]
        else:
            if set(entry) != {"license"} or not isinstance(entry["license"], dict):
                raise TypeError("CycloneDX license choice requires a license object")
            license_data = entry["license"]
            identities = [key for key in ("id", "name") if key in license_data]
            if len(identities) != 1:
                raise ValueError("CycloneDX license requires exactly one id or name")
            declaration = license_data[identities[0]]
        if not isinstance(declaration, str) or not declaration.strip():
            raise TypeError("CycloneDX license identity/expression must be a nonempty string")
        result.append(declaration.strip())
    return result


def _dependency_name(specification: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9_.-]+)", specification)
    return match.group(1) if match else specification.strip()


def read_components(path: Path) -> list[Component]:
    name = path.name.lower()
    if name == "package-lock.json":
        data = load_json(path)
        if (
            not isinstance(data, dict)
            or type(data.get("lockfileVersion")) is not int
            or data["lockfileVersion"] not in (2, 3)
        ):
            raise ValueError("npm lockfile requires supported integer lockfileVersion 2 or 3")
        packages = data.get("packages")
        if not isinstance(packages, dict):
            raise ValueError("npm lockfile packages must be an object")
        for location, item in packages.items():
            if not isinstance(location, str) or not isinstance(item, dict):
                raise ValueError("npm lockfile package entries must be objects")  # noqa: TRY004
            if any(
                field in item and (not isinstance(item[field], str) or not item[field].strip())
                for field in ("name", "version")
            ):
                raise ValueError("npm lockfile package name/version must be non-empty strings")
        components = []
        for location, raw in packages.items():
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
        data = tomllib.loads(read_text(path))
        project = data.get("project", {})
        if not isinstance(project, dict):
            raise TypeError("pyproject project must be an object")
        dependencies = project.get("dependencies", [])
        if not isinstance(dependencies, list) or any(
            not isinstance(item, str) or not item.strip() for item in dependencies
        ):
            raise TypeError("pyproject dependencies must be an array of nonempty strings")
        return [
            Component(_dependency_name(str(item)), "UNKNOWN", "NOASSERTION", path.name)
            for item in dependencies
            if isinstance(item, str)
        ]
    if name.endswith("requirements.txt") or name == "requirements.txt":
        components = []
        for line in read_text(path).splitlines():
            clean = line.split("#", 1)[0].strip()
            if not clean or clean.startswith("-"):
                continue
            version = clean.split("==", 1)[1] if "==" in clean else "UNKNOWN"
            components.append(Component(_dependency_name(clean), version, "NOASSERTION", path.name))
        return components
    data = _mapping(load_json(path))
    if data.get("bomFormat") == "CycloneDX":
        components = []
        raw_components = data.get("components", [])
        if not isinstance(raw_components, list):
            raise TypeError("CycloneDX components must be an array")
        pending = deque(raw_components)
        while pending:
            item = pending.popleft()
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("name"), str)
                or not item["name"].strip()
            ):
                raise TypeError("CycloneDX components require a nonempty name")
            if "version" in item and (
                not isinstance(item["version"], str) or not item["version"].strip()
            ):
                raise TypeError("CycloneDX component versions must be nonempty strings")
            nested = item.get("components", [])
            if not isinstance(nested, list):
                raise TypeError("CycloneDX nested components must be an array")
            pending.extend(nested)
            licenses = _cyclonedx_licenses(item.get("licenses", []))
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
    identities = [(item.name, item.version, item.source) for item in components]
    if len(identities) != len(set(identities)):
        raise ValueError(
            "conflicting component declarations share one name/version/source identity"
        )
    records = apply_overrides(
        [asdict(component) for component in components], [] if overrides is None else overrides
    )
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
            "creators": [f"Tool: License-Lantern-{__version__}"],
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
