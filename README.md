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

Python 3.11+ on Windows, macOS, and Linux. Current release: **v1.0.0**. Pull requests are reviewed. MIT licensed.
