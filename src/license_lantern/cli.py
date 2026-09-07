from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import build_inventory, build_notice, build_spdx


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a reviewable dependency-license inventory.")
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--spdx", type=Path)
    parser.add_argument("--notice", type=Path)
    parser.add_argument("--fail-unresolved", action="store_true")
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args(argv)
    if not all(path.is_file() for path in args.inputs):
        parser.error("every input must be an existing file")
    outputs = [path.resolve() for path in (args.inventory, args.spdx, args.notice) if path]
    if any(path.resolve() in outputs for path in args.inputs):
        parser.error("outputs must not replace inputs")
    try:
        if len(outputs) != len(set(outputs)) or any(path.exists() for path in outputs):
            raise ValueError("outputs must be distinct new files")
        overrides = json.loads(args.overrides.read_text(encoding="utf-8")) if args.overrides else []
        baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline else None
        inventory = build_inventory(args.inputs, overrides=overrides, baseline=baseline)
    except (OSError, ValueError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(inventory, indent=2) + "\n"
    if args.inventory:
        args.inventory.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if args.spdx:
        args.spdx.write_text(
            json.dumps(build_spdx(inventory, args.inputs[0].stem), indent=2) + "\n",
            encoding="utf-8",
        )
    if args.notice:
        args.notice.write_text(build_notice(inventory), encoding="utf-8")
    return int(args.fail_unresolved and bool(inventory["unresolvedLicenseCount"]))
