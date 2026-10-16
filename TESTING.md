# Testing

Run `ruff format --check .`, `ruff check .`, `mypy src`, `pytest`, `python -m build`, and `python -m pip_audit .`. Tests cover npm, Python, and CycloneDX inputs, missing licenses, deterministic fingerprints, SPDX output, NOTICE drafts, CI exit behavior, and unsupported documents.

## 1.1.0 regression acceptance

Run the complete existing suite plus the new regression fixtures. Confirm the documented command produces the selected output, malformed input remains actionable, and source files remain unchanged. Parse SPDX expressions, include nested CycloneDX components and declared npm alias identities, and add sourced attribution overrides with deterministic inventory diffs.

## 1.1.1 — 2026-10-16

npm package-lock.json inputs must declare integer lockfileVersion 2 or 3 and an object-valued packages map. Empty maps and root-only maps are valid empty inventories. Every package entry must be an object, with non-empty text name/version fields when present. Unsupported versions and malformed structures fail before inventory, SPDX or NOTICE output. Alias identities, reviewer overrides, unresolved declarations and deterministic inventory hashes retain their existing meaning.

Regression tests use synthetic inputs and disposable trees. Run the complete suite and inspect built wheel/source documentation before preparing a draft PR.
