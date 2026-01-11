# v1.0.0 Release Checklist

This checklist defines the minimum release readiness steps for Pantsagon v1.0.0.

## Pre-release verification

- [ ] CI green: pytest + pack validation (deterministic mode)
- [ ] `python -m pantsagon.tools.validate_packs --bundled` passes locally
- [ ] Docs generators ran with clean git diff
- [ ] README reflects current CLI behavior and status

## Packaging and versioning

- [ ] Update `pyproject.toml` version to `1.0.0`
- [ ] Tag the release `v1.0.0`
- [ ] Publish release notes

## Documentation

- [ ] Update CLI docs if flags changed
- [ ] Update schema docs if schemas changed
- [ ] Update diagnostic codes if codes changed
- [ ] Update pack docs if packs changed
- [ ] Publish docs for `v1.0.0` and update `latest`
