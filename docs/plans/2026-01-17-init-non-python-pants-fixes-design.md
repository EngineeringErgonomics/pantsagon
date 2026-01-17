# Init Non-Python Pants Fixes Design

**Goal:** Ensure repos initialized for TypeScript, Rust, and Go include required Python tooling/backends (per user choice), remove pants.toml whitespace artifacts, use the Pants GitHub Action in CI, and avoid executable BUILD files.

**Architecture:** The core pack remains the single source of global repo scaffolding (pants.toml, CI workflow, guard tooling). Language-specific packs only add language layouts. For non-Python repos, we still render Python config files and enable Python backends to support guard tooling and Python-based scripts, but we do not add non-selected language backends. We also normalize template whitespace with Jinja whitespace controls so generated pants.toml is clean and deterministic.

**Components:**
- `packs/core/templates/pants.toml.jinja`: Build backend lists and root patterns in Jinja variables, then render them via loops. This prevents blank lines when conditionals are false. Always include Python, ruff, and pyright backends, plus `[python]`, `[python-infer]`, `[ruff]`, and `[pyright]` sections with minimal defaults. Conditionally add only the selected language backends (TS/Rust/Go) and optional features (Docker).
- `packs/core/templates/.github/workflows/ci.yml.jinja`: Replace pip install with `pantsbuild/actions/init-pants@v10`, keeping the lint/check/test steps.
- `services/pantsagon/src/pantsagon/application/init_repo.py`: When setting executable bits in `tools/guards` and `.githooks`, only chmod files that contain a shebang (`#!`) so BUILD and config files remain non-executable.

**Data Flow:** `init` resolves packs, renders the core pack first, then renders service-scoped packs. The templates drive file contents. After render, post-init setup installs hooks and sets executable bits. The change ensures post-init only marks scripts as executable and templates yield clean, deterministic pants.toml output.

**Error Handling:** Keep existing diagnostics. Executable bit changes will skip unreadable files. CI template change is pure content, no runtime behavior.

**Testing:** Update the non-Python init E2E test to assert Python backends and config files exist for TS/Rust/Go, and ensure no blank lines at top or inside backend lists. The pack smoke test already checks the Pants action string. Add/keep executable bit assertion on a BUILD file.
