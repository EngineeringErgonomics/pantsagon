# Test Speed Guards

Prevents slow tests by banning real 3rd‑party runtime usage in tests. The policy is whitelist‑only: tests may import only
explicitly allowed modules plus stdlib and first‑party code. Everything else fails fast.

The guard reports and fails on:

- direct-import: tests directly import banned libraries (e.g., `cupy`, `cudf`, `torch`, `gymnasium`, …).
- heavy-src-import: tests import source modules that import banned libraries or production registries that select real backends.
- cp-proxy-without-early-register: tests import `test_support.cupy_api` but the nearest `conftest.py` lacks a module‑level `register_adapter(TestCuPyAdapter())` (or registers after importing `test_support.cupy_api`).
- registry-cp-in-tests: tests import `cp` from production CuPy registry.

Configuration lives in `test_speed_guard_config.json`.

Key fields:
- `source_root`: first‑party source tree (default `services`).
- `tests_roots`: list of roots to scan for tests (e.g., `tests/python`, `scripts/tools`, `scripts/experiments`).
- `tests_glob`: filename glob for test modules (default `test_*.py`). Files not matching this glob are ignored, which prevents false positives on non‑test helpers under `scripts/**`.
- `allowed_test_modules`: explicit allowlist for test‑only imports (e.g., `pytest`). All other non‑stdlib, non‑first‑party
  modules are treated as violations.
- `registry_modules`: production registries that, if imported at module level by a source module, mark that module as heavy.

## Run

```
tools/guards/test_speed_enforce/test_speed_guards.sh
```

Exit code is non‑zero on any violation. The script prints a Markdown summary with per‑category details.

## Fix guidance

- Use doubles from `tests/python/test_support` instead of importing real 3rd‑party modules.
- For CuPy, ensure a package‑local `conftest.py` registers `TestCuPyAdapter()` at module scope (not inside a fixture) so it executes before tests import any cp proxies.
- Avoid importing production registries in tests unless you only call `register_*` and never `cp()`/`cudf()`/`torch_api()` — prefer test doubles.
