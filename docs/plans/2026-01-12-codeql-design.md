# CodeQL Setup Design

## Goal
Enable CodeQL code scanning on GitHub.com with language auto-detection, explicit mapping to CodeQL-supported languages, robust fallback behavior, and a configurable query + path filter setup.

## Architecture
- Add a new workflow at `.github/workflows/codeql.yml` with two jobs: `detect-languages` and `codeql`.
- `detect-languages` calls the GitHub Languages API, maps Linguist names to CodeQL language keys, deduplicates, and falls back to `["python"]` when no supported languages are detected.
- `codeql` runs a matrix over the detected languages and executes CodeQL init, autobuild, and analyze steps with a shared config file.

## Language Detection & Mapping
- Explicitly map Linguist names to CodeQL language keys (e.g., TypeScript -> javascript-typescript, Java/Kotlin -> java-kotlin).
- Ignore any languages not supported by CodeQL.
- Warn and fall back to a safe default if the mapping result is empty to avoid a no-op workflow.

## Query Configuration & Path Filters
- Add `.github/codeql/codeql-config.yml` to customize query suites and ignore known generated/output paths.
- Use `security-extended` and `security-and-quality` suites to increase coverage over defaults.
- Ignore common build/output paths: `.pants.d/`, `dist/`, `site/`, `.venv/`, `**/__pycache__/`, `node_modules/`.
- Leave `3rdparty/` unignored unless we confirm it contains only dependencies.

## Build Strategy
- Use `autobuild` by default for maximum compatibility.
- Add a commented placeholder in the workflow documenting how to switch to manual build steps if a language needs it later.

## Triggers & Permissions
- Triggers: `push` and `pull_request` to `main`, plus a weekly schedule.
- Permissions: `security-events: write`, `actions: read`, `contents: read`.
