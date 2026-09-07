# Testing

Run `ruff format --check .`, `ruff check .`, `mypy src`, `pytest`, `python -m build`, and `python -m pip_audit .`. Tests cover npm, Python, and CycloneDX inputs, missing licenses, deterministic fingerprints, SPDX output, NOTICE drafts, CI exit behavior, and unsupported documents.

## 1.1.0 regression acceptance

Run the complete existing suite plus the new regression fixtures. Confirm the documented command produces the selected output, malformed input remains actionable, and source files remain unchanged. Parse SPDX expressions, include nested CycloneDX components and declared npm alias identities, and add sourced attribution overrides with deterministic inventory diffs.
