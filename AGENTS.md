# Repository Guidelines

## Project Structure & Module Organization

Pantsagon is a Pants-managed Python monorepo enforcing hexagonal architecture:

\`\`\`
.
├── services/          # Service modules (e.g., services/pantsagon/src/pantsagon/)
│   └── pantsagon/     # Core CLI service
├── shared/            # Cross-service layers
│   ├── foundation/    # Domain primitives
│   ├── adapters/      # Infrastructure impls
│   └── contracts/     # Schemas (e.g., pack.schema.v1.json)
├── packs/             # Template packs (e.g., packs/core/, packs/python/)
├── docs/              # MkDocs site source
├── tests/             # Unit/integration tests
├── tools/             # Utilities (e.g., forbidden_imports/)
├── 3rdparty/          # External deps (e.g., requirements.txt)
├── scripts/           # Build helpers (e.g., generate_schema_docs.py)
├── pants.toml         # Pants config
└── pyproject.toml     # Project metadata
\`\`\`

Hexagonal layers: \`domain/\`, \`application/\`, \`adapters/\`, \`ports/\`, \`entrypoints/\`.

## Build, Test, and Development Commands

- \`pants test ::\` – Run all tests with coverage.
- \`pants run services/pantsagon:cli -- init /path/to/repo --lang python\` – Scaffold new repo.
- \`PANTSAGON_DETERMINISTIC=1 python -m pantsagon.tools.validate_packs --bundled\` – Validate packs.
- Docs: \`pip install -r docs/requirements.txt && python scripts/generate_schema_docs.py && mkdocs serve\`.
- Type check: \`pants check ::\` (Pyright).

Requires Pants (pinned in \`pants.toml\`).

## Coding Style & Naming Conventions

- Python 3.12+, 2-space indentation.
- Linting/Formatting: Ruff (\`.ruff.toml\`), Pyright (\`.pyrightconfig.json\`).
- Naming: \`snake_case\` for modules/functions; \`CamelCase\` classes; kebab-case services/packs.
- **Strict typing**: Full type annotations; no \`Any\` except boundaries. Follow [Type-System Design Guidance](#type-system-design-guidance).
- Pre-commit: \`pants lint ::\` and \`pants check ::\`.

## Type-System Design Guidance

**Anti-patterns, Failure Modes, and Corrective Patterns**

At a high level, every type-system smell reduces to one root cause:

> **Domain information is being carried in values instead of types.**

The following anti-patterns describe *how* that information is lost, *why* it matters, and *how* to restore it.

### 1. Primitive Obsession

**Definition**  
Using raw language primitives (\`string\`, \`int\`, \`float\`) to represent semantically rich domain concepts.

**What’s actually wrong**  
The compiler sees *representation*, not *meaning*. Two values that share a machine representation but differ semantically become indistinguishable.

**Failure mode**
\`\`\`python
UserId = int
TemperatureCelsius = int
\`\`\`
The compiler cannot prevent: \`sendEmail(temperature)\`.

**Corrective pattern: Value Objects / Opaque Types**
\`\`\`python
from typing import NewType
UserId = NewType('UserId', str)
TemperatureCelsius = NewType('TemperatureCelsius', int)
EmailAddress = NewType('EmailAddress', str)
\`\`\`
**Rule of thumb**: If a primitive has *domain rules*, *constraints*, or *identity*, it deserves its own type.

### 2. “Stringly Typed” Systems

**Definition**  
Control flow, configuration, or business logic depends on raw strings instead of types.

**What’s actually wrong**  
The type system has been bypassed in favor of ad-hoc symbolic encoding.

**Failure mode**
\`\`\`python
if role == "admin": ...
\`\`\`

**Corrective pattern: Closed Sets**
\`\`\`python
from enum import Enum
class Role(Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"
\`\`\`
**Rule of thumb**: If a string controls behavior, it should almost certainly be a type.

### 3. Boolean Blindness

**Definition**  
Using booleans where meaning is not self-evident at the call site.

**Failure mode**
\`\`\`python
create_user("jdoe", True, False, True)
\`\`\`

**Corrective patterns**  
1. Enums: \`EmailVerification = Enum('Verified', 'Unverified')\`.  
2. Dataclasses:  
\`\`\`python
@dataclass
class UserCreationOptions:
    role: Role
    status: AccountStatus
    notifications: NotificationPolicy
\`\`\`
**Rule of thumb**: >1 boolean param = underspecified.

### 4. Data Clumps

**Definition**  
Repeatedly passing the same group of parameters together.

**Failure mode**
\`\`\`python
move(x, y, z); rotate(x, y, z); scale(x, y, z)
\`\`\`

**Corrective pattern**
\`\`\`python
@dataclass
class Vector3:
    x: float
    y: float
    z: float
\`\`\`
**Rule of thumb**: Params that travel together → aggregate.

### 5. The “God Type” (Blob)

**Definition**  
A single type mixing unrelated responsibilities.

**Failure mode**
\`\`\`python
class User:
    password_hash: str
    def save_to_db(self): ...
    def format_for_display(self): ...
    def is_admin(self): ...
\`\`\`

**Corrective pattern**  
Split: \`User\`, \`UserRepository\`, \`UserAuthPolicy\`, \`UserViewModel\`.  
**Rule of thumb**: Multi-reason-to-change = broken.

### 6. Illegal States Are Representable

**Definition**  
Type permits impossible states.

**Failure mode**  
\`is_loading = True; is_error = True\`.

**Corrective pattern**
\`\`\`python
from typing import Union, Literal
RequestState = Union[
    Literal['loading'],
    dict[str, Any],  # success data
    Exception,       # error
]
\`\`\`
Or use \`pydantic\`/\`attrs\` for tagged unions.  
**Rule of thumb**: Need comments for combos → bad types.

### 7. Null / Optional Abuse

**Definition**  
\`None\`/\`Optional\` encodes multiple meanings.

**Corrective patterns**  
- \`Optional[T]\` → may not exist.  
- \`Result[T, E]\` (e.g., via \`returns\` lib) → failure.  
- State types for lifecycle.

**Rule of thumb**  
\`None\` = *only* “does not exist”.

### 8. Inheritance for Code Reuse

**Definition**  
Inheritance for impl sharing, not “is-a”.

**Corrective pattern**  
Composition + protocols/dataclasses.

### 9. The Casting Crutch (Downcasting)

**Corrective patterns**  
Polymorphism or structural pattern matching (\`match\` in 3.10+).

### 10. The “Any” Trap (Type Erasure)

**Corrective patterns**  
Generics, unions; eliminate post-boundary.

**Core Heuristics**  
1. Types carry intent.  
2. Impossible states unrepresentable.  
3. Closed worlds > strings.  
4. Invariants in constructors.  
5. Model states > flags.  
6. Boundary chaos, internal order.

Pyright enforces: No \`Any\` in domain; full annotations.

## Testing Guidelines

- Framework: pytest (\`pyproject.toml\`).
- Run: \`pants test :: --cov\` (80%+ coverage).
- Conventions: \`test_*\`, \`Test*\`; function-scoped async loops.

## Commit & Pull Request Guidelines

- Commits: Conventional (\`feat:\`, \`fix:\`, \`docs:\`, \`types:\`). Explain *why*.
- PRs: Link issues (\`Fixes #123\`), title/body, screenshots/UI.
- CI: \`ci.yml\` (lint/test/docs/types). \`--strict\` for CLI.

Augmented coding: Edit this \`AGENTS.md\` for AI prompts (\`--augmented-coding agents\`).

