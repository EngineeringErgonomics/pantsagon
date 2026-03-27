Private Alias Guard — Design Spec

Purpose
- Enforce the policy: “Do NOT replace remaining private imports with public aliases. Things are either public or private — no masking via re-exports.”
- Detect attempts to re-export private modules (names with a leading underscore in any path segment) through public modules (e.g., package __init__.py or other public-facing modules) to hide private usage.

Scope
- Scan source tree under services (configurable).
- Exclude tests (tests/python), test support, and generated typings by default (configurable allowlist/ignore globs).
- Run in pre-push hook and CI.

Signal (Violations)
Flag any of the following patterns in public modules (not in tests) when the referenced module path contains a private segment (e.g., _internal, _private, _foo):

1) Re-export via import/star import
   - from pkg._private import *
   - from ._internal import *
   - import pkg._internal as public_name
   - from pkg import _internal as public_name

2) Re-export via named import that appears to create a public alias
   - from pkg._private import Name  # then exposed as part of public API
   - from ._private import Name as Name
   - import pkg._private as _p; Name = _p.Name

3) Re-export via __all__
   - __all__ = ["Name", ...] where Name originates from a private module path
   - __all__.append("Name") where Name comes from a private module path

4) Re-export via module proxy helpers
   - def __getattr__(name): return pkg._private.__getattr__(name)
   - setattr(sys.modules[__name__], name, getattr(pkg._private, name))

5) Public "+module facade+" that forwards to a private module
   - Any module whose top-level code assigns attributes or functions from a private module onto itself (assignments at module scope) to present a public surface.

Heuristics for “public module”
- File path does NOT contain: tests/python/, test_support/, _stubs/, typings/, __pycache__, .generated, .proto, or any configured ignore glob.
- File name is __init__.py or does not start with an underscore.

Allowances (configurable)
- Tests and test support under: tests/python/** (default)
- Typings and stubs: typings/** and services/**.pyi (default)
- Specific allowlist globs for legacy exceptions (JSON config allowlist)
- Inline suppression (line-level):
  - # private-alias-guard: ignore[reexport]

Suggested CLI/Config Interface

Config file (JSON), default path: tools/guards/private_alias_guard/private_alias_guard_config.json
- source_root: "services"
- tests_root: "tests/python"
- ignore_globs: ["**/.git/**", "**/__pycache__/**", "**/*.md", "typings/**"]
- allowlist: ["alpha_discovery/legacy_public_api/__init__.py"]
- suppression_token: "private-alias-guard: ignore[reexport]"
- private_segment_regex: "(?:^|\.)_\w+"  (any path segment beginning with underscore)

Exit behavior
- Exit 1 if any violation is found (after printing a concise report with file:line: reason). Exit 0 otherwise.

Detection Strategy (implementation outline)
1) Candidate file selection
   - Enumerate all *.py and *.pyi under source_root excluding ignore_globs and tests_root.
   - Exclude files whose basename starts with "_" (treated as private).

2) Line-level scans (regex + minimal parsing)
   Patterns (Python regex with named groups):
   - Star import from private:
     ^\s*from\s+(?P<mod>[\w\.]+)\s+import\s+\*\s*(#.*)?$
   - Private module segment detection:
     Use private_segment_regex against mod to decide if it contains a private segment.
   - Named import from private:
     ^\s*from\s+(?P<mod>[\w\.]+)\s+import\s+(?P<names>.+)$
     Split names on ","; any “as Name” form retains original symbol.
   - Import aliasing:
     ^\s*import\s+(?P<mod>[\w\.]+)\s+as\s+(?P<alias>\w+)\s*(#.*)?$
   - Assignment-based alias:
     ^\s*(?P<name>\w+)\s*=\s*(?P<mod>[\w\.]+)\.(?P<attr>\w+)\s*(#.*)?$
     Resolve if mod contains a private segment AND the assignment occurs at module scope.
   - __all__ population (collect context):
     __all__\s*=\s*\[(?P<items>[^\]]*)\]
     or __all__\.append\((?P<item>\w+)\)
     If a name listed in __all__ was imported from a private module in this file, flag.

3) Suppression and allowlist
   - Skip any line containing the suppression token.
   - Skip files matching allowlist globs.

4) Reporting
   - Print “file:line: code: message”. Suggested code: PRIV-ALIAS-REXPORT.
   - Include a short recommendation: “Promote to public API or remove dependency; do not re-export private modules.”

Examples

Violations:
- services/example/src/pkg/__init__.py
  from ._internal import Foo  # PRIV-ALIAS-REXPORT: re-export from private path
  __all__ = ["Foo"]

- services/example/src/pkg/api.py
  import pkg._private as _p  # PRIV-ALIAS-REXPORT
  Bar = _p.Bar

- services/example/src/pkg/__init__.py
  def __getattr__(name: str):  # PRIV-ALIAS-REXPORT
      from . import _internal
      return getattr(_internal, name)

Allowed:
- tests/python/test_support/
  from alpha_discovery.pkg._private import Foo  # tests are excluded

- services/example/src/pkg/_internal.py
  (Private module contents — ignored by guard)

Integrations
- Add a simple runner script (e.g., tools/guards/private_alias_guard/run_private_alias_guard.sh) that implements the above and returns non-zero on violations.
- Wire into scripts/pre-push.sh between file-size check and typecheck.
- Support HEX_GUARD_CONFIG-like override variable PRIVATE_ALIAS_GUARD_CONFIG to customize per-repo.

Non-goals
- This checker is not a full Python parser; it relies on robust regex and light state. Complex dynamic re-export patterns may require human review.

Performance
- Use ripgrep/fd to shortlist Python files and lines, then awk/python to post-process per file.
- Default execution time: sub-second to a few seconds on this repo size.
