Unique Module Guard — detect ambiguous owners

This guard scans common source roots and reports Python module name clashes that
lead to Pants ambiguity warnings (multiple targets owning the same module).

What it flags
- Cross‑root duplicates: the same module path exists in more than one root
  (e.g., `services/example/src/example/metrics.py` and
  `scripts/tools/discovery_cvic_gate/metrics.py`).
- Package/module collisions: `pkg/__init__.py` alongside `pkg.py`.
- Stub vs. implementation duplicates: both `.py` and `.pyi` exist for the same
  module in the same package (and/or additionally in `typings/`).

Exit codes
- 0: no clashes
- 1: clashes found (prints a Markdown report to stdout)
- 2: configuration or environment error (e.g., cannot read `pants.toml`)

Usage
```
tools/guards/unique_enforce/unique_name_guard.sh

# To reduce noise from DEBUG logs when running Pants right after:
./pants --level=info check services::
```

Notes
- No fallbacks: if configuration cannot be read, the script fails fast with a
  clear error rather than guessing.
- Roots are discovered from `pants.toml` `[source].root_patterns`.
- You can tune scanning with `unique_guard_config.json` (optional):
  - `ignore_globs`: ripgrep‑style globs to exclude
    (matched against repo‑relative paths and absolute paths)
  - `allow_module_globs`: module‑path globs to ignore (e.g., known exceptions)
  - `roots_override`: explicit list of roots to scan (bypasses `pants.toml`)
