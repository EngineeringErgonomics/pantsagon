from __future__ import annotations

import argparse
import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from pantsagon.adapters.errors import RendererExecutionError
from pantsagon.adapters.policy import pack_validator
from pantsagon.adapters.policy.pack_validator import PackPolicyEngine
from pantsagon.adapters.renderer.copier_renderer import CopierRenderer
from pantsagon.application.pack_validation import validate_pack
from pantsagon.domain.determinism import is_deterministic
from pantsagon.domain.diagnostics import Diagnostic, FileLocation, Severity
from pantsagon.domain.pack import PackRef
from pantsagon.domain.result import Result
from pantsagon.ports.renderer import RenderRequest

DEFAULTS_BY_NAME: dict[str, Any] = {
    "service_name": "example-service",
    "service_name_kebab": "example-service",
    "repo_name": "example-repo",
    "service_pkg": "example_service",
    "service_pkg_snake": "example_service",
}


def _repo_root() -> Path:
    for candidate in [Path.cwd(), *Path.cwd().parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return Path.cwd()


def _relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _serialize_location(location: object | None) -> dict[str, Any] | None:
    if location is None:
        return None
    if isinstance(location, FileLocation):
        return {
            "kind": "file",
            "path": location.path,
            "line": location.line,
            "col": location.col,
        }
    kind = getattr(location, "kind", "unknown")
    return {"kind": kind}


def _serialize_diagnostic(diagnostic: Diagnostic) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": diagnostic.id,
        "code": diagnostic.code,
        "rule": diagnostic.rule,
        "severity": diagnostic.severity.value,
        "message": diagnostic.message,
    }
    if diagnostic.location is not None:
        payload["location"] = _serialize_location(diagnostic.location)
    if diagnostic.hint is not None:
        payload["hint"] = diagnostic.hint
    if diagnostic.details is not None:
        payload["details"] = diagnostic.details
    return payload


def _placeholder_for(var: dict[str, Any]) -> Any:
    name = str(var.get("name", ""))
    if name in DEFAULTS_BY_NAME:
        return DEFAULTS_BY_NAME[name]
    if "default" in var:
        return var.get("default")
    vtype = var.get("type")
    if vtype == "int":
        return 1
    if vtype == "bool":
        return False
    if vtype == "enum":
        enum_values = var.get("enum")
        if isinstance(enum_values, list) and enum_values:
            return enum_values[0]
    return "example"


def _build_answers(manifest: dict[str, Any]) -> dict[str, Any]:
    answers: dict[str, Any] = {}
    raw_variables = manifest.get("variables", [])
    if isinstance(raw_variables, list):
        for entry in raw_variables:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if name is None:
                continue
            answers[str(name)] = _placeholder_for(entry)
    return answers


def _pack_dirs(packs_root: Path) -> list[Path]:
    if not packs_root.exists():
        return []
    dirs = [path for path in packs_root.iterdir() if path.is_dir()]
    candidates = [
        path
        for path in dirs
        if (path / "pack.yaml").exists() or (path / "copier.yml").exists()
    ]
    return sorted(candidates, key=lambda p: p.name)


def _missing_file_diagnostic(path: Path, root: Path, filename: str) -> Diagnostic:
    return Diagnostic(
        code="PACK_FILE_MISSING",
        rule="pack.files",
        severity=Severity.ERROR,
        message=f"Missing required pack file: {filename}",
        location=FileLocation(_relative_path(path / filename, root)),
    )


def _render_failed_diagnostic(
    pack_dir: Path, root: Path, pack_id: str, error: Exception
) -> Diagnostic:
    return Diagnostic(
        code="PACK_RENDER_FAILED",
        rule="pack.render",
        severity=Severity.ERROR,
        message=str(error),
        location=FileLocation(_relative_path(pack_dir, root)),
        details={"pack": pack_id},
        is_execution=True,
    )


def validate_bundled_packs(
    packs_root: Path,
    *,
    render_on_validation_error: bool,
    render_enabled: bool,
    quiet: bool,
) -> Result[dict[str, Any]]:
    root = _repo_root()
    pack_validator.SCHEMA_PATH = pack_validator._schema_path(root)
    engine = PackPolicyEngine()
    renderer = CopierRenderer()
    diagnostics: list[Diagnostic] = []
    artifacts: list[dict[str, Any]] = []

    for pack_dir in _pack_dirs(packs_root):
        pack_diags: list[Diagnostic] = []
        missing: list[str] = []
        if not (pack_dir / "pack.yaml").exists():
            missing.append("pack.yaml")
        if not (pack_dir / "copier.yml").exists():
            missing.append("copier.yml")
        for filename in missing:
            diag = _missing_file_diagnostic(pack_dir, root, filename)
            pack_diags.append(diag)
            diagnostics.append(diag)

        manifest: dict[str, Any] = {}
        pack_id = pack_dir.name
        pack_version = "unknown"
        if (pack_dir / "pack.yaml").exists():
            manifest = pack_validator.load_manifest(pack_dir)
            pack_id = str(manifest.get("id", pack_dir.name))
            pack_version = str(manifest.get("version", "unknown"))
        if not missing:
            result = validate_pack(pack_dir, engine)
            manifest = result.value or manifest
            pack_diags.extend(result.diagnostics)
            diagnostics.extend(result.diagnostics)
        elif manifest:
            schema_diags = pack_validator.validate_manifest_schema(manifest)
            pack_diags.extend(schema_diags)
            diagnostics.extend(schema_diags)

        has_validation_errors = any(
            d.severity == Severity.ERROR for d in pack_diags if not d.is_execution
        )
        render_skipped = False
        status = "passed"

        if has_validation_errors:
            status = "failed"

        if not render_enabled:
            render_skipped = True
        elif has_validation_errors and not render_on_validation_error:
            render_skipped = True

        if not render_skipped and not missing:
            answers = _build_answers(manifest)
            with tempfile.TemporaryDirectory() as tempdir:
                request = RenderRequest(
                    pack=PackRef(id=pack_id, version=pack_version, source="bundled"),
                    pack_path=pack_dir,
                    staging_dir=Path(tempdir),
                    answers=answers,
                    allow_hooks=False,
                )
                try:
                    if quiet:
                        with open(os.devnull, "w", encoding="utf-8") as devnull:
                            with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(
                                devnull
                            ):
                                renderer.render(request)
                    else:
                        renderer.render(request)
                except RendererExecutionError as exc:
                    diag = _render_failed_diagnostic(pack_dir, root, pack_id, exc)
                    diagnostics.append(diag)
                    pack_diags.append(diag)
                    status = "failed"

        artifacts.append(
            {
                "pack_id": pack_id,
                "pack_version": pack_version,
                "source": "bundled",
                "status": status,
                "render_skipped": render_skipped,
                "diagnostics": [_serialize_diagnostic(d) for d in pack_diags],
            }
        )

    return Result(value=None, diagnostics=diagnostics, artifacts=artifacts)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate bundled Pantsagon packs")
    parser.add_argument("--bundled", action="store_true", help="Validate bundled packs")
    parser.add_argument("--json", action="store_true", help="Emit Result JSON")
    parser.add_argument("--quiet", action="store_true", help="Suppress Copier output")
    render_group = parser.add_mutually_exclusive_group()
    render_group.add_argument(
        "--render-on-validation-error",
        action="store_true",
        help="Attempt render even if validation fails",
    )
    render_group.add_argument(
        "--no-render", action="store_true", help="Skip rendering entirely"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.bundled:
        parser.error("--bundled is required in v1")

    result = validate_bundled_packs(
        packs_root=_repo_root() / "packs",
        render_on_validation_error=args.render_on_validation_error,
        render_enabled=not args.no_render,
        quiet=args.quiet or args.json,
    )

    if args.json:
        payload = {
            "result_schema_version": 1,
            "exit_code": result.exit_code,
            "diagnostics": [_serialize_diagnostic(d) for d in result.diagnostics],
            "artifacts": result.artifacts,
        }
        print(json.dumps(payload, sort_keys=is_deterministic()))
    else:
        failed = [a for a in result.artifacts if a.get("status") != "passed"]
        print(f"Validated {len(result.artifacts)} bundled packs")
        for artifact in result.artifacts:
            print(f"- {artifact['pack_id']}: {artifact['status']}")
        if failed:
            print(f"Failures: {len(failed)}")

    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
