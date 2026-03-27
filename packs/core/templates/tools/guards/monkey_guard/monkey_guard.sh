#!/usr/bin/env bash
set -euo pipefail

# monkey_guard: detect monkey-patching (strict, any scope).
#
# This guard forbids patterns like:
#   SomeClass.method = fn
#   setattr(SomeClass, "method", fn)
#   delattr(SomeClass, "method")
#   vars(SomeClass)["method"] = fn
#   globals()["name"] = value
#
# Strict defaults:
#   - scans services/
#   - scans all scopes (including inside functions)
#   - no CLI flags (scope override via MONKEY_GUARD_SCOPE=module|all)
#
# Exit codes:
#   0 = no violations
#   1 = violations found
#   2 = usage or unexpected failure

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
DEFAULT_SCAN_DIR="$ROOT_DIR/services"

if [[ $# -ne 0 ]]; then
	echo "[monkey-guard] ERROR: this guard takes no arguments (strict by default)." >&2
	exit 2
fi

if [[ ! -d "$DEFAULT_SCAN_DIR" ]]; then
	echo "[monkey-guard] scan dir not found: $DEFAULT_SCAN_DIR; skipping." >&2
	exit 0
fi

tmpfiles="$(mktemp)"
trap 'rm -f "$tmpfiles"' EXIT

rg --files -0 --hidden \
	-g '!**/__pycache__/**' \
	-g '!**/.pants.d/**' \
	-g '!**/dist/**' \
	-g '!**/*.md' \
	-g '!**/BUILD' \
	-g '!**/*.lock' \
	-g '**/*.py' \
	"$DEFAULT_SCAN_DIR" >>"$tmpfiles"

if [[ ! -s "$tmpfiles" ]]; then
	echo "[monkey-guard] No Python files found under: $DEFAULT_SCAN_DIR; skipping." >&2
	exit 0
fi

python3 - "$ROOT_DIR" "$tmpfiles" <<'PY'
import ast
import io
import os
import sys
import tokenize
from dataclasses import dataclass
from typing import Iterable

ROOT_DIR = sys.argv[1]
FILES_LIST_PATH = sys.argv[2]
SCOPE = os.environ.get("MONKEY_GUARD_SCOPE", "all")


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    col: int
    rule: str
    message: str


def is_camel_class_name(name: str) -> bool:
    stripped = name.lstrip("_")
    if not stripped:
        return False
    if not stripped[0].isupper():
        return False
    # Avoid flagging ALL_CAPS constants masquerading as classes.
    return any(ch.islower() for ch in stripped)


def looks_like_class_holder_name(name: str) -> bool:
    stripped = name.lstrip("_").lower()
    return stripped.endswith(("_cls", "_class", "_klass"))


def iter_paths_from_nul_list(path: str) -> Iterable[str]:
    data = open(path, "rb").read()
    for chunk in data.split(b"\0"):
        if not chunk:
            continue
        yield chunk.decode("utf-8")


def rel_path(p: str) -> str:
    try:
        return os.path.relpath(p, ROOT_DIR)
    except Exception:
        return p


def is_type_checking_test(node: ast.AST) -> bool:
    # TYPE_CHECKING or typing.TYPE_CHECKING / typing_extensions.TYPE_CHECKING
    if isinstance(node, ast.Name) and node.id == "TYPE_CHECKING":
        return True
    if isinstance(node, ast.Attribute) and node.attr == "TYPE_CHECKING":
        base = node.value
        return isinstance(base, ast.Name) and base.id in {"typing", "typing_extensions"}
    return False


class _CallCollector(ast.NodeVisitor):
    def __init__(self, *, func_names: set[str]) -> None:
        self._func_names = func_names
        self.called: set[str] = set()

    def _visit_function_signature(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        for dec in node.decorator_list:
            self.visit(dec)
        for default in node.args.defaults:
            self.visit(default)
        for default in node.args.kw_defaults:
            if default is not None:
                self.visit(default)
        for arg in (
            list(node.args.posonlyargs)
            + list(node.args.args)
            + list(node.args.kwonlyargs)
        ):
            if arg.annotation is not None:
                self.visit(arg.annotation)
        if node.args.vararg is not None and node.args.vararg.annotation is not None:
            self.visit(node.args.vararg.annotation)
        if node.args.kwarg is not None and node.args.kwarg.annotation is not None:
            self.visit(node.args.kwarg.annotation)
        if node.returns is not None:
            self.visit(node.returns)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Decorators/defaults/annotations are evaluated at import time; function bodies are not.
        self._visit_function_signature(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function_signature(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Decorators and bases are evaluated at import time; class bodies are not.
        for dec in node.decorator_list:
            self.visit(dec)
        for base in node.bases:
            self.visit(base)
        for kw in node.keywords:
            self.visit(kw)

    def visit_If(self, node: ast.If) -> None:
        if is_type_checking_test(node.test):
            for n in node.orelse:
                self.visit(n)
            return
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in self._func_names:
            self.called.add(node.func.id)
        self.generic_visit(node)


def import_time_function_closure(tree: ast.Module) -> set[str]:
    func_defs: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_defs[stmt.name] = stmt
    if not func_defs:
        return set()

    func_names = set(func_defs)
    collector = _CallCollector(func_names=func_names)
    collector.visit(tree)

    visited: set[str] = set()
    pending = list(collector.called)
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        fn = func_defs.get(name)
        if fn is None:
            continue
        inner = _CallCollector(func_names=func_names)
        for stmt in fn.body:
            inner.visit(stmt)
        for callee in inner.called:
            if callee not in visited:
                pending.append(callee)
    return visited


def _extract_target_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Starred):
        return _extract_target_names(node.value)
    if isinstance(node, (ast.Tuple, ast.List)):
        names: list[str] = []
        for elt in node.elts:
            names.extend(_extract_target_names(elt))
        return names
    return []


class _LocalNameCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()
        self.globals: set[str] = set()
        self.nonlocals: set[str] = set()

    def _add_targets(self, target: ast.AST) -> None:
        for name in _extract_target_names(target):
            self.names.add(name)

    def visit_Assign(self, node: ast.Assign) -> None:
        for t in node.targets:
            self._add_targets(t)
        self.generic_visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._add_targets(node.target)
        if node.value is not None:
            self.generic_visit(node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._add_targets(node.target)
        self.generic_visit(node.value)

    def visit_For(self, node: ast.For) -> None:
        self._add_targets(node.target)
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._add_targets(node.target)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            if item.optional_vars is not None:
                self._add_targets(item.optional_vars)
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        for item in node.items:
            if item.optional_vars is not None:
                self._add_targets(item.optional_vars)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self.names.add(node.name)
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self._add_targets(node.target)
        self.generic_visit(node.value)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.names.add(alias.asname or alias.name.split(".")[-1])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            self.names.add(alias.asname or alias.name)

    def visit_Global(self, node: ast.Global) -> None:
        self.globals.update(node.names)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self.nonlocals.update(node.names)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.names.add(node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.names.add(node.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.names.add(node.name)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return

    def visit_ListComp(self, node: ast.ListComp) -> None:
        return

    def visit_SetComp(self, node: ast.SetComp) -> None:
        return

    def visit_DictComp(self, node: ast.DictComp) -> None:
        return

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        return


def _collect_function_locals(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    names: set[str] = set()
    args = node.args
    for arg in args.posonlyargs + args.args + args.kwonlyargs:
        names.add(arg.arg)
    if args.vararg is not None:
        names.add(args.vararg.arg)
    if args.kwarg is not None:
        names.add(args.kwarg.arg)

    collector = _LocalNameCollector()
    for stmt in node.body:
        collector.visit(stmt)

    names.update(collector.names)
    names.difference_update(collector.globals)
    names.difference_update(collector.nonlocals)
    return names


def _iter_suppression_comments(text: str) -> Iterable[tuple[int, int]]:
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type == tokenize.COMMENT:
            comment = tok.string
            if "monkey:" in comment and "ignore" in comment:
                yield tok.start


class MonkeyGuard(ast.NodeVisitor):
    def __init__(
        self, *, path: str, lines: list[str], import_time_functions: set[str]
    ) -> None:
        self.path = path
        self.lines = lines
        self.violations: list[Violation] = []

        self._class_depth = 0
        self._func_depth = 0
        self._tc_stack: list[bool] = []
        self._import_time_functions = import_time_functions
        self._import_time_stack: list[bool] = []

        # Known class-like names at module scope (seeded by class defs + CamelCase imports).
        self._classlike_names: set[str] = set()
        # Names bound to globals()/locals()/vars() (no-arg) results.
        self._module_dict_aliases: set[str] = set()
        self._module_dict_local_stack: list[set[str]] = []
        self._shadowed_names_stack: list[set[str]] = []

    def _visit_function_signature(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        for dec in node.decorator_list:
            self.visit(dec)
        for default in node.args.defaults:
            self.visit(default)
        for default in node.args.kw_defaults:
            if default is not None:
                self.visit(default)
        for arg in (
            list(node.args.posonlyargs)
            + list(node.args.args)
            + list(node.args.kwonlyargs)
        ):
            if arg.annotation is not None:
                self.visit(arg.annotation)
        if node.args.vararg is not None and node.args.vararg.annotation is not None:
            self.visit(node.args.vararg.annotation)
        if node.args.kwarg is not None and node.args.kwarg.annotation is not None:
            self.visit(node.args.kwarg.annotation)
        if node.returns is not None:
            self.visit(node.returns)

    def _record(self, node: ast.AST, rule: str, message: str) -> None:
        line = int(getattr(node, "lineno", 1))
        col = int(getattr(node, "col_offset", 0))
        self.violations.append(
            Violation(
                path=rel_path(self.path),
                line=line,
                col=col,
                rule=rule,
                message=message,
            )
        )

    def _in_type_checking(self) -> bool:
        return any(self._tc_stack)

    def _in_scoped_region(self) -> bool:
        if SCOPE == "all":
            return True
        # "module" scope: include module-level statements, and also bodies of
        # functions called at import time within the same module (import-time side effects).
        return self._class_depth == 0 and (self._func_depth == 0 or any(self._import_time_stack))

    def _seed_classlike(self, tree: ast.Module) -> None:
        for stmt in tree.body:
            if isinstance(stmt, ast.ClassDef):
                self._classlike_names.add(stmt.name)
            elif isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    name = alias.asname or alias.name.split(".")[-1]
                    if is_camel_class_name(name):
                        self._classlike_names.add(name)
            elif isinstance(stmt, ast.ImportFrom):
                for alias in stmt.names:
                    name = alias.asname or alias.name
                    if is_camel_class_name(name):
                        self._classlike_names.add(name)

        # One-pass aliasing: x = SomeClass, x = mod.SomeClass
        for stmt in tree.body:
            if isinstance(stmt, (ast.Assign, ast.AnnAssign)) and not self._in_type_checking():
                targets: list[ast.AST] = []
                value: ast.AST | None = None
                if isinstance(stmt, ast.Assign):
                    targets = list(stmt.targets)
                    value = stmt.value
                else:
                    targets = [stmt.target]
                    value = stmt.value
                if value is None:
                    continue
                if isinstance(value, ast.Name) and self._is_classlike_name(value.id):
                    for t in targets:
                        if isinstance(t, ast.Name):
                            self._classlike_names.add(t.id)
                if isinstance(value, ast.Attribute) and is_camel_class_name(value.attr):
                    for t in targets:
                        if isinstance(t, ast.Name):
                            self._classlike_names.add(t.id)

        # One-pass aliasing: g = globals() / locals() / vars()
        for stmt in tree.body:
            if isinstance(stmt, (ast.Assign, ast.AnnAssign)) and not self._in_type_checking():
                targets: list[ast.AST] = []
                value: ast.AST | None = None
                if isinstance(stmt, ast.Assign):
                    targets = list(stmt.targets)
                    value = stmt.value
                else:
                    targets = [stmt.target]
                    value = stmt.value
                if value is None:
                    continue
                if self._is_module_dict_call(value):
                    for t in targets:
                        if isinstance(t, ast.Name):
                            self._module_dict_aliases.add(t.id)

    def _is_classlike_name(self, name: str) -> bool:
        if name in {"self", "cls"}:
            return False
        return (
            name in self._classlike_names
            or is_camel_class_name(name)
            or looks_like_class_holder_name(name)
        )

    def _is_classlike_expr(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return self._is_classlike_name(node.id)
        if isinstance(node, ast.Attribute):
            # module.ClassName or outer.InnerClass
            return is_camel_class_name(node.attr)
        return False

    def _is_module_dict_call(self, node: ast.AST) -> bool:
        if not isinstance(node, ast.Call):
            return False
        if node.args or node.keywords:
            return False
        fn = node.func
        if isinstance(fn, ast.Name):
            if fn.id in {"globals", "locals"}:
                return True
            if fn.id == "vars":
                return True
        if isinstance(fn, ast.Attribute):
            # builtins.globals(), builtins.locals(), builtins.vars()
            if fn.attr in {"globals", "locals"}:
                return True
            if fn.attr == "vars":
                return True
        return False

    def _is_module_dict_name(self, name: str) -> bool:
        for shadowed, aliases in zip(
            reversed(self._shadowed_names_stack),
            reversed(self._module_dict_local_stack),
            strict=False,
        ):
            if name in shadowed:
                return name in aliases
        return name in self._module_dict_aliases

    def _add_module_dict_alias(self, name: str) -> None:
        if self._func_depth == 0:
            self._module_dict_aliases.add(name)
            return
        if self._module_dict_local_stack:
            self._module_dict_local_stack[-1].add(name)

    def _value_is_module_dict_alias(self, value: ast.AST) -> bool:
        if self._is_module_dict_call(value):
            return True
        return isinstance(value, ast.Name) and self._is_module_dict_name(value.id)

    def _note_module_dict_aliases(self, *, targets: list[ast.AST], value: ast.AST | None) -> None:
        if not self._in_scoped_region() or self._in_type_checking():
            return
        if value is None:
            return
        if (
            len(targets) == 1
            and isinstance(targets[0], (ast.Tuple, ast.List))
            and isinstance(value, (ast.Tuple, ast.List))
            and len(targets[0].elts) == len(value.elts)
        ):
            for t_elt, v_elt in zip(targets[0].elts, value.elts, strict=False):
                if self._value_is_module_dict_alias(v_elt):
                    for name in _extract_target_names(t_elt):
                        self._add_module_dict_alias(name)
            return

        if not self._value_is_module_dict_alias(value):
            return
        for t in targets:
            for name in _extract_target_names(t):
                self._add_module_dict_alias(name)

    def _check_attr_target(self, target: ast.Attribute) -> None:
        if not self._in_scoped_region():
            return
        if self._in_type_checking():
            return
        if self._is_classlike_expr(target.value):
            base_desc = ast.unparse(target.value) if hasattr(ast, "unparse") else "<class>"
            self._record(
                target,
                "MG001",
                f"class monkey-patch via attribute assignment: {base_desc}.{target.attr} = ...",
            )

    def _check_subscript_target(self, target: ast.Subscript) -> None:
        if not self._in_scoped_region():
            return
        if self._in_type_checking():
            return

        base = target.value
        # vars(ClassLike)[...]
        if isinstance(base, ast.Call) and isinstance(base.func, (ast.Name, ast.Attribute)):
            fn = base.func
            fn_name = fn.id if isinstance(fn, ast.Name) else fn.attr
            if fn_name == "vars" and base.args and self._is_classlike_expr(base.args[0]):
                base_desc = ast.unparse(base.args[0]) if hasattr(ast, "unparse") else "<class>"
                self._record(
                    target,
                    "MG001",
                    f"class monkey-patch via vars(): vars({base_desc})[...] = ...",
                )
                return

        # ClassLike.__dict__[...]
        if isinstance(base, ast.Attribute) and base.attr == "__dict__" and self._is_classlike_expr(base.value):
            base_desc = ast.unparse(base.value) if hasattr(ast, "unparse") else "<class>"
            self._record(
                target,
                "MG001",
                f"class monkey-patch via __dict__: {base_desc}.__dict__[...] = ...",
            )
            return

        # globals()/locals()/vars() -> module namespace mutation
        if self._is_module_dict_call(base):
            base_desc = ast.unparse(base) if hasattr(ast, "unparse") else "globals()"
            self._record(
                target,
                "MG002",
                f"module namespace mutation via {base_desc}[...] = ...",
            )
            return

        # g[...] where g = globals()/locals()/vars()
        if isinstance(base, ast.Name) and self._is_module_dict_name(base.id):
            self._record(
                target,
                "MG002",
                f"module namespace mutation via alias: {base.id}[...] = ...",
            )

    def visit_If(self, node: ast.If) -> None:
        is_tc = is_type_checking_test(node.test)
        if is_tc:
            self._tc_stack.append(True)
            for n in node.body:
                self.visit(n)
            self._tc_stack.pop()
            if node.orelse:
                self._tc_stack.append(False)
                for n in node.orelse:
                    self.visit(n)
                self._tc_stack.pop()
            return
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._class_depth += 1
        try:
            self.generic_visit(node)
        finally:
            self._class_depth -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        is_import_time = SCOPE == "module" and node.name in self._import_time_functions
        if SCOPE == "module" and not is_import_time:
            # Function bodies are not executed at import time unless called.
            # Still scan decorators/defaults/annotations since they are evaluated at import time.
            self._visit_function_signature(node)
            return
        self._shadowed_names_stack.append(_collect_function_locals(node))
        self._func_depth += 1
        self._import_time_stack.append(is_import_time)
        self._module_dict_local_stack.append(set())
        try:
            self.generic_visit(node)
        finally:
            self._module_dict_local_stack.pop()
            self._import_time_stack.pop()
            self._func_depth -= 1
            self._shadowed_names_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        is_import_time = SCOPE == "module" and node.name in self._import_time_functions
        if SCOPE == "module" and not is_import_time:
            self._visit_function_signature(node)
            return
        self._shadowed_names_stack.append(_collect_function_locals(node))
        self._func_depth += 1
        self._import_time_stack.append(is_import_time)
        self._module_dict_local_stack.append(set())
        try:
            self.generic_visit(node)
        finally:
            self._module_dict_local_stack.pop()
            self._import_time_stack.pop()
            self._func_depth -= 1
            self._shadowed_names_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        self._note_module_dict_aliases(targets=list(node.targets), value=node.value)
        for t in node.targets:
            if isinstance(t, ast.Attribute):
                self._check_attr_target(t)
            elif isinstance(t, ast.Subscript):
                self._check_subscript_target(t)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._note_module_dict_aliases(targets=[node.target], value=node.value)
        t = node.target
        if isinstance(t, ast.Attribute):
            self._check_attr_target(t)
        elif isinstance(t, ast.Subscript):
            self._check_subscript_target(t)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        t = node.target
        if isinstance(t, ast.Attribute):
            self._check_attr_target(t)
        elif isinstance(t, ast.Subscript):
            self._check_subscript_target(t)
        self.generic_visit(node)

    def visit_Delete(self, node: ast.Delete) -> None:
        for t in node.targets:
            if isinstance(t, ast.Attribute):
                self._check_attr_target(t)
            elif isinstance(t, ast.Subscript):
                self._check_subscript_target(t)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if not self._in_scoped_region() or self._in_type_checking():
            return

        fn = node.func
        fn_name: str | None = None
        if isinstance(fn, ast.Name):
            fn_name = fn.id
        elif isinstance(fn, ast.Attribute):
            # builtins.setattr / type.__setattr__
            fn_name = fn.attr

        if fn_name in {"setattr", "delattr"} and node.args:
            # setattr(obj, name, value) / delattr(obj, name)
            obj = node.args[0]
            if self._is_classlike_expr(obj):
                obj_desc = ast.unparse(obj) if hasattr(ast, "unparse") else "<class>"
                self._record(
                    node,
                    "MG001",
                    f"class monkey-patch via {fn_name}(): {fn_name}({obj_desc}, ...) ",
                )
                return

        if fn_name in {"__setattr__", "__delattr__"} and node.args:
            obj = node.args[0]
            if self._is_classlike_expr(obj):
                obj_desc = ast.unparse(obj) if hasattr(ast, "unparse") else "<class>"
                self._record(
                    node,
                    "MG001",
                    f"class monkey-patch via {fn_name}(): {fn_name}({obj_desc}, ...) ",
                )
                return

        # globals().update(...) / alias.update(...) etc.
        if isinstance(fn, ast.Attribute):
            base = fn.value
            is_module_dict = self._is_module_dict_call(base)
            if isinstance(base, ast.Name) and self._is_module_dict_name(base.id):
                is_module_dict = True
            if is_module_dict and fn.attr in {
                "update",
                "setdefault",
                "pop",
                "popitem",
                "clear",
                "__setitem__",
                "__delitem__",
            }:
                base_desc = ast.unparse(base) if hasattr(ast, "unparse") else "<module_dict>"
                self._record(
                    node,
                    "MG002",
                    f"module namespace mutation via {base_desc}.{fn.attr}(...)",
                )
                return

        self.generic_visit(node)


violations: list[Violation] = []
files = list(iter_paths_from_nul_list(FILES_LIST_PATH))

if SCOPE not in {"module", "all"}:
    print(f"[monkey-guard] ERROR: invalid scope: {SCOPE}", file=sys.stderr)
    sys.exit(2)

for path in files:
    try:
        text = open(path, "r", encoding="utf-8").read()
    except Exception as exc:
        print(f"[monkey-guard] ERROR: failed to read {rel_path(path)}: {exc}", file=sys.stderr)
        sys.exit(2)
    try:
        tree = ast.parse(text, filename=path)
    except SyntaxError as exc:
        loc = f"{rel_path(path)}:{exc.lineno or 1}:{exc.offset or 0}"
        print(f"[monkey-guard] ERROR: syntax error parsing {loc}: {exc.msg}", file=sys.stderr)
        sys.exit(2)

    lines = text.splitlines()
    import_time_functions = import_time_function_closure(tree)
    v = MonkeyGuard(
        path=path, lines=lines, import_time_functions=import_time_functions
    )
    v._seed_classlike(tree)
    for line_no, col in _iter_suppression_comments(text):
        v.violations.append(
            Violation(
                path=rel_path(path),
                line=line_no,
                col=col,
                rule="MG000",
                message="suppression comments are forbidden; remove `monkey: ignore[...]`",
            )
        )
    v.visit(tree)
    violations.extend(v.violations)

if violations:
    print("# Monkey Guard Report\n")
    print(
        "Detected monkey-patching (post-definition mutation). "
        "Prefer normal methods/mixins or explicit delegation instead of mutating classes or module namespaces.\n"
    )
    for viol in sorted(violations, key=lambda x: (x.path, x.line, x.col, x.rule)):
        print(f"{viol.path}:{viol.line}:{viol.col} {viol.rule} {viol.message}")
    print(f"\nTotal violations: {len(violations)}")
    sys.exit(1)

print("# Monkey Guard Report\n\nNo monkey-patching detected.")
sys.exit(0)
PY
