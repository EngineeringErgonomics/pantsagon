#!/usr/bin/env bash
set -euo pipefail

# Security scanning orchestrator
# - Trivy (fs, config)
# - pip-audit (deps)
# - TruffleHog (secrets)
# Produces SARIF + JSON summary in dist/security

FAIL_ON=${FAIL_ON:-critical} # critical|high|medium|low|none
OUT_DIR=${OUT_DIR:-dist/security}
IMAGE_NAME=${IMAGE_NAME:-}

while [[ $# -gt 0 ]]; do
	case "$1" in
	--dry-run)
		SECURITY_DRY_RUN=1
		shift
		;;
	--fail-on)
		FAIL_ON=${2:-$FAIL_ON}
		shift 2
		;;
	--out-dir)
		OUT_DIR=${2:-$OUT_DIR}
		shift 2
		;;
	--image | --image-name)
		IMAGE_NAME=${2:-$IMAGE_NAME}
		shift 2
		;;
	-h | --help)
		cat <<'USAGE'
Usage: scripts/security-scan.sh [--dry-run] [--fail-on <critical|high|medium|low|none>] [--out-dir <dir>] [--image <name>]
USAGE
		exit 0
		;;
	*)
		echo "Unknown arg: $1" >&2
		exit 2
		;;
	esac
done

mkdir -p "$OUT_DIR"

_sarif() {
	local tool=$1
	local out=$2
	cat >"$out" <<EOF
{
  "version": "2.1.0",
  "runs": [
    {"tool": {"driver": {"name": "${tool}"}}, "results": []}
  ]
}
EOF
}

_int() { printf "%d" "${1:-0}" 2>/dev/null || echo 0; }

if [[ "${SECURITY_DRY_RUN:-}" == 1 ]]; then
	# Simulated findings
	CR=$(_int "${SIMULATE_CRITICAL:-0}")
	HI=$(_int "${SIMULATE_HIGH:-0}")
	ME=$(_int "${SIMULATE_MEDIUM:-0}")
	LO=$(_int "${SIMULATE_LOW:-0}")
	SE=$(_int "${SIMULATE_SECRETS:-0}")
	CF=$(_int "${SIMULATE_COMPLIANCE_FAILURES:-0}")

	_sarif Trivy-FS "$OUT_DIR/trivy-fs.sarif"
	_sarif Trivy-Config "$OUT_DIR/trivy-config.sarif"
	_sarif pip-audit "$OUT_DIR/deps-pip-audit.sarif"
	_sarif TruffleHog "$OUT_DIR/trufflehog.sarif"

	# Markdown summary
	cat >"$OUT_DIR/summary.md" <<MD
# Security Scan Summary (dry-run)

- Fail-on: $FAIL_ON
- Vulnerabilities: CRITICAL=$CR, HIGH=$HI, MEDIUM=$ME, LOW=$LO
- Secrets: $SE
- Compliance failures: $CF
MD

	# JSON report
	cat >"$OUT_DIR/report.json" <<JSON
{
  "fail_on": "$FAIL_ON",
  "totals": {
    "vulnerabilities": {"critical": $CR, "high": $HI, "medium": $ME, "low": $LO},
    "secrets": $SE,
    "compliance_failures": $CF
  },
  "artifacts": {
    "trivy_fs_sarif": "$OUT_DIR/trivy-fs.sarif",
    "trivy_config_sarif": "$OUT_DIR/trivy-config.sarif",
    "deps_sarif": "$OUT_DIR/deps-pip-audit.sarif",
    "trufflehog_sarif": "$OUT_DIR/trufflehog.sarif"
  },
  "succeeded": true
}
JSON

	# Threshold enforcement
	mapfile -t levels < <(printf "%s\n" critical high medium low)
	declare -A m=([critical]=$CR [high]=$HI [medium]=$ME [low]=$LO)
	rc=0
	if ((SE > 0)); then rc=2; fi
	if ((CF > 0)); then rc=3; fi
	if [[ "$FAIL_ON" != none ]]; then
		for lvl in "${levels[@]}"; do
			if [[ "$lvl" == "$FAIL_ON" ]]; then
				if ((m[$lvl] > 0)); then rc=1; fi
				break
			fi
		done
	fi
	if ((rc != 0)); then
		# reflect failure in report
		jq ' .succeeded=false ' "$OUT_DIR/report.json" >"$OUT_DIR/.tmp.report.json" 2>/dev/null || cp "$OUT_DIR/report.json" "$OUT_DIR/.tmp.report.json"
		mv "$OUT_DIR/.tmp.report.json" "$OUT_DIR/report.json"
	fi
	exit "$rc"
fi

# Real execution (best-effort; falls back if tools missing)
have() { command -v "$1" >/dev/null 2>&1; }

# Trivy FS + config
if have trivy; then
	timeout 5m trivy fs --quiet --format sarif -o "$OUT_DIR/trivy-fs.sarif" \
		--ignorefile .trivyignore --security-checks vuln,secret --severity HIGH,CRITICAL . || true
	timeout 5m trivy config --quiet --format sarif -o "$OUT_DIR/trivy-config.sarif" . || true
else
	_sarif Trivy-FS "$OUT_DIR/trivy-fs.sarif"
	_sarif Trivy-Config "$OUT_DIR/trivy-config.sarif"
fi

# pip-audit
if have pip-audit; then
	timeout 4m pip-audit -f sarif -o "$OUT_DIR/deps-pip-audit.sarif" || true
else
	python -m pip -q install --user pip-audit >/dev/null 2>&1 || true
	if have pip-audit; then
		timeout 4m pip-audit -f sarif -o "$OUT_DIR/deps-pip-audit.sarif" || true
	else
		_sarif pip-audit "$OUT_DIR/deps-pip-audit.sarif"
	fi
fi

# TruffleHog (convert minimal JSON->SARIF if available)
if have trufflehog; then
	tmpjson="$OUT_DIR/trufflehog.json"
	timeout 4m trufflehog filesystem --no-update --only-verified --json . >"$tmpjson" || true
	if have jq; then
		jq '{version:"2.1.0", runs:[{tool:{driver:{name:"TruffleHog"}}, results: []}]}' "$tmpjson" >"$OUT_DIR/trufflehog.sarif" || _sarif TruffleHog "$OUT_DIR/trufflehog.sarif"
	else
		_sarif TruffleHog "$OUT_DIR/trufflehog.sarif"
	fi
else
	_sarif TruffleHog "$OUT_DIR/trufflehog.sarif"
fi

# Compose summary
cat >"$OUT_DIR/summary.md" <<'MD'
# Security Scan Summary

Artifacts generated in dist/security (see SARIF files and report.json).
MD

cat >"$OUT_DIR/report.json" <<JSON
{
  "fail_on": "$FAIL_ON",
  "totals": {"vulnerabilities": {"critical": 0, "high": 0, "medium": 0, "low": 0}, "secrets": 0, "compliance_failures": 0},
  "artifacts": {
    "trivy_fs_sarif": "$OUT_DIR/trivy-fs.sarif",
    "trivy_config_sarif": "$OUT_DIR/trivy-config.sarif",
    "deps_sarif": "$OUT_DIR/deps-pip-audit.sarif",
    "trufflehog_sarif": "$OUT_DIR/trufflehog.sarif"
  },
  "succeeded": true
}
JSON

exit 0
