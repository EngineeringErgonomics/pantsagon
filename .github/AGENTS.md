# AGENTS

## Docs publishing

- Docs are deployed via GitHub Pages (GitHub Actions) in `.github/workflows/docs.yml`.
- `mike` manages versioned docs in the `gh-pages` branch; that branch is used as the Pages artifact source.
- `main` publishes `dev` and sets it as default; tags publish `vX.Y.Z`, update `latest`, and set default to `latest`.
- PRs run docs validation only (no published preview).
- Generated docs in `docs/reference/` must be regenerated, not edited by hand.

## Testing

- Run tests with `pants test ::`.
- Do not use `pytest` directly.
- Never run `./pants test` (use `pants test`).
