# Repo lock: .pantsagon.toml

`.pantsagon.toml` is the single source of truth for:

- tool version
- selected packs (id/version/source)
- selected features and services
- resolved answers passed to the renderer
- strictness settings

In v1:

- pack versions are pinned and never auto-upgraded
- `add service` updates the lock deterministically
