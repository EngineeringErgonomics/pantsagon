#!/usr/bin/env bash
set -euo pipefail

# Limits
SRC_MAX_LINES=350
TEST_MAX_LINES=1000

# Project root
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

violations=0

# Optional allowlist of files that may exceed the limit (one path per line, project-root relative)
ALLOWLIST_FILE="$SCRIPT_DIR/ALLOWLIST.txt"
declare -a ALLOWED
if [ -f "$ALLOWLIST_FILE" ]; then
	while IFS= read -r line || [ -n "$line" ]; do
		line=${line%$'\r'}
		ALLOWED+=("$line")
	done <"$ALLOWLIST_FILE"
else
	ALLOWED=()
fi

is_allowed() {
	local rel="$1"
	for a in "${ALLOWED[@]}"; do
		if [ "$rel" = "$a" ]; then
			return 0
		fi
	done
	return 1
}

# Always check the full tree; do not depend on Git state.

check_dir() {
	local dir="$1"
	local max_lines="$2"
	if [ ! -d "$dir" ]; then
		return 0
	fi
	while IFS= read -r -d '' file; do
		# Compute project-root relative path for allowlist matching
		rel_path="${file#"$PROJECT_ROOT"/}"
		if is_allowed "$rel_path"; then
			continue
		fi
		local count
		count=$(wc -l <"$file")
		if [ "$count" -gt "$max_lines" ]; then
			echo "Error: $file has $count lines, exceeding limit $max_lines" >&2
			violations=$((violations + 1))
		fi
	done < <(find "$dir" -type f -name "*.py" -print0)
}

# Always scan standard directories (skip if missing)
check_dir "$PROJECT_ROOT/services" "$SRC_MAX_LINES"
check_dir "$PROJECT_ROOT/shared" "$SRC_MAX_LINES"
check_dir "$PROJECT_ROOT/tools" "$SRC_MAX_LINES"
check_dir "$PROJECT_ROOT/tests" "$TEST_MAX_LINES"

if [ "$violations" -gt 0 ]; then
	echo "Found $violations file(s) exceeding size limits." >&2
	exit 1
fi
exit 0
