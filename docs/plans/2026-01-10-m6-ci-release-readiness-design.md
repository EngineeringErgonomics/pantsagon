# M6 CI + Release Readiness Design

**Goal:** Add deterministic CI validation for packs and tests, plus release readiness docs for v1.0.0.

**Architecture:** Introduce a standalone module entry point `python -m pantsagon.tools.validate_packs` that validates bundled packs and optionally renders them. Keep the module independent of the Typer CLI. CI will call tests and pack validation as distinct steps.

**Tech Stack:** Python 3.12, argparse, existing `validate_pack` logic, Copier renderer.

## Pack validation command behavior

`pantsagon.tools.validate_packs` provides a focused, deterministic validation path for bundled packs. It enumerates packs under `packs/` by scanning subdirectories that contain both `pack.yaml` and `copier.yml` (missing file(s) produce a validation diagnostic pointing at the missing path). Validation is per pack and continues even when one pack fails. For each pack it runs `validate_pack()` to perform schema checks and manifest vs Copier variable cross checks. If any error diagnostics exist, the pack is marked failed and render is skipped by default. Flags control render behavior: `--no-render` forces validation-only, `--render-on-validation-error` attempts render even after validation failures. `--no-render` and `--render-on-validation-error` are mutually exclusive (or `--no-render` wins if both are provided). Render uses `CopierRenderer` with `allow_hooks=False` into a temp directory. Smoke answers use defaults from the manifest when present; otherwise type-based placeholders are used, with name-aware safe defaults for common variables (for example `service_name=example-service`, `repo_name=example-repo`, `service_pkg=example_service`). Render failures produce a Diagnostic with `code=PACK_RENDER_FAILED`, `rule=pack.render`, and `is_execution=True` for exit code precedence.

## Output, determinism, and exit codes

The tool prints a human summary to stdout and supports `--json` for structured results. JSON output aligns with the Result schema shape: `exit_code`, `diagnostics`, and `artifacts`. Artifacts include per-pack entries with `pack_id`, `pack_version`, `source`, `status`, `render_skipped`, and per-pack diagnostics. Exit codes follow the Result contract: any execution error yields 3, else any validation error yields 2, else 0. Deterministic mode (`PANTSAGON_DETERMINISTIC=1`) stabilizes output: pack order is sorted, temp paths are omitted, and timing fields are not emitted. All rendering runs in isolated temp dirs with hooks disabled to avoid side effects.

## CI and release readiness

CI adds a dedicated pack-validation step after pytest, using deterministic mode and `python -m pantsagon.tools.validate_packs --bundled`. This makes failures easy to triage and keeps validation independent of test discovery. Release readiness adds a v1.0.0 checklist doc and updates README with final status and usage notes. The README keeps deterministic mode and the new pack validation command clearly documented.
