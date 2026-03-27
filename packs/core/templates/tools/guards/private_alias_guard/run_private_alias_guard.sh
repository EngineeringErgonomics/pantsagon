#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR=""
if command -v git >/dev/null 2>&1; then
	ROOT_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
fi
if [[ -z "$ROOT_DIR" ]]; then
	ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
fi
cd "$ROOT_DIR"

SCAN_DIRS=()
for d in services shared; do
	if [[ -d "$d" ]]; then
		SCAN_DIRS+=("$d")
	fi
done
if [[ ${#SCAN_DIRS[@]} -eq 0 ]]; then
	echo "[private-alias-guard] no services/shared directories; skipping."
	exit 0
fi

echo "[private-alias-guard] scanning services/shared for private re-exports..."

# Default ignores
IGNORE_ARGS=(
	"-g" "!tests/python/**"
	"-g" "!**/__pycache__/**"
	"-g" "!**/*.md"
)

violations=()

# 1) from pkg._private import ...
while IFS= read -r line; do
	violations+=("$line | from-private-reexport")
done < <(rg -n --no-heading "${IGNORE_ARGS[@]}" -S "^\s*from\s+[^#\n]*\._[A-Za-z0-9_]+\s+import\s+" "${SCAN_DIRS[@]}" | cat)

# 2) import pkg._private as alias
while IFS= read -r line; do
	violations+=("$line | import-private-alias")
done < <(rg -n --no-heading "${IGNORE_ARGS[@]}" -S "^\s*import\s+[^#\n]*\._[A-Za-z0-9_]+\s+as\s+" "${SCAN_DIRS[@]}" | cat)

# 3) Module-proxy getattr forwarding a private module
while IFS= read -r line; do
	violations+=("$line | getattr-forward-private")
done < <(rg -n --no-heading "${IGNORE_ARGS[@]}" -S "__getattr__\s*\(.*\).*_[A-Za-z0-9_]+" "${SCAN_DIRS[@]}" | cat)

# 4) setattr(..., getattr(internal module, name)) style
while IFS= read -r line; do
	violations+=("$line | setattr-forward-private")
done < <(rg -n --no-heading "${IGNORE_ARGS[@]}" -S "setattr\(.*getattr\([^,]+\._[A-Za-z0-9_]+,\s*[A-Za-z_][A-Za-z0-9_]*\)\)" "${SCAN_DIRS[@]}" | cat)

if ((${#violations[@]} > 0)); then
	echo "[private-alias-guard] Violations detected:" >&2
	for v in "${violations[@]}"; do
		echo "  $v" >&2
	done
	printf "\nPolicy: Do NOT re-export private modules via public aliases. Promote to real public API or remove the dependency.\n" >&2
	exit 1
fi

echo "[private-alias-guard] OK (no private re-exports found)"
