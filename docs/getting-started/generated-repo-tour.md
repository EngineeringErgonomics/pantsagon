# Generated repo tour

A generated repo has these top-level areas:

- `services/` - independently-deployable services
- `shared/foundation/` - pure primitives, globally allowed
- `shared/adapters/` - reusable integrations (allowlisted)
- `tools/` - repo-owned checks (forbidden imports, validators)
- `.pantsagon.toml` - pack pins and answers (source of truth)

Each service follows:

- `domain/`: pure business rules
- `application/`: use-cases
- `adapters/`: IO implementations
- `entrypoints/`: CLI/HTTP/worker wiring

The repo is designed so layering is enforced by Pants dependency rules.
