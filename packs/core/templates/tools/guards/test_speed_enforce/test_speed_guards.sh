#!/usr/bin/env bash
set -euo pipefail

# Test Speed Guards (whitelist): forbid any 3rd‑party usage in tests except an explicit allowlist.
# Policy: every import in tests must be either stdlib, first‑party code under services/,
# or explicitly allowed test utilities (e.g., pytest, hypothesis, pydantic, test_support).
# Everything else is a violation. Fails fast with an actionable report.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$ROOT_DIR" ]]; then
	ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
fi
DEFAULT_CONFIG="$ROOT_DIR/tools/guards/test_speed_enforce/test_speed_guard_config.json"
if [[ ! -f "$DEFAULT_CONFIG" ]]; then
	DEFAULT_CONFIG="$SCRIPT_DIR/test_speed_guard_config.json"
fi
CONFIG_FILE="${TEST_SPEED_GUARD_CONFIG:-$DEFAULT_CONFIG}"
FALLBACK_CONFIG=""

if [[ -n "${TEST_SPEED_GUARD_CONFIG:-}" && ! -f "$TEST_SPEED_GUARD_CONFIG" ]]; then
	resolved=""
	if [[ "$TEST_SPEED_GUARD_CONFIG" != /* ]]; then
		if [[ -f "$ROOT_DIR/$TEST_SPEED_GUARD_CONFIG" ]]; then
			resolved="$ROOT_DIR/$TEST_SPEED_GUARD_CONFIG"
		elif [[ -f "$SCRIPT_DIR/$TEST_SPEED_GUARD_CONFIG" ]]; then
			resolved="$SCRIPT_DIR/$TEST_SPEED_GUARD_CONFIG"
		fi
	fi
	if [[ -n "$resolved" ]]; then
		CONFIG_FILE="$resolved"
	else
		echo "[test-speed-guards] WARN: config not found at $TEST_SPEED_GUARD_CONFIG; falling back to $DEFAULT_CONFIG" >&2
		CONFIG_FILE="$DEFAULT_CONFIG"
	fi
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
	if [[ -f "$DEFAULT_CONFIG" ]]; then
		CONFIG_FILE="$DEFAULT_CONFIG"
	else
		echo "[test-speed-guards] WARN: config not found: $CONFIG_FILE; using fallback defaults." >&2
		source_root="src"
		if [[ -d "$ROOT_DIR/services" ]]; then
			source_root="services"
		elif [[ -d "$ROOT_DIR/src" ]]; then
			source_root="src"
		fi
		tests_root="tests"
		if [[ -d "$ROOT_DIR/tests" ]]; then
			tests_root="tests"
		elif [[ -d "$ROOT_DIR/test" ]]; then
			tests_root="test"
		fi
		FALLBACK_CONFIG="$(mktemp "${TMPDIR:-/tmp}/test-speed-guards-config.XXXXXX")"
		cat >"$FALLBACK_CONFIG" <<JSON
{
  "source_root": "$source_root",
  "tests_root": "$tests_root",
  "tests_glob": "test_*.py",
  "ignore_globs": [
    "**/.git/**",
    "**/*.md"
  ],
  "allowed_test_modules": [
    "pytest",
    "hypothesis",
    "hypothesis.strategies",
    "pydantic"
  ],
  "registry_modules": []
}
JSON
		CONFIG_FILE="$FALLBACK_CONFIG"
	fi
fi

report_file="$(mktemp "${TMPDIR:-/tmp}/test-speed-guards.XXXXXX")"
cleanup_files=("$report_file")
if [[ -n "$FALLBACK_CONFIG" ]]; then
	cleanup_files+=("$FALLBACK_CONFIG")
fi
trap 'rm -f "${cleanup_files[@]}"' EXIT

python3 - "$CONFIG_FILE" "$ROOT_DIR" "$report_file" <<'PY'
import ast, json, os, sys
from pathlib import Path
import fnmatch as _fnm
from datetime import datetime, timezone

cfg_path, root, report_path = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])

def load_json(path: Path) -> dict:
    try:
        with path.open('r', encoding='utf-8') as fh:
            return json.load(fh)
    except Exception as e:
        print(f"[test-speed-guards] ERROR: failed to read config: {path}: {e}", file=sys.stderr)
        sys.exit(2)

cfg = load_json(Path(cfg_path))
SRC = root / cfg.get('source_root', 'src')
# In hermetic runners (e.g., Pants sandboxes), the source tree may be narrowed
# to only files needed for a given target. If the declared source root is not
# present in this sandbox, skip with a neutral result instead of failing.
if not SRC.exists():
    print(
        f"[test-speed-guards] INFO: source root missing in sandbox: {SRC}; skipping.",
        file=sys.stderr,
    )
    try:
        with report_path.open('w', encoding='utf-8') as fh:
            fh.write(json.dumps({'skipped': True, 'ts': datetime.now(timezone.utc).isoformat()}))
    except Exception:
        pass
    sys.exit(0)
# Support multiple test roots and explicit test file glob filtering.
# Prefer `tests_roots` (list) when present; otherwise use single `tests_root`.
tests_roots_cfg = cfg.get('tests_roots')
if isinstance(tests_roots_cfg, list) and tests_roots_cfg:
    TEST_ROOTS = [root / str(p) for p in tests_roots_cfg]
else:
    TEST_ROOTS = [root / cfg.get('tests_root', 'test')]

TESTS_GLOB = str(cfg.get('tests_glob', 'test_*.py'))
IGNORE_GLOBS = tuple(cfg.get('ignore_globs', []))
ALLOWED_TEST = set(cfg.get('allowed_test_modules', [])) | {'test_support'}
REGISTRIES = set(cfg.get('registry_modules', []))

def rel(p: Path) -> str:
    try:
        return str(p.relative_to(root))
    except Exception:
        return str(p)

def _ignore(path: Path) -> bool:
    s = str(path)
    return any(_fnm.fnmatch(s, pat) for pat in IGNORE_GLOBS)


def iter_py(root_dir: Path):
    for base, _dirs, files in os.walk(root_dir):
        base_path = Path(base)
        if _ignore(base_path):
            continue
        for f in files:
            if not f.endswith('.py'):
                continue
            p = base_path / f
            if _ignore(p):
                continue
            yield p

def iter_tests(root_dir: Path):
    """Yield only test files within a root (e.g., test_*.py or *_test.py)."""
    for p in iter_py(root_dir):
        n = p.name
        if _fnm.fnmatch(n, TESTS_GLOB) or n.endswith('_test.py'):
            yield p

def module_name_from_src(path: Path, src_root: Path) -> str | None:
    try:
        rp = path.relative_to(src_root)
    except Exception:
        return None
    parts = list(rp.parts)
    if parts[-1] == '__init__.py':
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][:-3]
    if not parts:
        return None
    return '.'.join(parts)

def ast_parse(path: Path):
    try:
        text = path.read_text(encoding='utf-8', errors='ignore')
        return ast.parse(text), text
    except Exception:
        return None, ''

def top_name(mod: str | None) -> str | None:
    if not mod:
        return None
    return mod.split('.')[0]


class _ImportScanner(ast.NodeVisitor):
    """Collect imports with context (module-level vs nested, TYPE_CHECKING-guarded).

    We treat imports as "heavy" only when they execute at module import time.
    That excludes:
      - imports under function/class bodies
      - imports guarded by `if TYPE_CHECKING:` (or `if typing.TYPE_CHECKING:`)
    """

    def __init__(self) -> None:
        self.scope_level = 0  # 0 == module level
        self.tc_stack: list[bool] = []  # inside TYPE_CHECKING branch
        self.top_level_imports: set[str] = set()
        self.all_imports: set[str] = set()

    # Scope tracking
    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.scope_level += 1
        self.generic_visit(node)
        self.scope_level -= 1

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef):
        self.scope_level += 1
        self.generic_visit(node)
        self.scope_level -= 1

    def _is_type_checking_name(self, node: ast.AST) -> bool:
        # TYPE_CHECKING or typing.TYPE_CHECKING
        if isinstance(node, ast.Name) and node.id == 'TYPE_CHECKING':
            return True
        if isinstance(node, ast.Attribute) and node.attr == 'TYPE_CHECKING':
            base = node.value
            return isinstance(base, ast.Name) and base.id in {'typing', 'typing_extensions'}
        return False

    def visit_If(self, node: ast.If):
        is_tc = self._is_type_checking_name(node.test)
        if is_tc:
            # Visit TYPE_CHECKING body under tc=True, orelse under tc=False
            self.tc_stack.append(True)
            for n in node.body:
                self.visit(n)
            self.tc_stack.pop()
            if node.orelse:
                self.tc_stack.append(False)
                for n in node.orelse:
                    self.visit(n)
                self.tc_stack.pop()
            return
        # Regular if: descend normally
        self.generic_visit(node)

    def _record(self, name: str) -> None:
        self.all_imports.add(name)
        if self.scope_level == 0 and not any(self.tc_stack):
            self.top_level_imports.add(name)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self._record(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        # Skip relative imports; they are always first-party within a package.
        if getattr(node, 'level', 0):
            return
        mod = getattr(node, 'module', None)
        if mod:
            self._record(mod)


# Determine first‑party runtime top‑level package names (exclude stub‑only dirs).
def first_party_toplevel(src_root: Path) -> set[str]:
    tops: set[str] = set()
    for entry in src_root.iterdir():
        if entry.name.startswith('.'):
            continue
        if entry.is_file() and entry.suffix == '.py':
            tops.add(entry.stem)
        elif entry.is_dir():
            # Treat as first‑party only if any real .py file exists under it
            has_runtime_py = False
            for b, _d, files in os.walk(entry):
                if any(f.endswith('.py') for f in files):
                    has_runtime_py = True
                    break
            if has_runtime_py:
                tops.add(entry.name)
    return tops

STDLIB = set(getattr(sys, 'stdlib_module_names', set()))
FIRST_PARTY = first_party_toplevel(SRC)

def is_third_party_top(top: str) -> bool:
    # Anything not stdlib, not first‑party, and not explicitly allowed for tests is 3rd‑party
    if top in STDLIB:
        return False
    if top in FIRST_PARTY:
        return False
    if top in ALLOWED_TEST:
        return False
    return True

# 1) Build set of heavy src modules (imports any third‑party at module level, or registry)
heavy_src_modules: set[str] = set()
src_imports_by_module: dict[str, set[str]] = {}

for path in iter_py(SRC):
    mod = module_name_from_src(path, SRC)
    if not mod:
        continue
    tree, _ = ast_parse(path)
    if tree is None:
        continue
    scanner = _ImportScanner()
    scanner.visit(tree)
    imports = scanner.all_imports
    top_level = scanner.top_level_imports

    # Heavy if it imports any 3rd‑party module at import time (whitelist policy), or known registries.
    # Treat relative intra-package imports (which appear as names starting with
    # an underscore when using "from .mod import ...") as first-party. These
    # are not third-party dependencies and must not mark a module as heavy.
    tops: set[str] = set()
    for n in top_level:
        if isinstance(n, str) and n.startswith('_'):
            continue
        tn = top_name(n)
        if tn:
            tops.add(tn)
    if any(is_third_party_top(t) for t in tops):
        heavy_src_modules.add(mod)
    if any(n in REGISTRIES for n in top_level):
        heavy_src_modules.add(mod)
    src_imports_by_module[mod] = imports

# 2) Scan tests for violations
violations: list[tuple[str, str, str]] = []  # (category, file, detail)

def add(cat: str, file: Path, detail: str):
    violations.append((cat, rel(file), detail))

def find_nearest_conftest(test_file: Path, stop_at: Path) -> Path | None:
    cur = test_file.parent
    while True:
        cf = cur / 'conftest.py'
        if cf.is_file():
            return cf
        if cur == stop_at:
            break
        if cur == cur.parent:
            break
        cur = cur.parent
    return None

def conftest_has_early_register(conftest: Path) -> tuple[bool, str]:
    tree, text = ast_parse(conftest)
    if tree is None:
        return False, 'unparsable-conftest'
    # Require module-level call to register_adapter(TestCuPyAdapter())
    class State(ast.NodeVisitor):
        def __init__(self) -> None:
            self.in_function = 0
            self.has_module_call = False
            self.register_lineno = None
            self.cp_import_lineno = None
        def visit_FunctionDef(self, node: ast.FunctionDef):
            self.in_function += 1
            self.generic_visit(node)
            self.in_function -= 1
        visit_AsyncFunctionDef = visit_FunctionDef
        def visit_ImportFrom(self, node: ast.ImportFrom):
            if node.module == 'test_support.cupy_api':
                self.cp_import_lineno = node.lineno
        def visit_Import(self, node: ast.Import):
            for alias in node.names:
                if alias.name == 'test_support.cupy_api':
                    self.cp_import_lineno = node.lineno
        def visit_Call(self, node: ast.Call):
            # match register_adapter(TestCuPyAdapter()) at module level
            if self.in_function == 0:
                fn = node.func
                fn_name = None
                if isinstance(fn, ast.Name):
                    fn_name = fn.id
                elif isinstance(fn, ast.Attribute):
                    fn_name = fn.attr
                if fn_name == 'register_adapter':
                    # any arg contains TestCuPyAdapter token
                    src = text.splitlines()[node.lineno-1] if node.lineno-1 < len(text.splitlines()) else ''
                    if 'TestCuPyAdapter' in src:
                        self.has_module_call = True
                        self.register_lineno = node.lineno
            self.generic_visit(node)

    st = State()
    st.visit(tree)
    if not st.has_module_call:
        return False, 'no-module-register'
    if st.cp_import_lineno is not None and st.register_lineno is not None and st.cp_import_lineno < st.register_lineno:
        return False, 'cp-import-before-register'
    return True, 'ok'

heavy_prefixes = tuple(sorted(heavy_src_modules))

def imports_in_test(tree: ast.AST) -> list[str]:
    # Only consider imports that execute at module import time for tests too.
    sc = _ImportScanner()
    sc.visit(tree)
    return sorted(sc.top_level_imports)

for tests_root in TEST_ROOTS:
    for test_file in iter_tests(tests_root):
        tree, text = ast_parse(test_file)
        if tree is None:
            continue

        # a) any third‑party import at module level (whitelist rule)
        sc = _ImportScanner()
        sc.visit(tree)
        # Enforce whitelist for any import location (module-level or nested) in tests.
        for name in sc.all_imports:
            top = name.split('.')[0]
            if is_third_party_top(top):
                add('third-party-import', test_file, f"import {name}")

        # b) heavy src imports (module path startswith heavy module)
        test_imports = imports_in_test(tree)
        for imp in test_imports:
            for heavy in heavy_prefixes:
                if imp == heavy or imp.startswith(heavy + '.'):
                    add('heavy-src-import', test_file, f"imports heavy src module: {imp} (heavy: {heavy})")
                    break

        # c) cp proxy without early register
        uses_cp_proxy = any(imp == 'test_support.cupy_api' or imp.startswith('test_support.cupy_api') for imp in test_imports)
        if uses_cp_proxy:
            cf = find_nearest_conftest(test_file, tests_root)
            ok = False
            reason = 'no-conftest'
            if cf:
                ok, reason = conftest_has_early_register(cf)
                reason = f"{reason}: {rel(cf)}"
            if not ok:
                add('cp-proxy-without-early-register', test_file, reason)

        # d) registry cp imported in tests
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == 'alpha_discovery.common.cupy_adapter.registry':
                names = {a.name for a in node.names}
                if 'cp' in names:
                    add('registry-cp-in-tests', test_file, 'from …registry import cp')

        # e) known framework client imports that must be replaced by test doubles
        for name in sc.top_level_imports:
            if name.startswith('fastapi.testclient') or name.startswith('starlette.testclient'):
                add('framework-testclient', test_file, f"import {name}")

        # f) Static slow-pattern detection for Synergy InProcessAssessAdapter.
        #    Attack root causes (metrics I/O, tiny timeouts, process pools) without timing.
        SYNERGY_MOD = 'alpha_discovery.generative_model.adapters.outbound.synergy.in_process_adapter'
        SYNERGY_PUBLIC = 'alpha_discovery.generative_model.adapters.outbound.synergy.assess_adapters'
        SYNERGY_TEST_FACADES = {
            'test_support.synergy_outbound_facade',
            'test_support.synergy_assess_adapters_facade',
        }

        def _literal(node: ast.AST):
            # Best-effort literal evaluation for small constants (int/float/str).
            if isinstance(node, ast.Constant):
                return node.value, True
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                val, ok = _literal(node.operand)
                if ok and isinstance(val, (int, float)):
                    return (+val if isinstance(node.op, ast.UAdd) else -val), True
            return None, False

        adapter_factories: set[str] = set()
        adapter_modules: set[str] = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.module == SYNERGY_MOD:
                for a in n.names:
                    name = a.asname or a.name
                    if a.name in {'InProcessAssessAdapter', 'LocalAssessAdapter'}:
                        adapter_factories.add(name)
            elif isinstance(n, ast.ImportFrom) and n.module == SYNERGY_PUBLIC:
                for a in n.names:
                    name = a.asname or a.name
                    if a.name in {'InProcessAssessAdapter', 'LocalAssessAdapter'}:
                        adapter_factories.add(name)
            elif isinstance(n, ast.ImportFrom) and n.module in SYNERGY_TEST_FACADES:
                for a in n.names:
                    name = a.asname or a.name
                    if a.name in {'InProcessAssessAdapter', 'LocalAssessAdapter'}:
                        adapter_factories.add(name)
            elif isinstance(n, ast.Import):
                for a in n.names:
                    if a.name == SYNERGY_MOD or a.name == SYNERGY_PUBLIC or a.name in SYNERGY_TEST_FACADES:
                        adapter_modules.add(a.asname or a.name)

        def _is_adapter_ctor(fn: ast.AST) -> bool:
            if isinstance(fn, ast.Name):
                return fn.id in adapter_factories
            if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name):
                if fn.attr in {'InProcessAssessAdapter', 'LocalAssessAdapter'} and fn.value.id in adapter_modules:
                    return True
            return False

        MIN_METRICS_INTERVAL_S = 5.0
        MIN_ENQUEUE_TIMEOUT_MS = 5
        MIN_FLUSH_MS = 2

        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            if not _is_adapter_ctor(n.func):
                continue
            # Collect keyword args as literals when possible
            kwargs: dict[str, object] = {}
            for kw in n.keywords or []:
                if kw.arg is None:
                    continue
                val, ok = _literal(kw.value)
                kwargs[kw.arg] = val if ok else '<dynamic>'

            # 1) Metrics interval too low or default (1.0) -> flushes + file I/O in unit tests
            mi = kwargs.get('metrics_interval_s', None)
            if mi is None:
                add('synergy-inprocess-metrics-interval', test_file, f"metrics_interval_s default (1.0) < {MIN_METRICS_INTERVAL_S}")
            elif isinstance(mi, (int, float)) and float(mi) < MIN_METRICS_INTERVAL_S:
                add('synergy-inprocess-metrics-interval', test_file, f"metrics_interval_s={mi} < {MIN_METRICS_INTERVAL_S}")

            # 2) Metrics path default or persistent path -> disk writes in tests
            mp = kwargs.get('metrics_path', None)
            if mp is None:
                add('synergy-inprocess-metrics-path', test_file, 'metrics_path default .metrics/synergy_inprocess.jsonl (disk I/O)')
            elif isinstance(mp, str):
                path_l = mp.lower()
                looks_persistent = (mp.startswith('.metrics') or mp.endswith('.jsonl')) and ('tmp' not in path_l and '/dev/null' not in path_l)
                if looks_persistent:
                    add('synergy-inprocess-metrics-path', test_file, f"metrics_path='{mp}' looks persistent (use tmp_path or /dev/null)")

            # 3) Tiny enqueue timeout -> racy cross-thread failure and retries
            et = kwargs.get('enqueue_timeout_ms', None)
            if isinstance(et, (int, float)) and int(et) <= MIN_ENQUEUE_TIMEOUT_MS:
                add('synergy-inprocess-enqueue-timeout', test_file, f"enqueue_timeout_ms={et} <= {MIN_ENQUEUE_TIMEOUT_MS}")

            # 4) Overly aggressive flush -> busy polling noise in unit tests
            fm = kwargs.get('flush_ms', None)
            if isinstance(fm, (int, float)) and int(fm) < MIN_FLUSH_MS:
                add('synergy-inprocess-flush-ms', test_file, f"flush_ms={fm} < {MIN_FLUSH_MS}")

            # 5) Process pool in unit tests -> heavyweight startup
            pw = kwargs.get('preprocess_workers', None)
            if isinstance(pw, (int, float)) and int(pw) > 0:
                add('synergy-inprocess-process-pool', test_file, f"preprocess_workers={pw} > 0 in a unit test")

        # g) Generic speed patterns across tests
        class _SpeedScan(ast.NodeVisitor):
            def __init__(self, source: str) -> None:
                self.source = source
                self.findings: list[tuple[str, str]] = []

            def _add(self, cat: str, detail: str) -> None:
                self.findings.append((cat, detail))

            def _is_sleep_call(self, node: ast.Call) -> bool:
                fn = node.func
                if isinstance(fn, ast.Name):
                    return fn.id == 'sleep'
                if isinstance(fn, ast.Attribute):
                    return fn.attr == 'sleep'
                return False

            def _num(self, node: ast.AST) -> float | None:
                if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                    return float(node.value)
                return None

            def visit_For(self, node: ast.For):
                it = node.iter
                if isinstance(it, ast.Call):
                    fn = it.func
                    name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else None)
                    if name == 'range' and it.args:
                        n = self._num(it.args[0])
                        if n is not None and n >= 10000:
                            self._add('high-iteration-loop', f"range({int(n)}) at line {node.lineno}")
                self.generic_visit(node)

            def visit_Call(self, node: ast.Call):
                if self._is_sleep_call(node) and node.args:
                    n = self._num(node.args[0])
                    if n is not None and n >= 0.1:
                        self._add('long-sleep-call', f"sleep({n}) at line {node.lineno}")
                self.generic_visit(node)

            def visit_While(self, node: ast.While):
                def _uses_time(n: ast.AST) -> bool:
                    if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == 'time':
                        return True
                    return any(_uses_time(c) for c in ast.iter_child_nodes(n))
                uses_time = _uses_time(node.test)
                has_sleep = False
                min_sleep: float | None = None
                for n in ast.walk(node):
                    if isinstance(n, ast.Call) and self._is_sleep_call(n) and n.args:
                        has_sleep = True
                        v = self._num(n.args[0])
                        if v is not None:
                            min_sleep = v if min_sleep is None else min(min_sleep, v)
                if has_sleep and (min_sleep is not None) and min_sleep <= 0.02:
                    self._add('polling-sleep-loop', f"while-loop sleeps {min_sleep}s at line {node.lineno}")
                if uses_time and not has_sleep:
                    self._add('busy-wait-loop', f"while time.* without sleep at line {node.lineno}")
                self.generic_visit(node)

            def visit_FunctionDef(self, node: ast.FunctionDef):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call):
                        fn = dec.func
                        name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else None)
                        if name == 'settings':
                            for kw in dec.keywords or []:
                                if kw.arg == 'max_examples':
                                    n = self._num(kw.value)
                                    if n is not None and n > 100:
                                        self._add('hypothesis-max-examples-high', f"max_examples={int(n)} at line {node.lineno}")
                self.generic_visit(node)

        _sp = _SpeedScan(text)
        _sp.visit(tree)
        for cat, det in _sp.findings:
            add(cat, test_file, det)

def fix_hint(cat: str, file: str, detail: str) -> str:
    # Provide actionable remediation per category/detail.
    if cat == 'cp-proxy-without-early-register':
        if detail.startswith('no-module-register'):
            return 'Add module-level register_adapter(TestCuPyAdapter()) in the nearest package conftest.py before any cp import.'
        if detail.startswith('cp-import-before-register'):
            return 'Move register_adapter(TestCuPyAdapter()) above any from test_support.cupy_api import cp in conftest.py.'
        if detail.startswith('no-conftest'):
            return 'Create a package conftest.py and register TestCuPyAdapter() at module scope.'
        return 'Ensure TestCuPyAdapter() is registered at module import time before cp usage.'
    if cat == 'registry-cp-in-tests':
        return 'Do not import cp from production registry in tests; import cp from test_support.cupy_api and ensure early registration in conftest.py.'
    if cat == 'third-party-import':
        mod = detail.split()[1] if ' ' in detail else detail
        top = mod.split('.')[0]
        if top == 'cupy':
            return 'Use cp from test_support.cupy_api (with early TestCuPyAdapter registration).'
        if top == 'cudf':
            return 'Use FakeCudfApi from tests/python/test_support/cudf_fake_backend via DI.'
        if top == 'torch':
            return 'Use tests/python/test_support/torch (which registers the fake provider) instead of real torch.'
        if top == 'httpx':
            return 'Replace real httpx with a small HTTP client stub (e.g., monitoring/fakes/fake_http_client) and inject it.'
        if top == 'fastapi':
            return 'Import FastAPI symbols via tests/python/test_support/fastapi_facade and use asgi_client.AsyncClient.'
        if top == 'starlette':
            return 'Import Request/Response via tests/python/test_support/fastapi_facade instead of starlette directly.'
        if top == 'yaml':
            return 'Replace PyYAML usage with minimal in-repo parser/fixtures or pre-parsed data.'
        if top == 'prometheus_client':
            return 'Assert on our MetricRegistry interface; avoid importing prometheus_client in tests.'
        if top == 'numpy':
            return 'Use cp from test_support.cupy_api and module-level helpers to build arrays.'
        if top == 'gymnasium' or top == 'ray' or top == 'tensorflow' or top == 'transformers' or top == 'xgboost' or top == 'lightgbm':
            return 'Avoid importing heavy runtime libs in tests; depend on ports and inject test doubles from tests/python/test_support.'
        return 'Avoid direct third-party import in tests; use a test double and DI.'
    if cat == 'heavy-src-import':
        return 'Do not import heavy source modules in tests; import the public port and inject a test double from tests/python/test_support.'
    if cat == 'framework-testclient':
        return 'Replace FastAPI/Starlette TestClient with tests/python/test_support/asgi_client.AsyncClient.'
    if cat == 'high-iteration-loop':
        return 'Reduce iteration count (e.g., N<=2_000) or mark as @pytest.mark.perf to exclude from default runs.'
    if cat == 'long-sleep-call':
        return 'Avoid long sleeps in unit tests; prefer events/conditions or shorten to <=0.05s with strict timeouts.'
    if cat == 'polling-sleep-loop':
        return 'Replace polling sleeps with a synchronization primitive (Event/Condition) and a short timeout.'
    if cat == 'busy-wait-loop':
        return 'Insert a tiny sleep (e.g., 0.002s) or use proper wait/notify to avoid CPU spin.'
    if cat == 'hypothesis-max-examples-high':
        return 'Reduce @settings(max_examples) to <=100 for default CI, or mark the test as slow/perf.'
    if cat == 'synergy-inprocess-metrics-interval':
        return 'Pass metrics_interval_s>=60.0 (or avoid metrics entirely in unit tests).'
    if cat == 'synergy-inprocess-metrics-path':
        return 'Set metrics_path to a tmp path (tmp_path fixture) or /dev/null to avoid disk I/O.'
    if cat == 'synergy-inprocess-enqueue-timeout':
        return 'Use enqueue_timeout_ms>=10 and make queue-full deterministic (hold the worker) instead of a 1ms race.'
    if cat == 'synergy-inprocess-flush-ms':
        return 'Avoid ultra-low flush_ms in unit tests; prefer >=2ms (or test batching via focused adapter tests).'
    if cat == 'synergy-inprocess-process-pool':
        return 'Set preprocess_workers=0 in unit tests; process pools belong in integration/benchmarks.'
    return 'Fix to remove real 3rd-party usage in tests.'

# Emit actionable, file-grouped report
violations.sort(key=lambda t: (t[1], t[0], t[2]))
total = len(violations)

by_file: dict[str, list[tuple[str, str]]] = {}
cat_counts: dict[str, int] = {}
for cat, file, detail in violations:
    by_file.setdefault(file, []).append((cat, detail))
    cat_counts[cat] = cat_counts.get(cat, 0) + 1

with report_path.open('w', encoding='utf-8') as out:
    out.write('# Test Speed Guards Report\n')
    out.write(f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n")
    out.write(f"Total potential issues: {total}\n\n")
    # Category summary
    if cat_counts:
        out.write('## Summary\n')
        for cat in sorted(cat_counts.keys()):
            out.write(f"- {cat}: {cat_counts[cat]}\n")
        out.write('\n')

    # File-grouped details with fixes
    out.write('## Actionable Violations by File\n')
    for file in sorted(by_file.keys()):
        issues = by_file[file]
        out.write(f"\n### {file} ({len(issues)} issue(s))\n")
        out.write('```text\n')
        for cat, detail in issues:
            out.write(f"- {cat}: {detail}\n  Fix: {fix_hint(cat, file, detail)}\n")
        out.write('```\n')

print('[test-speed-guards] Report:', file=sys.stderr)
print(Path(report_path).read_text(encoding='utf-8'), file=sys.stderr)

if total > 0:
    sys.exit(1)
PY

exit_code=$?
if [[ $exit_code -ne 0 ]]; then
	exit $exit_code
fi

echo "[test-speed-guards] PASS: no violations detected." >&2
