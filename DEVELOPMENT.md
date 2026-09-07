# Development handoff

License Lantern is an evidence and review tool, never a legal decision engine. Unknown licenses remain `NOASSERTION`; it must not infer compatibility or fetch unreviewed registry data. Parser support requires fixtures from the documented format and deterministic SPDX/NOTICE output.

## 1.1.0 improvement session

Parse SPDX expressions, include nested CycloneDX components and declared npm alias identities, and add sourced attribution overrides with deterministic inventory diffs.

Expressions are parsed by license-expression against its bundled license list. Original declarations remain visible; unknown or malformed expressions remain unresolved, and SPDX output uses NOASSERTION for them. Nested CycloneDX components and expression entries are included; npm lockfile name metadata preserves actual package names for aliases. --overrides accepts a local JSON array with exact name/version/source identity, license_declared, evidence, reviewer and reviewed_at. Each override must match one component; its original declaration and review provenance remain in the report. --baseline compares an earlier inventory for additions, removals and license/provenance changes. Inventory hashes include review provenance. No remote license lookup or legal conclusion is made; attribution drafts still require human review and license texts. Outputs must be new and distinct.

Local formatting, lint, strict types and regression tests pass. Public release completion requires the protected CI/CodeQL matrix, tagged artifacts and matching Forge catalog/detail deployment.
