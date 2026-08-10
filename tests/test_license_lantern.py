import json
from pathlib import Path

import pytest

from license_lantern.cli import main
from license_lantern.core import build_inventory, build_notice, build_spdx, read_components


def test_reads_package_lock(tmp_path: Path) -> None:
    path = tmp_path / "package-lock.json"
    path.write_text(
        json.dumps(
            {
                "packages": {
                    "": {},
                    "node_modules/alpha": {"version": "1.2.3", "license": "MIT"},
                    "node_modules/beta": {"version": "2.0.0"},
                }
            }
        ),
        encoding="utf-8",
    )
    inventory = build_inventory([path])
    assert inventory["componentCount"] == 2
    assert inventory["unresolvedLicenseCount"] == 1
    assert len(str(inventory["inventorySha256"])) == 64


def test_reads_pyproject_and_requirements(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    requirements = tmp_path / "dev-requirements.txt"
    pyproject.write_text('[project]\ndependencies=["requests>=2", "rich"]\n', encoding="utf-8")
    requirements.write_text("pytest==9.0.0\n-r other.txt\n# comment\n", encoding="utf-8")
    assert {item.name for item in read_components(pyproject)} == {"requests", "rich"}
    assert read_components(requirements)[0].version == "9.0.0"


def test_reads_cyclonedx_license_shapes(tmp_path: Path) -> None:
    path = tmp_path / "bom.json"
    path.write_text(
        json.dumps(
            {
                "bomFormat": "CycloneDX",
                "components": [
                    {"name": "a", "version": "1", "licenses": [{"license": {"id": "Apache-2.0"}}]}
                ],
            }
        ),
        encoding="utf-8",
    )
    assert read_components(path)[0].license_declared == "Apache-2.0"


def test_outputs_spdx_and_notice(tmp_path: Path) -> None:
    path = tmp_path / "package-lock.json"
    path.write_text(
        json.dumps({"packages": {"node_modules/a": {"version": "1", "license": "MIT"}}}),
        encoding="utf-8",
    )
    inventory = build_inventory([path])
    assert build_spdx(inventory, "demo")["spdxVersion"] == "SPDX-2.3"
    assert "a 1 — MIT" in build_notice(inventory)


def test_cli_writes_all_outputs_and_fails_unresolved(tmp_path: Path) -> None:
    source = tmp_path / "requirements.txt"
    source.write_text("example==1.0\n", encoding="utf-8")
    inventory, spdx, notice = (
        tmp_path / name for name in ("inventory.json", "spdx.json", "NOTICE.txt")
    )
    assert (
        main(
            [
                str(source),
                "--inventory",
                str(inventory),
                "--spdx",
                str(spdx),
                "--notice",
                str(notice),
                "--fail-unresolved",
            ]
        )
        == 1
    )
    assert inventory.is_file() and spdx.is_file() and notice.is_file()


def test_rejects_unknown_json(tmp_path: Path) -> None:
    path = tmp_path / "unknown.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        read_components(path)
