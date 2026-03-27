#!/usr/bin/env bash
set -euo pipefail

# Detect risky top-level Python package name clashes across Pants source roots.
# Exits 1 when the same top-level package appears in multiple source roots.

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT_DIR"

python3 - <<'PY'
import glob
import os
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    print("[pkg-clash] python3/tomllib required", file=sys.stderr)
    sys.exit(2)

root = Path(".").resolve()
pt = root / "pants.toml"
if not pt.exists():
    print("[pkg-clash] pants.toml not found; skipping", file=sys.stderr)
    sys.exit(0)

data = tomllib.loads(pt.read_text(encoding="utf-8"))
patterns = data.get("source", {}).get("root_patterns", [])
patterns = [str(p).lstrip("/") for p in patterns if isinstance(p, str)]

roots = []
for pat in patterns:
    # Skip test roots for clash detection.
    if "/tests" in pat or pat.startswith("tests"):
        continue
    for match in glob.glob(pat, recursive=True):
        p = root / match
        if p.is_dir():
            roots.append(p)

if not roots:
    print("[pkg-clash] no source roots found; skipping", file=sys.stderr)
    sys.exit(0)

def is_pkg_dir(p: Path) -> bool:
    return p.is_dir() and (p / "__init__.py").exists()

owners: dict[str, set[str]] = {}
for r in roots:
    for child in r.iterdir():
        if child.name.startswith("."):
            continue
        if is_pkg_dir(child):
            owners.setdefault(child.name, set()).add(str(r))
        elif child.is_file() and child.suffix == ".py":
            owners.setdefault(child.stem, set()).add(str(r))

clashes = [(name, sorted(paths)) for name, paths in owners.items() if len(paths) > 1]
if clashes:
    print("[pkg-clash] Duplicate top-level packages detected:")
    for name, paths in sorted(clashes):
        print(f"- {name}:")
        for p in paths:
            print(f"  - {os.path.relpath(p, root)}")
    sys.exit(1)
sys.exit(0)
PY
