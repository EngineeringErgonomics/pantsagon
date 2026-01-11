# Dependabot Configuration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Dependabot configuration to update GitHub Actions and Python dependencies daily with sensible limits, labels, and grouping to reduce PR noise.

**Architecture:** Create a single `.github/dependabot.yml` (version 2) with one `github-actions` entry and three `pip` entries for `/`, `/3rdparty/python`, and `/docs`. Apply `open-pull-requests-limit`, `rebase-strategy: auto`, and labels per ecosystem, and define basic grouping for pip updates to keep PR volume manageable.

**Tech Stack:** GitHub Dependabot (config v2), YAML.

### Task 1: Add Dependabot configuration

**Files:**
- Create: `.github/dependabot.yml`

**Step 1: Write the failing test**

```bash
# Expect: exit status 1 because the file doesn't exist yet
set -e
if test -f .github/dependabot.yml; then
  echo "unexpected: dependabot.yml already exists"
  exit 1
fi
```

**Step 2: Run test to verify it fails**

Run: `test -f .github/dependabot.yml`
Expected: exit status 1

**Step 3: Write minimal implementation**

```yaml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "daily"
    open-pull-requests-limit: 5
    rebase-strategy: "auto"
    labels:
      - "dependencies"
      - "ci"

  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "daily"
    open-pull-requests-limit: 10
    rebase-strategy: "auto"
    labels:
      - "dependencies"
    groups:
      runtime:
        patterns:
          - "typer"
          - "rich"
          - "pyyaml"
          - "tomli-w"
          - "jsonschema"
          - "copier"
      dev-tooling:
        patterns:
          - "pytest*"

  - package-ecosystem: "pip"
    directory: "/3rdparty/python"
    schedule:
      interval: "daily"
    open-pull-requests-limit: 10
    rebase-strategy: "auto"
    labels:
      - "dependencies"
    groups:
      tooling:
        patterns:
          - "*"

  - package-ecosystem: "pip"
    directory: "/docs"
    schedule:
      interval: "daily"
    open-pull-requests-limit: 10
    rebase-strategy: "auto"
    labels:
      - "dependencies"
      - "docs"
    groups:
      docs:
        patterns:
          - "*"
```

**Step 4: Run test to verify it passes**

Run: `test -f .github/dependabot.yml`
Expected: exit status 0

**Step 5: Commit**

```bash
git add .github/dependabot.yml
git commit -m "chore: add dependabot config"
```
