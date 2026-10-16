# Changelog

## [1.1.1] - 2026-10-16

npm package-lock.json inputs must declare integer lockfileVersion 2 or 3 and an object-valued packages map. Empty maps and root-only maps are valid empty inventories. Every package entry must be an object, with non-empty text name/version fields when present. Unsupported versions and malformed structures fail before inventory, SPDX or NOTICE output. Alias identities, reviewer overrides, unresolved declarations and deterministic inventory hashes retain their existing meaning.


## 1.1.0 - 2026-09-07

- Parse SPDX expressions, include nested CycloneDX components and declared npm alias identities, and add sourced attribution overrides with deterministic inventory diffs.
- Added regression coverage for the audited behavior and invalid inputs.

## 1.0.0 - 2026-08-10

- Added local npm, Python, and CycloneDX dependency inventory readers.
- Added unresolved-license review evidence and deterministic inventory fingerprints.
- Added SPDX 2.3 and third-party attribution drafts without legal compatibility claims.
