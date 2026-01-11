# M3 Repo Lock Fidelity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement repo lock fidelity v1: `.pantsagon.toml` full structure, pack index mapping, resolved pack/answer persistence, drift validation, and README updates.

**Architecture:** Add a pack index file (`packs/_index.json`) and a small application utility module to load/resolve packs. Centralize lock read/write/validation in `application/repo_lock.py`. `init_repo` computes pack refs + answers, writes lock into a staging workspace, renders, then commits. `validate_repo` is resolved-driven: it reads the lock, validates pack refs/availability/requirements, checks repo invariants, and emits drift diagnostics.

**Tech Stack:** Python 3.12, tomllib/tomli-w, json, PyYAML, jsonschema, pytest.

---

### Task 1: Add pack index loader + resolution tests (TDD)

**Files:**
- Create: `tests/application/test_pack_index.py`
- Create: `services/pantsagon/src/pantsagon/application/pack_index.py`
- Create: `packs/_index.json`

**Step 1: Write failing tests**

```python
import json
from pathlib import Path

from pantsagon.application.pack_index import load_pack_index, resolve_pack_ids


def test_resolve_pack_ids_from_index(tmp_path):
    index_path = tmp_path / "_index.json"
    index_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "base_packs": ["pantsagon.core"],
                "languages": {"python": ["pantsagon.python"]},
                "features": {"openapi": ["pantsagon.openapi"], "docker": ["pantsagon.docker"]},
            }
        ),
        encoding="utf-8",
    )
    index = load_pack_index(index_path)
    result = resolve_pack_ids(index, languages=["python"], features=["openapi", "docker"])
    assert result.diagnostics == []
    assert result.value == [
        "pantsagon.core",
        "pantsagon.python",
        "pantsagon.openapi",
        "pantsagon.docker",
    ]


def test_resolve_pack_ids_unknown_language(tmp_path):
    index_path = tmp_path / "_index.json"
    index_path.write_text(
        json.dumps({"schema_version": 1, "base_packs": ["pantsagon.core"], "languages": {}, "features": {}}),
        encoding="utf-8",
    )
    index = load_pack_index(index_path)
    result = resolve_pack_ids(index, languages=["elixir"], features=[])
    assert any(d.code == "PACK_INDEX_UNKNOWN_LANGUAGE" for d in result.diagnostics)
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/application/test_pack_index.py -q`

Expected: FAIL with `ModuleNotFoundError` for `pantsagon.application.pack_index`.

**Step 3: Commit**

```bash
git add tests/application/test_pack_index.py
git commit -m "test: add pack index resolution tests"
```

---

### Task 2: Implement pack index loader + resolution

**Files:**
- Create: `services/pantsagon/src/pantsagon/application/pack_index.py`
- Create: `packs/_index.json`

**Step 1: Implement `pack_index.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from pantsagon.domain.diagnostics import Diagnostic, Severity
from pantsagon.domain.result import Result


@dataclass(frozen=True)
class PackIndex:
    base_packs: list[str]
    languages: dict[str, list[str]]
    features: dict[str, list[str]]


def load_pack_index(path: Path) -> PackIndex:
    raw = json.loads(path.read_text(encoding="utf-8"))
    base = list(raw.get("base_packs") or [])
    languages = dict(raw.get("languages") or {})
    features = dict(raw.get("features") or {})
    return PackIndex(base_packs=base, languages=languages, features=features)


def resolve_pack_ids(index: PackIndex, languages: list[str], features: list[str]) -> Result[list[str]]:
    diagnostics: list[Diagnostic] = []
    packs: list[str] = []
    packs.extend(index.base_packs)

    for lang in languages:
        if lang not in index.languages:
            diagnostics.append(
                Diagnostic(
                    code="PACK_INDEX_UNKNOWN_LANGUAGE",
                    rule="pack.index.language",
                    severity=Severity.ERROR,
                    message=f"Unknown language in pack index: {lang}",
                )
            )
            continue
        packs.extend(index.languages[lang])

    for feature in features:
        if feature not in index.features:
            diagnostics.append(
                Diagnostic(
                    code="PACK_INDEX_UNKNOWN_FEATURE",
                    rule="pack.index.feature",
                    severity=Severity.ERROR,
                    message=f"Unknown feature in pack index: {feature}",
                )
            )
            continue
        packs.extend(index.features[feature])

    seen: set[str] = set()
    ordered: list[str] = []
    for pack_id in packs:
        if pack_id not in seen:
            seen.add(pack_id)
            ordered.append(pack_id)

    return Result(value=ordered, diagnostics=diagnostics)
```

**Step 2: Create `packs/_index.json`**

```json
{
  "schema_version": 1,
  "base_packs": ["pantsagon.core"],
  "languages": {
    "python": ["pantsagon.python"]
  },
  "features": {
    "openapi": ["pantsagon.openapi"],
    "docker": ["pantsagon.docker"]
  }
}
```

**Step 3: Run tests**

Run: `pytest tests/application/test_pack_index.py -q`

Expected: PASS

**Step 4: Commit**

```bash
git add services/pantsagon/src/pantsagon/application/pack_index.py packs/_index.json
git commit -m "feat: add pack index mapping"
```

---

### Task 3: Add repo lock read/write tests (TDD)

**Files:**
- Create: `tests/application/test_repo_lock.py`
- Create: `services/pantsagon/src/pantsagon/application/repo_lock.py`

**Step 1: Write failing tests**

```python
import tomllib
from pathlib import Path

from pantsagon.application.repo_lock import read_lock, write_lock


def test_read_lock_missing(tmp_path):
    result = read_lock(tmp_path / ".pantsagon.toml")
    assert any(d.code == "LOCK_MISSING" for d in result.diagnostics)


def test_write_lock_roundtrip(tmp_path):
    lock = {
        "tool": {"name": "pantsagon", "version": "0.1.0"},
        "settings": {"renderer": "copier", "strict": False, "strict_manifest": True, "allow_hooks": False},
        "selection": {"languages": ["python"], "features": ["openapi"], "services": ["svc"], "augmented_coding": "none"},
        "resolved": {"packs": [{"id": "pantsagon.core", "version": "1.0.0", "source": "bundled"}], "answers": {"repo_name": "demo"}},
    }
    path = tmp_path / ".pantsagon.toml"
    write_lock(path, lock)
    parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    assert parsed["tool"]["name"] == "pantsagon"
    assert parsed["resolved"]["packs"][0]["id"] == "pantsagon.core"
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/application/test_repo_lock.py -q`

Expected: FAIL with import error or missing functions.

**Step 3: Commit**

```bash
git add tests/application/test_repo_lock.py
git commit -m "test: add repo lock io tests"
```

---

### Task 4: Implement repo lock read/write + pack ordering

**Files:**
- Create: `services/pantsagon/src/pantsagon/application/repo_lock.py`

**Step 1: Implement lock helpers**

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any

from pantsagon.domain.diagnostics import Diagnostic, FileLocation, Severity
from pantsagon.domain.result import Result


LockDict = dict[str, Any]


def read_lock(path: Path) -> Result[LockDict]:
    if not path.exists():
        return Result(diagnostics=[Diagnostic(code="LOCK_MISSING", rule="lock.exists", severity=Severity.ERROR, message=".pantsagon.toml not found")])
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return Result(
            diagnostics=[
                Diagnostic(
                    code="LOCK_PARSE_FAILED",
                    rule="lock.parse",
                    severity=Severity.ERROR,
                    message=str(e),
                    location=FileLocation(str(path)),
                )
            ]
        )
    return Result(value=data)


def write_lock(path: Path, lock: LockDict) -> None:
    import tomli_w

    content = tomli_w.dumps(lock)
    path.write_text(content, encoding="utf-8")
```

**Step 2: Run tests**

Run: `pytest tests/application/test_repo_lock.py -q`

Expected: PASS

**Step 3: Commit**

```bash
git add services/pantsagon/src/pantsagon/application/repo_lock.py
git commit -m "feat: add repo lock io helpers"
```

---

### Task 5: Add init_repo lock fidelity tests (TDD)

**Files:**
- Create: `tests/application/test_init_repo_lock.py`
- Modify: `services/pantsagon/src/pantsagon/application/init_repo.py`

**Step 1: Write failing test**

```python
import tomllib
from pantsagon.application.init_repo import init_repo


def test_init_repo_writes_full_lock(tmp_path):
    init_repo(
        repo_path=tmp_path,
        languages=["python"],
        services=["monitors"],
        features=["openapi"],
        renderer="copier",
    )
    lock = tomllib.loads((tmp_path / ".pantsagon.toml").read_text(encoding="utf-8"))
    assert "tool" in lock
    assert "settings" in lock
    assert "selection" in lock
    assert "resolved" in lock
    assert lock["resolved"]["packs"]
    assert "answers" in lock["resolved"]
```

**Step 2: Run test to verify failure**

Run: `pytest tests/application/test_init_repo_lock.py -q`

Expected: FAIL because init_repo writes minimal lock.

**Step 3: Commit**

```bash
git add tests/application/test_init_repo_lock.py
git commit -m "test: add init repo lock structure test"
```

---

### Task 6: Implement init_repo lock fidelity + staging

**Files:**
- Modify: `services/pantsagon/src/pantsagon/application/init_repo.py`
- Modify: `services/pantsagon/src/pantsagon/adapters/workspace/filesystem.py` (if needed)
- Modify: `services/pantsagon/src/pantsagon/application/pack_index.py`
- Modify: `services/pantsagon/src/pantsagon/adapters/pack_catalog/bundled.py`

**Step 1: Implement staging flow**

- Create `FilesystemWorkspace(repo_path)`
- `stage = workspace.begin_transaction()`
- Write `.pantsagon.toml` into `stage` (using `write_lock`)
- Write minimal `pants.toml` into `stage`
- Render packs into `stage` if available (optional for v1)
- Commit stage via `workspace.commit(stage)`

**Step 2: Resolve packs and answers**

- Load pack index from `packs/_index.json`
- Resolve pack IDs from selection
- Load each pack manifest to get version and requires
- Build `resolved.packs` with `id/version/source` (source = bundled)
- Persist `resolved.answers` = `{repo_name, service_name}`
- Ensure deterministic ordering via topological sort on `requires.packs` then id

**Step 3: Update init_repo implementation**

- Use `write_lock` to serialize full lock dict
- Return Result with diagnostics if resolution fails

**Step 4: Run test**

Run: `pytest tests/application/test_init_repo_lock.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add services/pantsagon/src/pantsagon/application/init_repo.py
git commit -m "feat: write full repo lock during init"
```

---

### Task 7: Add validate_repo drift tests (TDD)

**Files:**
- Create: `tests/application/test_validate_repo.py`

**Step 1: Write failing tests**

```python
import tomllib
from pathlib import Path

from pantsagon.application.init_repo import init_repo
from pantsagon.application.validate_repo import validate_repo


def test_validate_repo_missing_lock(tmp_path):
    result = validate_repo(repo_path=tmp_path)
    assert any(d.code == "LOCK_MISSING" for d in result.diagnostics)


def test_validate_repo_missing_service_dir(tmp_path):
    init_repo(repo_path=tmp_path, languages=["python"], services=["missing"], features=[], renderer="copier")
    # Remove service dir if created
    svc_dir = tmp_path / "services" / "missing"
    if svc_dir.exists():
        for p in svc_dir.rglob("*"):
            if p.is_file():
                p.unlink()
        svc_dir.rmdir()
    result = validate_repo(repo_path=tmp_path)
    assert any(d.code == "REPO_SERVICE_MISSING" for d in result.diagnostics)


def test_validate_repo_pack_not_found(tmp_path):
    init_repo(repo_path=tmp_path, languages=["python"], services=["svc"], features=[], renderer="copier")
    lock_path = tmp_path / ".pantsagon.toml"
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    lock["resolved"]["packs"][0]["id"] = "pantsagon.missing"
    lock_path.write_text("".join(["[tool]\nname=\"pantsagon\"\nversion=\"0.1.0\"\n"]))
    # overwrite with tampered lock for simplicity in test
    import tomli_w
    lock_path.write_text(tomli_w.dumps(lock), encoding="utf-8")

    result = validate_repo(repo_path=tmp_path)
    assert any(d.code == "PACK_NOT_FOUND" for d in result.diagnostics)
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/application/test_validate_repo.py -q`

Expected: FAIL because validate_repo is stub.

**Step 3: Commit**

```bash
git add tests/application/test_validate_repo.py
git commit -m "test: add validate repo drift tests"
```

---

### Task 8: Implement validate_repo structural drift (B)

**Files:**
- Modify: `services/pantsagon/src/pantsagon/application/validate_repo.py`
- Modify: `services/pantsagon/src/pantsagon/application/repo_lock.py`
- Modify: `services/pantsagon/src/pantsagon/application/pack_index.py`

**Step 1: Implement `validate_repo`**

- Use `read_lock` to parse lock
- Validate presence of `tool` and `resolved.packs` (emit `LOCK_SECTION_MISSING`)
- Validate resolved pack list integrity (unique ids, required fields)
- For each pack ref:
  - resolve pack path (bundled => `packs/<name>`; local => `location`)
  - if missing, emit `PACK_NOT_FOUND`
  - load manifest and validate with `PackPolicyEngine`
  - check `requires.packs` satisfied by resolved set
- Check service directories for each `selection.services` if present
- If `pantsagon.python` in resolved packs, ensure service layer dirs exist
- If selection is present, ensure selection languages/features are compatible with resolved packs (mapping in index)

**Step 2: Run tests**

Run: `pytest tests/application/test_validate_repo.py -q`

Expected: PASS

**Step 3: Commit**

```bash
git add services/pantsagon/src/pantsagon/application/validate_repo.py services/pantsagon/src/pantsagon/application/repo_lock.py
git commit -m "feat: validate repo lock drift"
```

---

### Task 9: Update diagnostics codes + regenerate docs (if needed)

**Files:**
- Modify: `pantsagon/diagnostics/codes.yaml`
- Modify: `docs/reference/diagnostic-codes.md` (generated)

**Step 1: Add codes**

Add entries for:
- `LOCK_MISSING`, `LOCK_PARSE_FAILED`, `LOCK_SECTION_MISSING`
- `PACK_INDEX_UNKNOWN_LANGUAGE`, `PACK_INDEX_UNKNOWN_FEATURE`
- `REPO_SERVICE_MISSING`, `REPO_LAYER_MISSING`

**Step 2: Regenerate docs**

Run:
```
python scripts/generate_diagnostic_codes.py
```

**Step 3: Commit**

```bash
git add pantsagon/diagnostics/codes.yaml docs/reference/diagnostic-codes.md
git commit -m "docs: add lock drift diagnostics"
```

---

### Task 10: Update README with lock structure

**Files:**
- Modify: `README.md`

**Step 1: Add `.pantsagon.toml` structure example**

Include snippet:

```toml
[tool]
name = "pantsagon"
version = "0.1.0"

[settings]
renderer = "copier"
strict = false
strict_manifest = true
allow_hooks = false

[selection]
languages = ["python"]
features = ["openapi", "docker"]
services = ["monitors", "governance"]
augmented_coding = "none"

[[resolved.packs]]
id = "pantsagon.core"
version = "1.0.0"
source = "bundled"

[resolved.answers]
repo_name = "my-repo"
service_name = "monitors"
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document repo lock structure"
```

---

### Task 11: Verification

Run:

```bash
pytest -q
```

Expected: All tests pass.

