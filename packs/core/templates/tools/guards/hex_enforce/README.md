# Hexagonal Test Guards

This guard script enforces hexagonal boundaries in tests and source code.

Checks:
- Path-based imports in tests via `importlib.util.spec_from_file_location`.
- Private-module imports in tests (`from pkg._private ...` or `import pkg._private`).
- Forbidden test imports for entrypoint modules (configured via `forbidden_test_imports`).
- Heavy dependency imports anywhere in source code, outside adapter directories (both `import X` and `from X import ...`, even if indented inside functions/blocks).

## Config

The script reads JSON config from `tools/guards/hex_enforce/hex_guard_config.json` by default.
Override with `HEX_GUARD_CONFIG=/path/to/config.json`.

Keys:
- `source_root` (string): Source root to scan, default `services`.
- `tests_root` (string): Tests root to scan, default `test`.
- `adapter_dirs` (array of strings): Substring/regex patterns that identify allowed directories where heavy imports are permitted (e.g. `"/adapters/"`).
- `heavy_imports` (array of strings): Module names treated as heavy dependencies that must be accessed only via adapters. The guard flags `import <name>` and `from <name> ...` anywhere in the file.
- `ignore_globs` (array of strings): Ripgrep globs to exclude from scans (e.g. `"**/*.md"`).
- `whitelist_test_dirs` (array of strings): Test subdirectories to ignore for path/private import checks (e.g. harnesses that intentionally do wrapper/path imports).
- `forbidden_test_imports` (array of strings): Module prefixes that must not be imported in tests (e.g. entrypoints like `cli_agent_orchestrator.api.main`).
 

Example:
```json
{
  "source_root": "services",
  "tests_root": "tests/python",
  "adapter_dirs": ["/adapters/", "/drivers/"],
  "heavy_imports": ["torch_types", "tensorflow", "jax", "cupy_types", "cudf_types", "transformers", "xgboost"],
  "ignore_globs": ["**/.git/**", "**/*.md"],
  "whitelist_test_dirs": ["wrapper_imports", "integration"],
  "forbidden_test_imports": ["my_project.entrypoints.api", "my_project.entrypoints.cli"]
}
```

Notes:
- Only the modules listed in `heavy_imports` are enforced, anywhere in the file (not just at module top). Add or remove entries to tune strictness.

## Running

```
tools/guards/hex_enforce/hex_test_guards.sh
```

The script outputs a Markdown report and exits non‑zero on any violations.
