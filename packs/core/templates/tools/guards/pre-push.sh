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
	echo "[pre-push] ${name}: running... (log: $logfile)"
	if "$@" >"$logfile" 2>&1; then
		echo "[pre-push] ${name}: ok (log: $logfile)"
	else
		local ec=$?
		echo "[pre-push] ${name}: FAILED (exit ${ec}). Showing last 200 lines:"
		tail -n 200 "$logfile" || true
		echo "[pre-push] Full log: $logfile"
		exit "$ec"
	fi
}

if has_lang python; then
	echo "[pre-push] Running Python guard scripts..."
	run_quiet size_check "$ROOT_DIR/tools/guards/enforce_py_size_limit/py_line_check.sh"
	run_quiet unique_guard "$ROOT_DIR/tools/guards/unique_enforce/unique_name_guard.sh"
	run_quiet monkey_guard "$ROOT_DIR/tools/guards/monkey_guard/monkey_guard.sh"
	run_quiet test_speed_guard "$ROOT_DIR/tools/guards/test_speed_enforce/test_speed_guards.sh"
else
	echo "[pre-push] Python not selected; skipping Python guards."
fi

if [[ -n "$PANTS" && " $LANGS " == *" python "* ]]; then
	echo "[pre-push] Running pants test..."
	run_quiet tests "$PANTS" --no-pantsd --no-watch-filesystem test ::
else
	echo "[pre-push] pants not available or python not selected; skipping tests."
fi

echo "[pre-push] Completed successfully."
