import json
from pathlib import Path

import pytest

from license_lantern.cli import main
from license_lantern.core import build_inventory


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"lockfileVersion": 1, "dependencies": {}},
        {"lockfileVersion": 4, "packages": {}},
        {"lockfileVersion": "3", "packages": {}},
        {"lockfileVersion": True, "packages": {}},
        {"lockfileVersion": 3},
        {"lockfileVersion": 3, "packages": []},
        {"lockfileVersion": 3, "packages": None},
        {"lockfileVersion": 3, "packages": {"node_modules/a": None}},
        {"lockfileVersion": 3, "packages": {"node_modules/a": []}},
        {"lockfileVersion": 3, "packages": {"node_modules/a": {"version": 2}}},
        {"lockfileVersion": 3, "packages": {"node_modules/a": {"name": []}}},
    ],
)
def test_invalid_lock_has_no_inventory_or_cli_outputs(payload, tmp_path, capsys):
    source = tmp_path / "package-lock.json"
    content = json.dumps(payload)
    source.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="npm lockfile"):
        build_inventory([source])
    outputs = [tmp_path / name for name in ("inventory.json", "spdx.json", "notice.txt")]
    assert (
        main(
            [
                str(source),
                "--inventory",
                str(outputs[0]),
                "--spdx",
                str(outputs[1]),
                "--notice",
                str(outputs[2]),
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert not captured.out and "npm lockfile" in captured.err
    assert all(not p.exists() for p in outputs)
    assert source.read_text(encoding="utf-8") == content


@pytest.mark.parametrize("version", [2, 3])
@pytest.mark.parametrize("packages", [{}, {"": {}}])
def test_supported_empty_lock_is_valid(version, packages, tmp_path: Path):
    source = tmp_path / "package-lock.json"
    source.write_text(json.dumps({"lockfileVersion": version, "packages": packages}))
    report = build_inventory([source])
    assert report["componentCount"] == 0
    assert report["unresolvedLicenseCount"] == 0
