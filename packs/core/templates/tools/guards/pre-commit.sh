#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT_DIR"

LOG_DIR="$ROOT_DIR/.git/hooks/logs"
mkdir -p "$LOG_DIR"

read_languages() {
	python3 - <<'PY' 2>/dev/null || echo "python"
import tomllib
from pathlib import Path
try:
    data = tomllib.loads(Path(".pantsagon.toml").read_text(encoding="utf-8"))
    langs = data.get("selection", {}).get("languages", []) or ["python"]
    print(" ".join(str(x) for x in langs))
except Exception:
    print("python")
PY
}

LANGS="$(read_languages)"
has_lang() { [[ " $LANGS " == *" $1 "* ]]; }

pants_cmd() {
	if command -v pants >/dev/null 2>&1; then
		echo "pants"
		return 0
	fi
	if [ -x "$ROOT_DIR/pants" ]; then
		echo "$ROOT_DIR/pants"
		return 0
	fi
	return 1
}

PANTS="$(pants_cmd || true)"

run_quiet() {
	local name="$1"
	shift
	local logfile="$LOG_DIR/${name}.log"
	echo "[pre-commit] ${name}: running... (log: $logfile)"
	if "$@" >"$logfile" 2>&1; then
		echo "[pre-commit] ${name}: ok (log: $logfile)"
	else
		local ec=$?
		echo "[pre-commit] ${name}: FAILED (exit ${ec}). Showing last 100 lines:"
		if [[ ! -f "$logfile" ]]; then
			echo "[pre-commit] ${name}: log file missing: $logfile" >&2
			exit 1
		fi
		set +e
		tail -n 100 "$logfile"
		local tail_ec=$?
		set -e
		if [[ $tail_ec -ne 0 ]]; then
			echo "[pre-commit] ${name}: failed reading log: $logfile (exit ${tail_ec})" >&2
			exit "$tail_ec"
		fi
		echo "[pre-commit] Full log: $logfile"
		exit "$ec"
	fi
}

mapfile -t STAGED < <(git diff --cached --name-only --diff-filter=ACM | sed '/^$/d')

if [[ ${#STAGED[@]} -gt 0 && -n "$PANTS" && " $LANGS " == *" python "* ]]; then
	echo "[pre-commit] Formatting staged files..."
	run_quiet format_staged "$PANTS" fmt "${STAGED[@]}"

	echo "[pre-commit] Linting staged files..."
	run_quiet lint_staged "$PANTS" lint "${STAGED[@]}"

	echo "[pre-commit] Typechecking staged files..."
	run_quiet check_staged "$PANTS" check "${STAGED[@]}"
else
	echo "[pre-commit] Skipping Pants format/lint/check (requires python + pants + staged files)."
fi

echo "[pre-commit] Optional secret scan (TruffleHog) on staged files..."
if [[ ${#STAGED[@]} -gt 0 ]]; then
	if command -v trufflehog >/dev/null 2>&1; then
		TMP_LIST="$(mktemp)"
		printf "%s\n" "${STAGED[@]}" >"$TMP_LIST"
		mapfile -t TO_SCAN < <(awk '{print $0}' "$TMP_LIST" | while read -r f; do [ -f "$f" ] && echo "$f"; done)
		if [[ ${#TO_SCAN[@]} -gt 0 ]]; then
			if ! trufflehog filesystem --no-update --only-verified --json "${TO_SCAN[@]}" >/dev/null 2>&1; then
				echo "[pre-commit] TruffleHog detected potential secrets in staged files." >&2
				exit 3
			fi
		else
			echo "No regular files staged. Skipping secret scan."
		fi
		rm -f "$TMP_LIST"
	else
		echo "[pre-commit] TruffleHog not installed; skipping secret scan." >&2
	fi
else
	echo "No staged files. Skipping secret scan."
fi

if has_lang python; then
	echo "[pre-commit] Running Python guard scripts..."
	run_quiet monkey_guard "$ROOT_DIR/tools/guards/monkey_guard/monkey_guard.sh"
	run_quiet hex_enforce "$ROOT_DIR/tools/guards/hex_enforce/hex_test_guards.sh"
	run_quiet fp_sheriff "$ROOT_DIR/tools/guards/fp_sheriff/find_functional_violators.sh" --paths services shared tools
	run_quiet enforce_py_size_limit "$ROOT_DIR/tools/guards/enforce_py_size_limit/py_line_check.sh"
	run_quiet private_alias_guard "$ROOT_DIR/tools/guards/private_alias_guard/run_private_alias_guard.sh"
	run_quiet third_party_sheriff "$ROOT_DIR/tools/guards/third_party_sheriff/find_heavy_tests.sh"
	run_quiet unique_enforce "$ROOT_DIR/tools/guards/unique_enforce/unique_name_guard.sh"
	run_quiet find_python_package_clashes "$ROOT_DIR/tools/guards/find_python_package_clashes.sh"
	run_quiet test_speed_enforce "$ROOT_DIR/tools/guards/test_speed_enforce/test_speed_guards.sh"
else
	echo "[pre-commit] Python not selected; skipping Python guards."
fi

if command -v python3 >/dev/null 2>&1 && [ -d "$ROOT_DIR/tools/forbidden_imports/src" ]; then
	echo "[pre-commit] Running forbidden-imports guard..."
	run_quiet forbidden_imports env PYTHONPATH="$ROOT_DIR/tools/forbidden_imports/src" python3 -m forbidden_imports.cli
fi

echo "[pre-commit] Completed successfully."
