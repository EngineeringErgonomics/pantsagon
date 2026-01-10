# Diagnostics

All frontends emit structured diagnostics:

- code (stable identifier)
- rule (stable rule id / namespace)
- severity (error|warn|info)
- message
- optional location/hint/details

Commands return a Result:

- diagnostics
- artifacts (written paths, applied packs, executed commands)
- exit_code

Use `--json` to emit a machine-readable Result (for CI / GitHub Actions).
