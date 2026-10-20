# Development handoff

License Lantern is an evidence and review tool, never a legal decision engine. Unknown licenses remain `NOASSERTION`; it must not infer compatibility or fetch unreviewed registry data. Parser support requires fixtures from the documented format and deterministic SPDX/NOTICE output.

## 1.1.0 improvement session

Parse SPDX expressions, include nested CycloneDX components and declared npm alias identities, and add sourced attribution overrides with deterministic inventory diffs.

Expressions are parsed by license-expression against its bundled license list. Original declarations remain visible; unknown or malformed expressions remain unresolved, and SPDX output uses NOASSERTION for them. Nested CycloneDX components and expression entries are included; npm lockfile name metadata preserves actual package names for aliases. --overrides accepts a local JSON array with exact name/version/source identity, license_declared, evidence, reviewer and reviewed_at. Each override must match one component; its original declaration and review provenance remain in the report. --baseline compares an earlier inventory for additions, removals and license/provenance changes. Inventory hashes include review provenance. No remote license lookup or legal conclusion is made; attribution drafts still require human review and license texts. Outputs must be new and distinct.

Local formatting, lint, strict types and regression tests pass. Public release completion requires the protected CI/CodeQL matrix, tagged artifacts and matching Forge catalog/detail deployment.

## 1.1.1 — 2026-10-16

npm package-lock.json inputs must declare integer lockfileVersion 2 or 3 and an object-valued packages map. Empty maps and root-only maps are valid empty inventories. Every package entry must be an object, with non-empty text name/version fields when present. Unsupported versions and malformed structures fail before inventory, SPDX or NOTICE output. Alias identities, reviewer overrides, unresolved declarations and deterministic inventory hashes retain their existing meaning.

## 1.1.2 input and output boundaries

Inputs, overrides and baselines are UTF-8 files limited to 10 MB each; duplicate JSON keys, non-finite constants, symlink paths and malformed Python/CycloneDX collections fail clearly. Outputs must have existing parent directories and be distinct new files. All requested destinations and report rendering are checked before publication; exclusive creation preserves a competing writer's file. A later filesystem failure can leave earlier newly published reports. This prevents accidental replacement, without claiming protection against hostile concurrent filesystem changes.

Use `license-lantern examples/bom.json --fail-unresolved` for a synthetic, resolved example. Requirements include/options lines are not followed; this is a direct-declaration inventory, not dependency resolution. Retain the complete checks, 90% coverage gate and installed wheel/source acceptance.

JSON inputs reject nesting beyond 128 containers with an actionable error, including parser recursion failures.

CycloneDX license choices accept a list of license objects (each with exactly one nonempty string id or name), or one nonempty string expression. Mixed choices and malformed identity types fail validation; this validates the consumed license fields, not the complete CycloneDX schema.
