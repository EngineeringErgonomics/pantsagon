#!/usr/bin/env bash
set -euo pipefail

# Hexagonal hygiene guards.
# - Detect path-based imports via importlib.util.spec_from_file_location (tests)
# - Detect private-module imports in tests: `from pkg._private import ...` or `import pkg._private`
# - Fail on module-top imports of heavy dependencies outside adapter packages (source).
#   Heavy dependencies are configured via a JSON config (see README).
#
# False-positive controls:
# - Private test helper prefixes can be allowlisted via `private_allow_prefixes` in config
#   (defaults: test_support, tests.python._stubs).
# - Inline suppressions for exceptional, reviewed cases:
#     # hex-guard: ignore[path-import]
#     # hex-guard: ignore[private-import]
#     # hex-guard: ignore[heavy-import]
#   Place on the violating line or the line above.
#
# There is only one architecture; violations fail.

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

# Config resolution: allow override via HEX_GUARD_CONFIG.
DEFAULT_CONFIG="$ROOT_DIR/tools/guards/hex_enforce/hex_guard_config.json"
CONFIG_FILE="${HEX_GUARD_CONFIG:-$DEFAULT_CONFIG}"

# Defaults if config is missing or incomplete (preserves current behavior):
DEFAULT_TESTS_ROOT="tests"
DEFAULT_SRC_ROOT="services"
DEFAULT_ADAPTER_DIRS=("/adapters/")
DEFAULT_HEAVY_IMPORTS=("torch")
DEFAULT_IGNORE_GLOBS=("**/.git/**" "**/*.md")
DEFAULT_TEST_WHITELIST_DIRS=("wrapper_imports")
# Test-only module prefixes that are allowed to be underscore-prefixed
# (avoid false positives for helpers under tests/python/test_support and _stubs)
DEFAULT_PRIVATE_ALLOW_PREFIXES=("test_support" "test._stubs")
DEFAULT_FORBIDDEN_TEST_IMPORTS=()

TEST_DIR="$ROOT_DIR/$DEFAULT_TESTS_ROOT"
SRC_DIR="$ROOT_DIR/$DEFAULT_SRC_ROOT"

tmp_report="$(mktemp)"
trap 'rm -f "$tmp_report"' EXIT

echo "# Hexagonal Guards Report" >"$tmp_report"
date -u "+Generated: %Y-%m-%dT%H:%M:%SZ" >>"$tmp_report"
echo >>"$tmp_report"

violations=0

# --- Config parsing helpers -------------------------------------------------
have_jq() { command -v jq >/dev/null 2>&1; }

json_get_array() {
	# $1: json file, $2: jq path (e.g., .heavy_imports)
	# prints one item per line. Returns 1 if missing/empty.
	local jf="$1"
	local path="$2"
	if [[ ! -f "$jf" ]]; then
		return 1
	fi
	if have_jq; then
		# shellcheck disable=SC2016
		jq -r "$path // [] | .[]" "$jf" 2>/dev/null || return 1
	else
		# Fallback to Python for environments without jq
		python3 - "$jf" "$path" 2>/dev/null <<'PY'
import json, sys
fn, path = sys.argv[1], sys.argv[2]
try:
    data = json.load(open(fn))
except Exception:
    sys.exit(1)
def get_path(d, path):
    # very small subset: split on '.' and walk keys
    if not path.startswith('.'):
        return None
    keys = path[1:].split('.')
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur
val = get_path(data, path)
if isinstance(val, list):
    for v in val:
        if isinstance(v, str):
            print(v)
    sys.exit(0)
sys.exit(1)
PY
	fi
}

json_get_string() {
	# $1: json file, $2: jq path (e.g., .source_root)
	local jf="$1"
	local path="$2"
	if [[ ! -f "$jf" ]]; then
		return 1
	fi
	if have_jq; then
		# shellcheck disable=SC2016
		jq -r "$path // empty" "$jf" 2>/dev/null || return 1
	else
		python3 - "$jf" "$path" 2>/dev/null <<'PY'
import json, sys
fn, path = sys.argv[1], sys.argv[2]
try:
    data = json.load(open(fn))
except Exception:
    sys.exit(1)
def get_path(d, path):
    if not path.startswith('.'):
        return None
    keys = path[1:].split('.')
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur
val = get_path(data, path)
if isinstance(val, str) and val:
    print(val)
    sys.exit(0)
sys.exit(1)
PY
	fi
}

read_array() {
	local __name="$1"
	eval "$__name=()"
	local line
	while IFS= read -r line; do
		if [[ -n "$line" ]]; then
			line=${line//\"/\\\"}
			eval "$__name+=(\"$line\")"
		fi
	done
}

load_config() {
	# Populate globals: TEST_DIR, SRC_DIR, ADAPTER_DIRS[], HEAVY_IMPORTS[], IGNORE_GLOBS[], TEST_WHITELIST_DIRS[], PRIVATE_ALLOW_PREFIXES[]
	local srcr testsr
	srcr=$(json_get_string "$CONFIG_FILE" .source_root || true)
	testsr=$(json_get_string "$CONFIG_FILE" .tests_root || true)
	if [[ -n "${srcr:-}" ]]; then SRC_DIR="$ROOT_DIR/$srcr"; fi
	if [[ -n "${testsr:-}" ]]; then TEST_DIR="$ROOT_DIR/$testsr"; fi

	# Arrays
	read_array ADAPTER_DIRS < <(json_get_array "$CONFIG_FILE" .adapter_dirs || true)
	read_array HEAVY_IMPORTS < <(json_get_array "$CONFIG_FILE" .heavy_imports || true)
	read_array IGNORE_GLOBS < <(json_get_array "$CONFIG_FILE" .ignore_globs || true)
	read_array TEST_WHITELIST_DIRS < <(json_get_array "$CONFIG_FILE" .whitelist_test_dirs || true)
	read_array PRIVATE_ALLOW_PREFIXES < <(json_get_array "$CONFIG_FILE" .private_allow_prefixes || true)
	read_array FORBIDDEN_TEST_IMPORTS < <(json_get_array "$CONFIG_FILE" .forbidden_test_imports || true)

	# Defaults if not provided
	if [[ ${#ADAPTER_DIRS[@]} -eq 0 ]]; then ADAPTER_DIRS=("${DEFAULT_ADAPTER_DIRS[@]}"); fi
	if [[ ${#HEAVY_IMPORTS[@]} -eq 0 ]]; then HEAVY_IMPORTS=("${DEFAULT_HEAVY_IMPORTS[@]}"); fi
	if [[ ${#IGNORE_GLOBS[@]} -eq 0 ]]; then IGNORE_GLOBS=("${DEFAULT_IGNORE_GLOBS[@]}"); fi
	if [[ ${#TEST_WHITELIST_DIRS[@]} -eq 0 ]]; then TEST_WHITELIST_DIRS=("${DEFAULT_TEST_WHITELIST_DIRS[@]}"); fi
	if [[ ${#PRIVATE_ALLOW_PREFIXES[@]} -eq 0 ]]; then PRIVATE_ALLOW_PREFIXES=("${DEFAULT_PRIVATE_ALLOW_PREFIXES[@]}"); fi
	if [[ ${#FORBIDDEN_TEST_IMPORTS[@]} -eq 0 ]]; then FORBIDDEN_TEST_IMPORTS=("${DEFAULT_FORBIDDEN_TEST_IMPORTS[@]}"); fi
}

load_config

if [[ ! -d "$TEST_DIR" ]]; then
	echo "[hex-guards] ${TEST_DIR#"$ROOT_DIR"/} not found; nothing to scan." >&2
	exit 0
fi

section() {
	local title="$1"
	echo >>"$tmp_report"
	echo "## $title" >>"$tmp_report"
}

collect() {
	local name="$1"
	shift
	local pattern="$1"
	shift
	local filter_re="${1:-}"
	# ignore globs from config
	local exclude_args=()
	for g in "${IGNORE_GLOBS[@]}"; do
		exclude_args+=("--glob" "!$g")
	done
	# Wrapper tests may intentionally load modules by path; whitelist folder name
	# Pattern: tests/python/wrapper_imports/**
	local whitelist_re=""
	# Build whitelist regex from configured dirs
	if [[ ${#TEST_WHITELIST_DIRS[@]} -gt 0 ]]; then
		whitelist_re="$(printf '%s|' "${TEST_WHITELIST_DIRS[@]}")"
		whitelist_re="${whitelist_re%|}"
	else
		whitelist_re="wrapper_imports"
	fi
	# Optional second filter: allowlist prefixes for private imports (ERE for awk)
	local allow_prefix_re=""
	if [[ "$name" == "private-module imports" && ${#PRIVATE_ALLOW_PREFIXES[@]} -gt 0 ]]; then
		local prefix_alt
		# shellcheck disable=SC2016
		prefix_alt="$(printf '%s\n' "${PRIVATE_ALLOW_PREFIXES[@]}" |
			sed -e 's/[.[\\*^$()+?{}|]/\\\\&/g' |
			paste -sd'|' -)"
		allow_prefix_re="^[[:space:]]*(from|import)[[:space:]]+(${prefix_alt})(\\.|[[:space:]]|$)"
	fi

	# Choose inline suppression token and filter in-place with awk
	local suppress_token=""
	case "$name" in
	path-imports*) suppress_token="path-import" ;;
	private-module*) suppress_token="private-import" ;;
	forbidden-test-imports*) suppress_token="forbidden-test-import" ;;
	esac

	# Use PCRE (-P) and smart case (-S). Anchors reduce incidental matches.
	# We intentionally ignore pipeline exit status so "no matches" doesn't mask
	# real matches due to pipefail; we rely on file content to decide results.
	rg -n --hidden --no-ignore "${exclude_args[@]}" -P -S "$pattern" "$TEST_DIR" |
		{ # Inline suppression filter, allowlist, and default explanation formatter
			awk -F: -v token="$suppress_token" -v whitelist_re="$whitelist_re" -v allow_prefix_re="$allow_prefix_re" -v filter_re="$filter_re" '
              function join_rest(start_i,   j, s){
                  s=$start_i; for(j=start_i+1;j<=NF;++j){ s=s FS $j } return s
              }
              function explain(token){
                  if(token=="path-import") return "[path-import] Path-based import via importlib.util.spec_from_file_location; violates black-box tests. Fix: import public API or run CLI via subprocess; use DI for stubs.";
                  if(token=="private-import") return "[private-import] Import of underscore-prefixed production module from tests; violates black-box boundary. Fix: depend on public surface or ports; re-export if needed.";
                  if(token=="forbidden-test-import") return "[forbidden-test-import] Forbidden test import of entrypoint module; violates hex boundary. Fix: exercise handlers via ports or inject app in a fixture without importing entrypoints.";
                  return "";
              }
              {
                path=$1; lineno=$2+0; rest=join_rest(3);
                if(whitelist_re!="" && path ~ whitelist_re) next;
                if(allow_prefix_re!="" && rest ~ allow_prefix_re) next;
                if(filter_re!="" && rest !~ filter_re) next;
                if(token!=""){
                  # Check same and previous line for inline suppression token
                  start = lineno - 1; if (start < 1) start = 1;
                  cmd = "sed -n \"" start "," lineno "p\" \"" path "\"";
                  ignore=0;
                  while ((cmd) | getline l) {
                    if (index(l, "hex-guard: ignore[" token "]")>0) { ignore=1; break }
                  }
                  close(cmd);
                  if (ignore) next;
                  print path":"lineno": " explain(token) " -- " rest;
                } else {
                  print $0;
                }
              }
            '
		} \
			>"$tmp_report.$name" || true
	if [[ -s "$tmp_report.$name" ]]; then
		local count
		count=$(wc -l <"$tmp_report.$name")
		{
			echo "- $name: $count"
			echo
			echo '```text'
			sed -n '1,200p' "$tmp_report.$name"
			echo '```'
		} >>"$tmp_report"
		violations=$((violations + count))
	else
		echo "- $name: 0" >>"$tmp_report"
	fi
}

section "Summary"

# 1) path-based imports via importlib.util.spec_from_file_location
#    Anchor to non-comment line start to avoid matching in comments.
collect "path-imports (spec_from_file_location)" '^(?!\s*#).*\bspec_from_file_location\(.*\)'

if [[ -d "$ROOT_DIR/scripts" ]]; then
	original_test_dir="$TEST_DIR"
	TEST_DIR="$ROOT_DIR/scripts"
	collect "scripts path-imports (spec_from_file_location)" '^(?!\s*#).*\bspec_from_file_location\(.*\)'
	TEST_DIR="$original_test_dir"
fi

# 2) private-module imports in tests: from pkg._private import ... | import pkg._private
#    Use anchored PCRE to only match true import statements.
collect "private-module imports" '^\s*(?:from\s+[A-Za-z0-9_.]+\._[A-Za-z0-9_]+\s+import\b|import\s+[A-Za-z0-9_.]+\._[A-Za-z0-9_]+\b)'

# 3) forbidden test imports (entrypoints, etc.)
section "Forbidden test imports"
if [[ ${#FORBIDDEN_TEST_IMPORTS[@]} -gt 0 ]]; then
	# shellcheck disable=SC2016
	forbidden_re="$(printf '%s\n' "${FORBIDDEN_TEST_IMPORTS[@]}" |
		sed -e 's/[.[\\*^$()+?{}|]/\\\\&/g' |
		paste -sd'|' -)"
	if [[ -n "$forbidden_re" ]]; then
		forbidden_filter_re="^[[:space:]]*(from|import)[[:space:]]+(${forbidden_re})(\\.|[[:space:]]|$)"
		collect "forbidden-test-imports" "^[[:space:]]*(from|import)[[:space:]]+" "$forbidden_filter_re"
	else
		echo "- forbidden-test-imports: 0 (no forbidden_test_imports configured)" >>"$tmp_report"
	fi
else
	echo "- forbidden-test-imports: 0 (no forbidden_test_imports configured)" >>"$tmp_report"
fi

# Additional guard: forbid torch sys.modules mutations in tests.
section "Torch sys.modules mutations"

sysmods_args=()
for g in "${IGNORE_GLOBS[@]}"; do
	sysmods_args+=("--glob" "!$g")
done

pattern_assign="^(?!\s*#).*sys\.modules\[(?:\"|')torch(?:_types)?(?:\\.[^\"']+)?(?:\"|')\]\s*="
pattern_methods="^(?!\s*#).*sys\.modules\.(?:setdefault|pop)\((?:\"|')torch(?:_types)?"

tmp_sys_assign="$tmp_report.torch_assign"
tmp_sys_methods="$tmp_report.torch_methods"
rg -n --hidden --no-ignore "${sysmods_args[@]}" -P -S "$pattern_assign" "$TEST_DIR" 2>/dev/null >"$tmp_sys_assign" || true
rg -n --hidden --no-ignore "${sysmods_args[@]}" -P -S "$pattern_methods" "$TEST_DIR" 2>/dev/null >"$tmp_sys_methods" || true
cat "$tmp_sys_assign" "$tmp_sys_methods" | sed '/^$/d' | sort -u >"$tmp_report.torch_sys"
rm -f "$tmp_sys_assign" "$tmp_sys_methods"
if [[ -s "$tmp_report.torch_sys" ]]; then
	count=$(wc -l <"$tmp_report.torch_sys")
	{
		echo "- torch-sys-modules: $count"
		echo
		echo '```text'
		sed -n '1,200p' "$tmp_report.torch_sys"
		echo '```'
	} >>"$tmp_report"
	violations=$((violations + count))
else
	echo "- torch-sys-modules: 0" >>"$tmp_report"
fi

# ----------------------------------------------------------------------------
# Source scan: module-top torch_types imports outside adapters (enforced)
# ----------------------------------------------------------------------------
if [[ -d "$SRC_DIR" ]]; then
	# Build adapter exclusion as a combined regex for rg -v
	if [[ ${#ADAPTER_DIRS[@]} -gt 0 ]]; then
		adapter_excl="$(printf '%s|' "${ADAPTER_DIRS[@]}")"
		adapter_excl="${adapter_excl%|}"
	else
		adapter_excl="/adapters/"
	fi
	# ignore globs from config
	src_exclude_args=()
	for g in "${IGNORE_GLOBS[@]}"; do
		src_exclude_args+=("--glob" "!$g")
	done

	section "Heavy imports anywhere (outside adapters)"
	if [[ ${#HEAVY_IMPORTS[@]} -gt 0 ]]; then
		# AST-based scanner to ignore TYPE_CHECKING and support inline suppression
		python3 - "$SRC_DIR" "$adapter_excl" "${HEAVY_IMPORTS[@]}" <<'PY' >"$tmp_report.heavy" || true
import sys, os, ast, fnmatch, io

src_root = sys.argv[1]
adapter_excl = sys.argv[2]
heavy = set(sys.argv[3:])

def path_is_adapter(p: str) -> bool:
    return any(x for x in adapter_excl.split('|') if x and x in p)

def is_type_checking_test(node: ast.AST) -> bool:
    # Detect expressions containing TYPE_CHECKING (bare or typing.TYPE_CHECKING)
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id == 'TYPE_CHECKING':
            return True
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) \
           and n.value.id in {'typing', 'typing_extensions'} and n.attr == 'TYPE_CHECKING':
            return True
    return False

def top_name(mod: str | None) -> str | None:
    if not mod:
        return None
    return mod.split('.')[0]

def iter_files(root: str):
    for base, dirs, files in os.walk(root):
        for f in files:
            if not f.endswith('.py'):
                continue
            path = os.path.join(base, f)
            if path_is_adapter(path):
                continue
            yield path

needle = 'hex-guard: ignore[heavy-import]'

for path in iter_files(src_root):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
            text = fh.read()
    except Exception:
        continue
    try:
        tree = ast.parse(text, filename=path)
    except Exception:
        # Skip unparsable files; do not count as violations
        continue
    lines = text.splitlines()

    suppressed_lines: set[int] = set()
    for i, line in enumerate(lines, start=1):
        if needle in line or (i > 1 and needle in lines[i-2]):
            suppressed_lines.add(i)

    type_checking_stack: list[bool] = []

    class V(ast.NodeVisitor):
        def visit_If(self, node: ast.If) -> None:
            tc = is_type_checking_test(node.test)
            type_checking_stack.append(tc)
            for n in node.body:
                self.visit(n)
            type_checking_stack.pop()
            for n in node.orelse:
                self.visit(n)

        def generic_visit(self, node: ast.AST) -> None:
            super().generic_visit(node)

    # Collect imports with positions and matched module
    results: list[tuple[int, str, str]] = []
    def visit_node(node: ast.AST, in_tc: bool) -> None:
        if isinstance(node, ast.Import):
            if in_tc:
                return
            for alias in node.names:
                nm = alias.name.split('.')[0]
                if nm in heavy:
                    src = lines[node.lineno-1] if node.lineno-1 < len(lines) else ''
                    results.append((node.lineno, src, nm))
        elif isinstance(node, ast.ImportFrom):
            if in_tc:
                return
            nm = top_name(node.module)
            if nm in heavy:
                src = lines[node.lineno-1] if node.lineno-1 < len(lines) else ''
                results.append((node.lineno, src, nm))
        elif isinstance(node, ast.If):
            tc = is_type_checking_test(node.test)
            for n in node.body:
                visit_node(n, in_tc or tc)
            for n in node.orelse:
                visit_node(n, in_tc)
        else:
            for child in ast.iter_child_nodes(node):
                visit_node(child, in_tc)

    visit_node(tree, False)

    for lineno, src, mod in results:
        if lineno in suppressed_lines:
            continue
        reason = f"[heavy-import] Heavy dependency '{mod}' imported at module top outside adapters; not under TYPE_CHECKING. Fix: move to adapter layer or gate under TYPE_CHECKING with Protocols."
        sys.stdout.write(f"{path}:{lineno}:{reason} -- {src}\n")
PY
		if [[ -s "$tmp_report.heavy" ]]; then
			count=$(wc -l <"$tmp_report.heavy")
			{
				echo "- heavy-imports-anywhere: $count"
				echo
				echo '```text'
				sed -n '1,200p' "$tmp_report.heavy"
				echo '```'
			} >>"$tmp_report"
			violations=$((violations + count))
		else
			echo "- heavy-imports-anywhere: 0" >>"$tmp_report"
		fi
	else
		echo "- heavy-imports-anywhere: 0 (no heavy_imports configured)" >>"$tmp_report"
	fi
else
	section "Module-top heavy imports (outside adapters)"
	echo "- heavy-top-imports: skipped (src root not found)" >>"$tmp_report"
fi

echo >>"$tmp_report"
echo "Total potential issues: $violations" >>"$tmp_report"

echo "[hex-guards] Report:" >&2
sed -n '1,200p' "$tmp_report" >&2 || true

if [[ "$violations" -gt 0 ]]; then
	echo "[hex-guards] FAIL: violations detected." >&2
	exit 1
fi

echo "[hex-guards] PASS: no violations detected." >&2
exit 0
