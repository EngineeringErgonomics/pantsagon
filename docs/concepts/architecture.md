# Architecture

Pantsagon itself is hexagonal:

- **Domain** models `Blueprint -> PackSelection -> RenderPlan -> RepoLock -> Diagnostics`
- **Application** orchestrates `init`, `add service`, and `validate`
- **Ports** define pack discovery, rendering, workspace IO, policy checks, and command execution
- **Adapters** implement those ports (Copier renderer, filesystem workspace, bundled/local packs)

This lets Pantsagon support multiple frontends and third-party extensions without forking.
