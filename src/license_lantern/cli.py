from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ._io import load_json, preflight, write_new
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
    try:
        outputs = [path for path in (args.inventory, args.spdx, args.notice) if path]
        preflight(outputs)
        overrides = load_json(args.overrides) if args.overrides else []
        baseline = load_json(args.baseline) if args.baseline else None
        inventory = build_inventory(args.inputs, overrides=overrides, baseline=baseline)
        rendered = json.dumps(inventory, indent=2) + "\n"
        reports = []
        if args.inventory:
            reports.append((args.inventory, rendered))
        if args.spdx:
            reports.append(
                (args.spdx, json.dumps(build_spdx(inventory, args.inputs[0].stem), indent=2) + "\n")
            )
        if args.notice:
            reports.append((args.notice, build_notice(inventory)))
        for path, content in reports:
            write_new(path, content)
        if not args.inventory:
            print(rendered, end="")
    except (OSError, ValueError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return int(args.fail_unresolved and bool(inventory["unresolvedLicenseCount"]))
