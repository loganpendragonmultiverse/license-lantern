# Testing

Run `ruff format --check .`, `ruff check .`, `mypy src`, `pytest`, `python -m build`, and `python -m pip_audit .`. Tests cover npm, Python, and CycloneDX inputs, missing licenses, deterministic fingerprints, SPDX output, NOTICE drafts, CI exit behavior, and unsupported documents.

## 1.1.0 regression acceptance

Run the complete existing suite plus the new regression fixtures. Confirm the documented command produces the selected output, malformed input remains actionable, and source files remain unchanged. Parse SPDX expressions, include nested CycloneDX components and declared npm alias identities, and add sourced attribution overrides with deterministic inventory diffs.

## 1.1.1 — 2026-10-16

npm package-lock.json inputs must declare integer lockfileVersion 2 or 3 and an object-valued packages map. Empty maps and root-only maps are valid empty inventories. Every package entry must be an object, with non-empty text name/version fields when present. Unsupported versions and malformed structures fail before inventory, SPDX or NOTICE output. Alias identities, reviewer overrides, unresolved declarations and deterministic inventory hashes retain their existing meaning.

Regression tests use synthetic inputs and disposable trees. Run the complete suite and inspect built wheel/source documentation before preparing a draft PR.

## 1.1.2 input and output boundaries

Inputs, overrides and baselines are UTF-8 files limited to 10 MB each; duplicate JSON keys, non-finite constants, symlink paths and malformed Python/CycloneDX collections fail clearly. Outputs must have existing parent directories and be distinct new files. All requested destinations and report rendering are checked before publication; exclusive creation preserves a competing writer's file. A later filesystem failure can leave earlier newly published reports. This prevents accidental replacement, without claiming protection against hostile concurrent filesystem changes.

Use `license-lantern examples/bom.json --fail-unresolved` for a synthetic, resolved example. Requirements include/options lines are not followed; this is a direct-declaration inventory, not dependency resolution. Retain the complete checks, 90% coverage gate and installed wheel/source acceptance.

JSON inputs reject nesting beyond 128 containers with an actionable error, including parser recursion failures.

CycloneDX license choices accept a list of license objects (each with exactly one nonempty string id or name), or one nonempty string expression. Mixed choices and malformed identity types fail validation; this validates the consumed license fields, not the complete CycloneDX schema.
