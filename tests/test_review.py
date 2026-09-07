import json
from pathlib import Path

import pytest

from license_lantern.cli import main
from license_lantern.core import build_inventory, build_spdx
from license_lantern.review import apply_overrides, expression_info, inventory_diff


def test_explicit_expression_semantics_and_unknowns() -> None:
    for text in (
        "MIT OR Apache-2.0",
        "(MIT OR Apache-2.0) AND BSD-3-Clause",
        "GPL-2.0-only WITH Classpath-exception-2.0",
    ):
        assert expression_info(text)["valid"]
    for text in ("MIT OR", "Fictional-License", "MIT AND NOASSERTION", "MIT WITH Apache-2.0"):
        assert not expression_info(text)["valid"]


def test_nested_scoped_alias_and_review_provenance(tmp_path: Path) -> None:
    lock = tmp_path / "package-lock.json"
    lock.write_text(
        json.dumps(
            {
                "packages": {
                    "node_modules/@scope/alias": {
                        "name": "@scope/actual",
                        "version": "1",
                        "license": "MIT",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    bom = tmp_path / "bom.json"
    bom.write_text(
        json.dumps(
            {
                "bomFormat": "CycloneDX",
                "components": [
                    {
                        "name": "parent",
                        "version": "1",
                        "licenses": [{"expression": "MIT OR Apache-2.0"}],
                        "components": [{"name": "child", "version": "2"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    original = build_inventory([lock, bom])
    assert original["componentCount"] == 3
    assert original["unresolvedLicenseCount"] == 1
    assert any(c["name"] == "@scope/actual" for c in original["components"])
    override = {
        "name": "child",
        "version": "2",
        "source": "bom.json",
        "license_declared": "BSD-3-Clause",
        "evidence": "vendor/LICENSE at reviewed commit abc",
        "reviewer": "Owner",
        "reviewed_at": "2026-09-07",
    }
    reviewed = build_inventory([lock, bom], overrides=[override], baseline=original)
    assert reviewed["unresolvedLicenseCount"] == 0
    assert len(reviewed["comparison"]["changed"]) == 1
    child = next(c for c in reviewed["components"] if c["name"] == "child")
    assert child["override"]["original_license"] == "NOASSERTION"
    assert original["unresolvedLicenseCount"] == 1
    assert (
        build_inventory([bom, lock], overrides=[override])["inventorySha256"]
        == reviewed["inventorySha256"]
    )
    bad = build_inventory([bom], overrides=[{**override, "license_declared": "Unknown-License"}])
    assert any(p["licenseDeclared"] == "NOASSERTION" for p in build_spdx(bad, "review")["packages"])
    overrides = tmp_path / "overrides.json"
    overrides.write_text(json.dumps([override]), encoding="utf-8")
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps(original), encoding="utf-8")
    assert (
        main(
            [
                str(lock),
                str(bom),
                "--overrides",
                str(overrides),
                "--baseline",
                str(baseline),
                "--fail-unresolved",
            ]
        )
        == 0
    )
    output = tmp_path / "out.json"
    output.write_text("keep", encoding="utf-8")
    assert main([str(lock), "--inventory", str(output)]) == 2


@pytest.mark.parametrize("overrides", [{}, [None], [{"name": "x"}]])
def test_invalid_overrides(overrides: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        apply_overrides([], overrides)


def test_unmatched_duplicate_and_bad_baseline() -> None:
    record = {"name": "a", "version": "1", "source": "x", "license_declared": "MIT"}
    override = {**record, "evidence": "LICENSE", "reviewer": "Owner", "reviewed_at": "2026-09-07"}
    with pytest.raises(ValueError, match="exactly one"):
        apply_overrides([], [override])
    with pytest.raises(ValueError, match="Duplicate"):
        apply_overrides([record], [override, override])
    for baseline in ([], {"components": [None]}, {"components": [record, record]}):
        with pytest.raises((TypeError, ValueError)):
            inventory_diff([], baseline)
    assert inventory_diff([], {"components": [record]})["removed"] == [record]
