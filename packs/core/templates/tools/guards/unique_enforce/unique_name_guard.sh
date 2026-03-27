#!/usr/bin/env bash
set -euo pipefail

# Unique module ownership guard.
# Fails when the same Python module is owned by multiple roots or by both
# a .py and .pyi in ways that cause Pants dependency inference ambiguity.
#
# No config fallbacks: this script requires a readable pants.toml and python3.

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
	echo "[unique-guard] python3 not found in PATH; install it and retry." >&2
	exit 2
fi

CONFIG_DIR="${UNIQUE_GUARD_DIR:-$ROOT_DIR/tools/guards/unique_enforce}"
CONFIG_FILE="$CONFIG_DIR/unique_guard_config.json"
export CONFIG_FILE # used by the Python snippet below

python3 - "$CONFIG_FILE" <<'PY'
import json, sys, fnmatch
from pathlib import Path

def fail(msg: str) -> None:
    print(f"[unique-guard] {msg}", file=sys.stderr)
    sys.exit(2)

try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        fail("tomllib not available; install tomli for Python < 3.11")

ROOT = Path('.').resolve()
cfg_arg = sys.argv[1] if len(sys.argv) > 1 else ""
cfg_path = Path(cfg_arg) if cfg_arg else Path("")

def load_config() -> dict:
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text())
        except Exception as e:
            fail(f"invalid JSON in {cfg_path}: {e}")
    return {}

cfg = load_config()

def pants_roots() -> list[str]:
    override = cfg.get('roots_override') or []
    if override:
        # Require explicit strings
        roots = [str(x) for x in override if isinstance(x, str)]
        if not roots:
            fail("roots_override provided but empty/invalid")
        return roots
    pt = Path('pants.toml')
    if not pt.exists():
        fail("pants.toml not found; cannot determine source roots")
    try:
        data = tomllib.loads(pt.read_text())
        roots = data.get('source', {}).get('root_patterns', [])
        roots = [str(r).lstrip('/') for r in roots if isinstance(r, str)]
        if not roots:
            fail("[source].root_patterns empty in pants.toml")
        return roots
    except Exception as e:
        fail(f"cannot parse pants.toml: {e}")

roots = pants_roots()

# Normalize to existing directories only (keep order)
roots = [r for r in roots if (ROOT / r).is_dir()]
if not roots:
    fail("no existing source roots resolved from configuration")

IGNORE = [str(x) for x in (cfg.get('ignore_globs') or []) if isinstance(x, str)]
ALLOW_MOD_GLOBS = [str(x) for x in (cfg.get('allow_module_globs') or []) if isinstance(x, str)]

def ignored(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    abs_path = path.resolve().as_posix()
    for g in IGNORE:
        if fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(abs_path, g):
            return True
    return False

def module_key(root: str, file: Path) -> tuple[str, str]:
    # Return (module_path, ext) without suffix; path separators as '/'
    rel = file.relative_to(ROOT / root)
    if rel.name == '__init__.py' or rel.name == '__init__.pyi':
        # package module; treat module as directory path without '/__init__'
        mod = rel.parent.as_posix()
    else:
        mod = rel.with_suffix('').as_posix()
    return (mod, file.suffix)

owners: dict[str, list[tuple[str, str, str]]] = {}
for root in roots:
    base = ROOT / root
    for f in base.rglob('*.py'):
        if ignored(f):
            continue
        mk = module_key(root, f)
        owners.setdefault(mk[0], []).append((root, mk[1], str(f)))
    for f in base.rglob('*.pyi'):
        if ignored(f):
            continue
        mk = module_key(root, f)
        owners.setdefault(mk[0], []).append((root, mk[1], str(f)))

def allowed_mod(mod: str) -> bool:
    for g in ALLOW_MOD_GLOBS:
        if fnmatch.fnmatch(mod, g):
            return True
    return False

def is_pkg_init(path_str: str) -> bool:
    name = Path(path_str).name
    return name == '__init__.py' or name == '__init__.pyi'

clashes = []
for mod, lst in owners.items():
    if allowed_mod(mod):
        continue
    roots_set = {r for (r, _, _) in lst}
    exts = {e for (_, e, _) in lst}
    has_pkg_init = any(is_pkg_init(fp) for (_, _, fp) in lst)
    has_module_file = any(not is_pkg_init(fp) for (_, _, fp) in lst)
    pkg_module_collision = has_pkg_init and has_module_file
    # Cross-root duplicate or both .py and .pyi owners cause ambiguity
    if len(lst) > 1 and (
        len(roots_set) > 1
        or ('.py' in exts and '.pyi' in exts)
        or pkg_module_collision
    ):
        clashes.append((mod, lst))

if clashes:
    print("# Unique Module Guard Report\n")
    print("Found modules with ambiguous ownership (cross-root or .py/.pyi):\n")
    for mod, lst in sorted(clashes):
        print(f"- {mod}")
        for root, ext, fpath in sorted(lst):
            print(f"  - [{ext}] {root}: {fpath}")
        # Heuristic suggestions
        src_like = [fp for r, _, fp in lst if r.startswith('services/')]
        tool_like = [fp for r, _, fp in lst if r.startswith('tools/')]
        typ_like = [fp for r, _, fp in lst if r.startswith('typings')]
        if src_like and (tool_like or typ_like):
            print("  Suggested BUILD fixes (on importers of this module):")
            for s in src_like[:1]:
                # Prefer the first src implementation; ignore other owners
                print(f"    - Depend on: \"{s}\"")
            for t in tool_like:
                print(f"    - Ignore: !{t}")
            for t in typ_like:
                print(f"    - Ignore: !{t}")
        print()
    sys.exit(1)

print("# Unique Module Guard Report\n\nNo clashes found.")
sys.exit(0)
PY
