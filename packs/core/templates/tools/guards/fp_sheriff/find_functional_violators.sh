#!/usr/bin/env bash
set -euo pipefail

# fp_sheriff: Scan Python sources for anti-functional patterns that
# make code hard to test or type check. This is a lightweight shell
# wrapper that runs an embedded Python AST analyzer.
#
# Defaults to scanning services/. You can override with:
#   tools/guards/fp_sheriff/find_functional_violators.sh --paths services shared
#
# Exit codes:
#   0 = no violations, PASS
#   1 = violations found
#   2 = usage or unexpected failure

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
DEFAULT_SCAN_DIR="$ROOT_DIR/services"

usage() {
	cat <<'USAGE'
Usage: fp_sheriff [--paths <dir> ...]

Scans Python files for functional-programming violations:
  - FP001: Mutable default arguments
  - FP002: use of global/nonlocal
  - FP003: import-time side effects (open/print/os/subprocess/time/random/etc.)
  - FP004: untyped function parameters or returns
  - FP005: Any/object used in annotations
  - FP006: IO/OS/time/random/subprocess in function bodies (no injection)
  - FP007: mutable globals at module level
  - FP008: bare except
  - FP009: implicit Optional (default None without Optional/| None)

Inline suppression: append a comment on the offending line:
  # fp: ignore[FP001,FP006]

Examples:
  tools/guards/fp_sheriff/find_functional_violators.sh
  tools/guards/fp_sheriff/find_functional_violators.sh --paths services shared
USAGE
}

paths=()
while [[ $# -gt 0 ]]; do
	case "${1:-}" in
	-h | --help)
		usage
		exit 0
		;;
	--paths)
		shift || {
			echo "--paths needs value" >&2
			exit 2
		}
		while [[ $# -gt 0 && ! "${1:-}" =~ ^- ]]; do
			paths+=("$1")
			shift || true
		done
		;;
	*)
		echo "Unknown arg: $1" >&2
		usage
		exit 2
		;;
	esac
done

if [[ ${#paths[@]} -eq 0 ]]; then
	if [[ -d "$DEFAULT_SCAN_DIR" ]]; then
		paths=("$DEFAULT_SCAN_DIR")
	else
		echo "[fp-sheriff] services not found; nothing to scan." >&2
		exit 0
	fi
fi

# Collect .py files (NUL-delimited) using ripgrep for speed.
tmpfiles="$(mktemp)"
trap 'rm -f "$tmpfiles"' EXIT
for p in "${paths[@]}"; do
	if [[ -d "$p" ]]; then
		rg --files -0 --hidden \
			-g '!**/__pycache__/**' \
			-g '!**/*.md' \
			-g '!**/BUILD' \
			-g '!**/*.lock' \
			-g '**/*.py' \
			"$p" >>"$tmpfiles" || true
	elif [[ -f "$p" && "$p" == *.py ]]; then
		printf '%s\0' "$p" >>"$tmpfiles"
	fi
done

if [[ ! -s "$tmpfiles" ]]; then
	echo "[fp-sheriff] No Python files found under: ${paths[*]}" >&2
	exit 0
fi

# Run the AST analyzer, passing ROOT_DIR and the NUL-list file path.
python3 - "$ROOT_DIR" "$tmpfiles" <<'PY'
from __future__ import annotations

import ast
import io
import os
import sys
import re
from dataclasses import dataclass
from typing import Iterable, Iterator, Sequence

ROOT_DIR = sys.argv[1]
FILES_LIST_PATH = sys.argv[2]


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    col: int
    rule: str
    message: str


IGNORE_RE = re.compile(r"fp:\s*ignore\[([^\]]+)\]")


def read_ignores(lines: Sequence[str]) -> dict[int, set[str]]:
    ignores: dict[int, set[str]] = {}
    for i, line in enumerate(lines, start=1):
        m = IGNORE_RE.search(line)
        if not m:
            continue
        rules = {r.strip() for r in m.group(1).split(',') if r.strip()}
        if rules:
            ignores[i] = rules
    return ignores


def is_mutable_default(node: ast.AST) -> bool:
    return isinstance(node, (ast.List, ast.Dict, ast.Set)) or (
        isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Name, ast.Attribute))
        and (
            (isinstance(node.func, ast.Name) and node.func.id in {"list", "dict", "set", "defaultdict"})
            or (isinstance(node.func, ast.Attribute) and node.func.attr in {"copy", "fromkeys"})
        )
    )


def iter_defaults(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> Iterator[tuple[str, ast.AST]]:
    pos_args = fn.args.args
    pos_defaults = fn.args.defaults
    if pos_defaults:
        for arg, default in zip(pos_args[-len(pos_defaults):], pos_defaults, strict=False):
            yield arg.arg, default
    for arg, default in zip(fn.args.kwonlyargs, fn.args.kw_defaults, strict=False):
        if default is not None:
            yield arg.arg, default


def has_annotation(ann: ast.AST | None) -> bool:
    return ann is not None


def is_any_or_object(ann: ast.AST | None) -> bool:
    if ann is None:
        return False
    # Convert simple names and dotted names to string forms
    def to_name(a: ast.AST) -> str | None:
        if isinstance(a, ast.Name):
            return a.id
        if isinstance(a, ast.Attribute):
            base = to_name(a.value)
            return f"{base}.{a.attr}" if base else a.attr
        if isinstance(a, ast.Subscript):
            return to_name(a.value)
        return None

    name = to_name(ann) or ""
    simple = name.split(".")[-1]
    return simple in {"Any", "object"}


def is_none_node(ann: ast.AST) -> bool:
    return (isinstance(ann, ast.Constant) and ann.value is None) or (
        isinstance(ann, ast.Name) and ann.id == "None"
    )


def union_has_none(slice_node: ast.AST) -> bool:
    if isinstance(slice_node, ast.Tuple):
        elts = slice_node.elts
    else:
        elts = [slice_node]
    return any(is_optional_annotation(elt) for elt in elts)


def is_optional_annotation(ann: ast.AST | None) -> bool:
    """Return True if the annotation expresses an Optional/nullable type.

    Supports:
      - T | None (PEP 604)
      - Optional[T] / Union[T, None]
      - Annotated[T | None, ...] (unwraps Annotated)
      - String-literal annotations produced by .
    """
    if ann is None:
        return False
    if is_none_node(ann):
        return True

    # Unwrap string-literal annotations by parsing the expression.
    if isinstance(ann, ast.Constant) and isinstance(ann.value, str):
        try:
            parsed = ast.parse(ann.value, mode="eval")
            return is_optional_annotation(parsed.body)
        except Exception:
            return False

    # Unwrap Annotated[...] by recursing into its first type argument.
    if isinstance(ann, ast.Subscript):
        base_name = dotted_name(ann.value) or ""
        if base_name.split(".")[-1] == "Annotated":
            sl = ann.slice
            # slice can be a Tuple(type, *metadata) or a bare node
            inner = None
            if isinstance(sl, ast.Tuple) and sl.elts:
                inner = sl.elts[0]
            else:
                inner = sl  # type: ignore[assignment]
            return is_optional_annotation(inner)

    # Handles Optional[T], Union[T, None], T | None
    if isinstance(ann, ast.BinOp) and isinstance(ann.op, ast.BitOr):
        return is_optional_annotation(ann.left) or is_optional_annotation(ann.right)
    if isinstance(ann, ast.Subscript):
        base_name = dotted_name(ann.value) or ""
        base_simple = base_name.split(".")[-1]
        if base_simple == "Optional":
            return True
        if base_simple == "Union":
            return union_has_none(ann.slice)
    # Sometimes None | T parsed as ast.Constant | ast.Name etc. Covered above.
    return False


def dotted_name(n: ast.AST) -> str | None:
    if isinstance(n, ast.Name):
        return n.id
    if isinstance(n, ast.Attribute):
        base = dotted_name(n.value)
        return f"{base}.{n.attr}" if base else n.attr
    return None


EDGE_PREFIXES = {
    "open",
    "print",
    "os.system",
    "os.remove",
    "os.rename",
    "os.mkdir",
    "os.makedirs",
    "os.rmdir",
    "os.environ",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.check_call",
    "subprocess.check_output",
    "pathlib.Path",
    "shutil.copy",
    "shutil.move",
    "logging.basicConfig",
    "datetime.datetime.now",
    "datetime.date.today",
    "time.time",
    "random.random",
    "random.randrange",
    "random.randint",
    "cupy.random",
}


def is_edge_call(call: ast.Call) -> bool:
    name = dotted_name(call.func)
    if name is None:
        return False
    # reduce dotted names to check prefixes
    parts = name.split(".")
    prefixes = {".".join(parts[:i]) for i in range(1, len(parts) + 1)}
    return any(p in EDGE_PREFIXES for p in prefixes)


def iter_calls_excluding_nested_functions(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
) -> Iterator[ast.Call]:
    stack: list[ast.AST] = list(fn.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(node, ast.Call):
            yield node
        stack.extend(ast.iter_child_nodes(node))


def collect_main_guard_ranges(mod: ast.Module) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for node in mod.body:
        if isinstance(node, ast.If):
            test = node.test
            ok = False
            if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
                left = test.left
                right = test.comparators[0]
                if isinstance(left, ast.Name) and left.id == "__name__" and isinstance(right, ast.Constant) and right.value == "__main__":
                    ok = True
                if isinstance(right, ast.Name) and right.id == "__name__" and isinstance(left, ast.Constant) and left.value == "__main__":
                    ok = True
            if ok:
                # Record the range of the guarded body
                for b in node.body:
                    start = getattr(b, "lineno", None)
                    end = getattr(b, "end_lineno", start)
                    if start is not None and end is not None:
                        ranges.append((start, end))
    return ranges


def in_ranges(line: int, ranges: Sequence[tuple[int, int]]) -> bool:
    return any(a <= line <= b for a, b in ranges)


def analyze(path: str, text: str) -> list[Violation]:
    violations: list[Violation] = []
    lines = text.splitlines()
    ignores_by_line = read_ignores(lines)
    try:
        mod = ast.parse(text, filename=path)
    except SyntaxError as e:
        violations.append(Violation(path, e.lineno or 1, e.offset or 0, "FP000", f"syntax error: {e.msg}"))
        return violations

    main_ranges = collect_main_guard_ranges(mod)

    # FP003 + FP007 + top-level checks
    for node in mod.body:
        assign_value: ast.AST | None = None
        if isinstance(node, ast.Assign):
            assign_value = node.value
        elif isinstance(node, ast.AnnAssign):
            assign_value = node.value

        if assign_value is not None and is_mutable_default(assign_value):
            ln = getattr(node, "lineno", 1)
            if "FP007" not in ignores_by_line.get(ln, set()):
                violations.append(Violation(path, ln, getattr(node, "col_offset", 0), "FP007", "mutable global assignment"))
        if not in_ranges(getattr(node, "lineno", 1), main_ranges):
            # Side effects at import-time
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and is_edge_call(node.value):
                ln = getattr(node, "lineno", 1)
                if "FP003" not in ignores_by_line.get(ln, set()):
                    violations.append(Violation(path, ln, getattr(node, "col_offset", 0), "FP003", "import-time side effect call"))
            if assign_value is not None and isinstance(assign_value, ast.Call) and is_edge_call(assign_value):
                ln = getattr(node, "lineno", 1)
                if "FP003" not in ignores_by_line.get(ln, set()):
                    violations.append(Violation(path, ln, getattr(node, "col_offset", 0), "FP003", "import-time side effect call"))
            if isinstance(node, ast.With):
                for item in node.items:
                    if isinstance(item.context_expr, ast.Call) and is_edge_call(item.context_expr):
                        ln = getattr(node, "lineno", 1)
                        if "FP003" not in ignores_by_line.get(ln, set()):
                            violations.append(Violation(path, ln, getattr(node, "col_offset", 0), "FP003", "import-time IO (with ...)"))

    # Function-level checks
    for node in ast.walk(mod):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            def_line = node.lineno
            # FP001 mutable defaults
            for arg_name, default in iter_defaults(node):
                if is_mutable_default(default):
                    if "FP001" not in ignores_by_line.get(getattr(default, "lineno", def_line), set()):
                        violations.append(Violation(path, getattr(default, "lineno", def_line), getattr(default, "col_offset", 0), "FP001", f"mutable default for parameter '{arg_name}'"))

            # FP004 untyped defs (ignore 'self'/'cls')
            missing = []
            for a in list(node.args.args) + list(node.args.kwonlyargs):
                if a.arg in {"self", "cls"}:
                    continue
                if not has_annotation(a.annotation):
                    missing.append(a.arg)
            if missing or node.returns is None:
                if "FP004" not in ignores_by_line.get(def_line, set()):
                    msg = "missing annotations: "
                    parts = []
                    if missing:
                        parts.append("params=" + ",".join(missing))
                    if node.returns is None:
                        parts.append("return")
                    violations.append(Violation(path, def_line, node.col_offset, "FP004", msg + "; ".join(parts)))

            # FP005 Any/object annotations
            bad = False
            for a in list(node.args.args) + list(node.args.kwonlyargs):
                if is_any_or_object(a.annotation):
                    bad = True
                    ann_line = getattr(a.annotation, "lineno", def_line)
                    if "FP005" not in ignores_by_line.get(ann_line, set()):
                        violations.append(Violation(path, ann_line, getattr(a.annotation, "col_offset", 0), "FP005", f"disallowed annotation on '{a.arg}'"))
            if is_any_or_object(node.returns):
                ann_line = getattr(node.returns, "lineno", def_line)
                if "FP005" not in ignores_by_line.get(ann_line, set()):
                    violations.append(Violation(path, ann_line, getattr(node.returns, "col_offset", 0), "FP005", "disallowed return annotation"))

            # FP006 edge calls in function bodies
            for sub in iter_calls_excluding_nested_functions(node):
                if is_edge_call(sub):
                    ln = getattr(sub, "lineno", def_line)
                    if "FP006" not in ignores_by_line.get(ln, set()):
                        violations.append(Violation(path, ln, getattr(sub, "col_offset", 0), "FP006", "edge IO/time/random call in function body"))

            # FP009 implicit Optional for parameters with default None
            for a, default in zip(node.args.args[-len(node.args.defaults):], node.args.defaults, strict=False):
                if isinstance(default, ast.Constant) and default.value is None and not is_optional_annotation(a.annotation):
                    ln = getattr(a, "lineno", def_line)
                    if "FP009" not in ignores_by_line.get(ln, set()):
                        violations.append(Violation(path, ln, getattr(a, "col_offset", 0), "FP009", f"parameter '{a.arg}' default None but annotation not Optional/| None"))
            for a, default in zip(node.args.kwonlyargs, node.args.kw_defaults, strict=False):
                if default is not None and isinstance(default, ast.Constant) and default.value is None and not is_optional_annotation(a.annotation):
                    ln = getattr(a, "lineno", def_line)
                    if "FP009" not in ignores_by_line.get(ln, set()):
                        violations.append(Violation(path, ln, getattr(a, "col_offset", 0), "FP009", f"parameter '{a.arg}' default None but annotation not Optional/| None"))

        elif isinstance(node, ast.Global):
            ln = getattr(node, "lineno", 1)
            path_local = getattr(node, "_fp_path", path)
            # fp: ignore only works on the 'global' line
            if "FP002" not in read_ignores(text.splitlines()).get(ln, set()):
                violations.append(Violation(path, ln, getattr(node, "col_offset", 0), "FP002", f"global usage: {', '.join(node.names)}"))
        elif isinstance(node, ast.Nonlocal):
            ln = getattr(node, "lineno", 1)
            if "FP002" not in read_ignores(text.splitlines()).get(ln, set()):
                violations.append(Violation(path, ln, getattr(node, "col_offset", 0), "FP002", f"nonlocal usage: {', '.join(node.names)}"))
        elif isinstance(node, ast.ExceptHandler) and node.type is None:
            ln = getattr(node, "lineno", 1)
            if "FP008" not in ignores_by_line.get(ln, set()):
                violations.append(Violation(path, ln, getattr(node, "col_offset", 0), "FP008", "bare except"))

    return violations


def main() -> int:
    with open(FILES_LIST_PATH, "rb") as fh:
        data = fh.read()
    files = [p.decode() for p in data.split(b"\0") if p]
    if not files:
        print("[fp-sheriff] No files provided.", file=sys.stderr)
        return 0
    all_viol: list[Violation] = []
    for path in files:
        try:
            with io.open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception as e:
            print(f"[fp-sheriff] Could not read {path}: {e}", file=sys.stderr)
            continue
        all_viol.extend(analyze(path, text))

    # Print diagnostics similar to ripgrep style
    for v in all_viol:
        rel = os.path.relpath(v.path, ROOT_DIR)
        print(f"{rel}:{v.line}:{v.col}: {v.rule} {v.message}")

    if all_viol:
        # Simple summary by rule
        counts: dict[str, int] = {}
        for v in all_viol:
            counts[v.rule] = counts.get(v.rule, 0) + 1
        parts = ", ".join(f"{k}={counts[k]}" for k in sorted(counts))
        print(f"[fp-sheriff] FAIL: violations found ({parts}).", file=sys.stderr)
        return 1
    else:
        print("[fp-sheriff] PASS: no FP violations detected.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
PY

exit $?
