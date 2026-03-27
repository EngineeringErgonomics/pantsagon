#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT_DIR"

HOOKS_DIR="$ROOT_DIR/.githooks"
mkdir -p "$HOOKS_DIR"

for hook in pre-commit pre-push; do
	src="$HOOKS_DIR/$hook"
	if [ ! -f "$src" ]; then
		echo "Missing hook: $src" >&2
		exit 1
	fi
	chmod +x "$src"
done

if command -v git >/dev/null 2>&1; then
	git config core.hooksPath .githooks
	echo "Git hooks installed (core.hooksPath=.githooks)."
else
	echo "git not found; unable to set hooksPath." >&2
	exit 1
fi
