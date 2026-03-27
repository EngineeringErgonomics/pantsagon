#!/usr/bin/env bash
# Detect tests that import real third‑party dependencies instead of fakes/doubles.
#
# Heuristics only — optimized for this repo’s layout and stubbing approach.
# Exits with code 0 when no heavy imports are found; 2 otherwise.
#
# Usage:
#   tools/guards/third_party_sheriff/find_heavy_tests.sh [--tests-dir DIR] [--summary]
#
# Notes:
# - Ignores modules that our test bootstrap stubs via test/sitecustomize.py
#   (e.g., torch_types, cupy_types, cudf_types, pyarrow, httpx_types). It also scans tests/python/test_support/_stubs
#   and reports heavy imports there separately so accidental real deps are caught.
# - Looks only at import statements in test files; it won’t detect indirect runtime
#   loads or network activity triggered by wrappers.

set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TESTS_DIR=""
SUMMARY_ONLY=false

# Parse flags (order‑independent)
while [[ $# -gt 0 ]]; do
	case "$1" in
	--tests-dir)
		shift
		TESTS_DIR="${1:-}"
		[[ -z "${TESTS_DIR}" ]] && {
			echo "error: --tests-dir requires a value" >&2
			exit 3
		}
		;;
	--summary)
		SUMMARY_ONLY=true
		;;
	*)
		echo "error: unknown argument: $1" >&2
		exit 3
		;;
	esac
	shift || true
done

if [[ -z "${TESTS_DIR}" ]]; then
	# Default to the canonical tests directory in this repo
	TESTS_DIR="${ROOT}/tests"
fi

if ! command -v rg >/dev/null 2>&1; then
	echo "error: ripgrep (rg) is required" >&2
	exit 3
fi

if [[ ! -d "${TESTS_DIR}" ]]; then
	echo "tests directory not found: ${TESTS_DIR}; skipping." >&2
	exit 0
fi

# -----------------------------------------------------------------------------
# Gather modules that are explicitly stubbed by test/sitecustomize.py
# -----------------------------------------------------------------------------
declare -A STUBBED=()
SITEC="${ROOT}/tests/sitecustomize.py"
if [[ -f "${SITEC}" ]]; then
	# sys.modules["name"] = ... → treat as stubbed
	# Also include well-known stubs that are installed via import hooks.
	while IFS= read -r mod; do
		if [[ -n "${mod}" ]]; then
			STUBBED["${mod}"]=1
		fi
	done < <({ rg -N --pcre2 -o '(?<=sys\.modules\[")([A-Za-z0-9_\.]+)(?="\])' "${SITEC}" || true; } | sort -u)
	# Import hook stubs (torch_types) that may not appear in sys.modules assignment
	STUBBED["torch"]=1
fi

# -----------------------------------------------------------------------------
# Denylist of third‑party modules that should be faked in unit tests
# (exclude those covered by STUBBED above)
# -----------------------------------------------------------------------------
DENY_CANDIDATES=(
	requests
	aiohttp
	urllib3
	boto3
	google.cloud
	googleapiclient
	azure
	kubernetes
	docker
	sqlalchemy
	psycopg2
	pymysql
	mysqlclient
	pymongo
	redis
	kafka
	confluent_kafka
	pika
	s3fs
	paramiko
	snowflake
	elasticsearch
	opensearchpy
	minio
	stripe
	twilio
	slack_sdk
	openai
	anthropic
	transformers
	selenium
	playwright
	sklearn
	pandas
	numpy
)

DENYLIST=()
for name in "${DENY_CANDIDATES[@]}"; do
	# Skip anything already stubbed by sitecustomize
	if [[ -n "${STUBBED[${name}]:-}" ]]; then
		continue
	fi
	DENYLIST+=("${name}")
done

if [[ ${#DENYLIST[@]} -eq 0 ]]; then
	echo "warn: empty denylist after excluding stubs; nothing to check" >&2
	exit 0
fi

# Build a regex like: (mod1|mod2|pkg\.sub)
DENY_REGEX="$(printf "%s\n" "${DENYLIST[@]}" | sed -E 's/([\.\+\*\^\$\|\(\)\[\]\{\}\?])/\\\\\1/g' | paste -sd '|' -)"

echo "third_party_sheriff: scanning ${TESTS_DIR}"
if [[ -f "${SITEC}" ]]; then
	echo " - recognized stubs: $(printf "%s " "${!STUBBED[@]}" | sed 's/ $//')"
fi
echo " - denylist modules: ${DENY_REGEX}"

# -----------------------------------------------------------------------------
# Search import statements in tests (excluding bootstrap), and in _stubs separately
# -----------------------------------------------------------------------------
RG_ARGS_TESTS=(
	-n -H -S --no-heading --color=never
	--glob '!**/_stubs/**'
	--glob '!**/sitecustomize.py'
	-P
	"^\s*(?:from|import)\s+(?:${DENY_REGEX})\b"
	"${TESTS_DIR}"
)

mapfile -t HITS < <(rg "${RG_ARGS_TESTS[@]}" || true)

# Also scan tests/_stubs for denylisted imports to keep stubs lightweight
mapfile -t HITS_STUBS < <(rg -n -H -S --no-heading --color=never -P "^\s*(?:from|import)\s+(?:${DENY_REGEX})\b" "${TESTS_DIR}/_stubs" 2>/dev/null || true)

if [[ ${#HITS[@]} -eq 0 && ${#HITS_STUBS[@]} -eq 0 ]]; then
	echo "✅ No heavy third‑party imports detected in tests."
	exit 0
fi

# Parse and filter to module names actually imported, account for both forms.
declare -A FILE_COUNTS=()
printf "\n❌ Potential heavy imports found (line → import):\n"
for line in "${HITS[@]}"; do
	# Format: path:lineno:code
	file="${line%%:*}"
	rest="${line#*:}"
	lno="${rest%%:*}"
	code="${rest#*:}"
	mod=""
	if [[ "${code}" =~ ^[[:space:]]*from[[:space:]]+([A-Za-z0-9_\.]+)[[:space:]]+import ]]; then
		mod="${BASH_REMATCH[1]}"
	elif [[ "${code}" =~ ^[[:space:]]*import[[:space:]]+([A-Za-z0-9_\.]+) ]]; then
		mod="${BASH_REMATCH[1]}"
	fi
	# Skip if module is covered by stubs (defensive double-check)
	if [[ -n "${STUBBED[${mod}]:-}" ]]; then
		continue
	fi
	echo " - ${file}:${lno} → ${code#*(}"
	FILE_COUNTS["${file}"]=$((${FILE_COUNTS["${file}"]:-0} + 1))
done

if [[ ${#HITS_STUBS[@]} -gt 0 ]]; then
	printf "\n⚠ Heavy imports found under tests/_stubs (avoid real deps in stubs):\n"
	for line in "${HITS_STUBS[@]}"; do
		file="${line%%:*}"
		rest="${line#*:}"
		lno="${rest%%:*}"
		code="${rest#*:}"
		echo " - ${file}:${lno} → ${code#*(}"
		FILE_COUNTS["${file}"]=$((${FILE_COUNTS["${file}"]:-0} + 1))
	done
fi

if ${SUMMARY_ONLY}; then
	printf "\nSummary (files with hits):\n"
	for f in "${!FILE_COUNTS[@]}"; do
		printf " - %s: %d\n" "${f}" "${FILE_COUNTS["${f}"]}"
	done | sort
fi

printf "\nHint: prefer repository fakes/doubles via dependency injection or tests/python/test_support/_stubs.\n"
printf "      If a module is safely stubbed in sitecustomize.py, it’s ignored here.\n"

exit 2
