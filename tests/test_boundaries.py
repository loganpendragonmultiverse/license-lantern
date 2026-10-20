import json
from pathlib import Path

import pytest

from license_lantern import _io
from license_lantern.cli import main
from license_lantern.core import build_inventory


def source(tmp_path):
    path = tmp_path / "bom.json"
    path.write_text(
        '{"bomFormat":"CycloneDX","components":[{"name":"a","licenses":[{"license":{"id":"MIT"}}]}]}'
    )
    return path


@pytest.mark.parametrize(
    "text",
    [
        "project=[]",
        '[project]\ndependencies="requests"',
        "[project]\ndependencies=[1]",
        '[project]\ndependencies=[" "]',
    ],
)
def test_python_shapes_are_not_silently_dropped(tmp_path, text):
    path = tmp_path / "pyproject.toml"
    path.write_text(text)
    with pytest.raises(TypeError, match="pyproject"):
        build_inventory([path])
    assert main([str(path)]) == 2


@pytest.mark.parametrize(
    "component",
    [
        None,
        {},
        {"name": ""},
        {"name": "a", "version": 1},
        {"name": "a", "components": {}},
        {"name": "a", "licenses": {}},
        {"name": "a", "licenses": [None]},
    ],
)
def test_cyclonedx_shapes_are_validated(tmp_path, component):
    path = tmp_path / "bom.json"
    path.write_text(json.dumps({"bomFormat": "CycloneDX", "components": [component]}))
    with pytest.raises(TypeError, match="CycloneDX"):
        build_inventory([path])


def test_cyclonedx_top_level_collection_and_identity_conflict(tmp_path):
    path = tmp_path / "bom.json"
    path.write_text('{"bomFormat":"CycloneDX","components":{}}')
    with pytest.raises(TypeError, match="components"):
        build_inventory([path])
    path.write_text(
        '{"bomFormat":"CycloneDX","components":[{"name":"a","licenses":[{"expression":"MIT"}]},{"name":"a","licenses":[{"expression":"Apache-2.0"}]}]}'
    )
    with pytest.raises(ValueError, match="conflicting"):
        build_inventory([path])


@pytest.mark.parametrize("text", ['{"x":1,"x":2}', '{"x":NaN}'])
def test_ambiguous_json_is_rejected(tmp_path, text):
    path = tmp_path / "bad.json"
    path.write_text(text)
    assert main([str(path)]) == 2


def test_empty_override_object_is_invalid(tmp_path):
    path = source(tmp_path)
    overrides = tmp_path / "overrides.json"
    overrides.write_text("{}")
    assert main([str(path), "--overrides", str(overrides)]) == 2


def test_bounded_and_invalid_encoding_inputs(tmp_path, monkeypatch):
    path = tmp_path / "bom.json"
    monkeypatch.setattr(_io, "MAX_INPUT_BYTES", 64)
    path.write_bytes(b"x" * 65)
    assert main([str(path)]) == 2
    path.write_bytes(b"\xff")
    assert main([str(path)]) == 2


def test_all_destinations_preflight_before_writes(tmp_path):
    path = source(tmp_path)
    output = tmp_path / "out.json"
    notice = tmp_path / "notice.txt"
    notice.write_text("keep")
    assert main([str(path), "--inventory", str(output), "--notice", str(notice)]) == 2
    assert not output.exists() and notice.read_text() == "keep"
    assert main([str(path), "--inventory", str(output), "--notice", str(output)]) == 2
    assert not output.exists()
    assert main([str(path), "--inventory", str(tmp_path / "missing" / "out")]) == 2
    before = path.read_bytes()
    assert main([str(path), "--inventory", str(path)]) == 2
    assert path.read_bytes() == before


def test_competing_file_and_write_failure_remain_actionable(tmp_path, monkeypatch):
    path = source(tmp_path)
    output = tmp_path / "race.json"
    original = Path.open

    def race(candidate, mode="r", *args, **kwargs):
        if candidate == output and mode == "x":
            with original(candidate, "w", encoding="utf-8") as handle:
                handle.write("other writer")
        return original(candidate, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", race)
    assert main([str(path), "--inventory", str(output)]) == 2
    assert output.read_text() == "other writer"


def test_write_permission_error_is_exit_two(tmp_path, monkeypatch, capsys):
    path = source(tmp_path)
    original = Path.open

    def denied(candidate, mode="r", *args, **kwargs):
        if mode == "x":
            raise PermissionError("synthetic permission failure")
        return original(candidate, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied)
    assert main([str(path), "--inventory", str(tmp_path / "report.json")]) == 2
    assert "error:" in capsys.readouterr().err


def test_symlink_sources_and_dangling_destinations_are_refused(tmp_path):
    path = source(tmp_path)
    link = tmp_path / "input.json"
    output = tmp_path / "out.json"
    absent = tmp_path / "absent.json"
    try:
        link.symlink_to(path)
        output.symlink_to(absent)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")
    assert main([str(link)]) == 2
    assert main([str(path), "--inventory", str(output)]) == 2
    assert output.is_symlink() and not absent.exists()
    with pytest.raises(ValueError, match="new"):
        _io.write_new(output, "preserve")


def test_shipped_example_and_bom_encoding(tmp_path):
    example = Path(__file__).parents[1] / "examples" / "bom.json"
    assert main([str(example), "--fail-unresolved"]) == 0
    path = source(tmp_path)
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    assert build_inventory([path])["unresolvedLicenseCount"] == 0


@pytest.mark.parametrize("depth", [129, 1100], ids=["bounded-depth", "parser-depth"])
@pytest.mark.parametrize("option", [None, "--overrides", "--baseline"])
def test_deep_json_is_actionable_for_every_input(tmp_path, capsys, depth, option):
    valid = source(tmp_path)
    deep = tmp_path / "deep.json"
    deep.write_text("[" * depth + "0" + "]" * depth)
    args = [str(deep)] if option is None else [str(valid), option, str(deep)]
    assert main(args) == 2
    assert "nesting" in capsys.readouterr().err


@pytest.mark.parametrize(
    "choices",
    [
        [{"license": ["MIT"]}],
        [{"expression": ["MIT"]}],
        [{"expression": 1}],
        [{"license": {"id": ["MIT"]}}],
        [{"license": {"name": 1}}],
        [{"license": {"id": "MIT", "name": "MIT"}}],
        [{"expression": "MIT", "license": {"id": "MIT"}}],
        [{"expression": "MIT"}, {"license": {"id": "MIT"}}],
        [{"license": {}}],
        [{}],
        [{"license": {"id": " "}}],
    ],
)
def test_malformed_cyclonedx_license_choices_cannot_resolve(tmp_path, choices):
    path = tmp_path / "bom.json"
    path.write_text(
        json.dumps({"bomFormat": "CycloneDX", "components": [{"name": "a", "licenses": choices}]})
    )
    with pytest.raises((TypeError, ValueError), match="CycloneDX"):
        build_inventory([path])
    assert main([str(path), "--fail-unresolved"]) == 2


@pytest.mark.parametrize(
    "choice", [{"license": {"id": "MIT"}}, {"license": {"name": "MIT"}}, {"expression": "MIT"}]
)
def test_valid_cyclonedx_license_choices_keep_their_identity(tmp_path, choice):
    path = tmp_path / "bom.json"
    path.write_text(
        json.dumps({"bomFormat": "CycloneDX", "components": [{"name": "a", "licenses": [choice]}]})
    )
    assert build_inventory([path])["unresolvedLicenseCount"] == 0


def test_finite_json_fractions_remain_supported(tmp_path):
    path = tmp_path / "finite.json"
    path.write_text('{"fraction":1.25,"tiny":1e-10}')
    assert _io.load_json(path) == {"fraction": 1.25, "tiny": 1e-10}


@pytest.mark.parametrize("number", ["1e400", "-1e400"])
@pytest.mark.parametrize("option", [None, "--overrides", "--baseline"])
def test_json_numeric_overflow_is_rejected_for_every_input(tmp_path, capsys, number, option):
    valid = source(tmp_path)
    bad = tmp_path / "overflow.json"
    bad.write_text('{"number":' + number + "}")
    args = [str(bad)] if option is None else [str(valid), option, str(bad)]
    assert main(args) == 2
    assert "numbers must be finite" in capsys.readouterr().err
