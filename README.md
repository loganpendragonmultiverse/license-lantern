# License Lantern

License Lantern builds a reviewable dependency-license inventory, SPDX 2.3 draft, and third-party attribution draft from local project files.

Version 1 reads npm `package-lock.json`, Python `pyproject.toml`, requirements files, and CycloneDX JSON. It preserves unresolved licenses as `NOASSERTION` instead of guessing and can fail CI when human review remains.

## Three-minute start

```bash
python -m pip install .
license-lantern package-lock.json --inventory licenses.json --spdx sbom.spdx.json --notice THIRD-PARTY.txt
license-lantern requirements.txt --fail-unresolved
```

## Scope and limitations

- Output is an evidence draft, not legal advice, a compatibility ruling, or proof that an upstream declaration is correct.
- Lockfiles often omit license text and copyright notices; those must be verified and added before distribution.
- Python requirement specifications normally lack license metadata and remain unresolved without a supplied SBOM.
- No package registry, network service, vulnerability database, telemetry, or source-code scanner is used.
- Input files are read-only and outputs cannot replace them.

Python 3.11+ on Windows, macOS, and Linux. Current release: **v1.1.0**. Pull requests are reviewed. MIT licensed.

## Version 1.1.0: reviewed improvements

Parse SPDX expressions, include nested CycloneDX components and declared npm alias identities, and add sourced attribution overrides with deterministic inventory diffs.

```bash
license-lantern pyproject.toml --inventory review.json
```

Expressions are parsed by license-expression against its bundled license list. Original declarations remain visible; unknown or malformed expressions remain unresolved, and SPDX output uses NOASSERTION for them. Nested CycloneDX components and expression entries are included; npm lockfile name metadata preserves actual package names for aliases. --overrides accepts a local JSON array with exact name/version/source identity, license_declared, evidence, reviewer and reviewed_at. Each override must match one component; its original declaration and review provenance remain in the report. --baseline compares an earlier inventory for additions, removals and license/provenance changes. Inventory hashes include review provenance. No remote license lookup or legal conclusion is made; attribution drafts still require human review and license texts. Outputs must be new and distinct.
