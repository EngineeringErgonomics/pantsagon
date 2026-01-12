# CodeQL Setup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add CodeQL code scanning for GitHub.com with language auto-detection, explicit mapping, fallback behavior, and a configurable query + path filter setup.

**Architecture:** Add a CodeQL workflow with a language-detection job and a matrix analysis job, plus a shared CodeQL config file to control query suites and ignored paths. Use autobuild by default with a documented manual-build fallback.

**Tech Stack:** GitHub Actions, github/codeql-action, actions/github-script, YAML.

### Task 1: Add CodeQL config file

**Files:**
- Create: `.github/codeql/codeql-config.yml`

**Step 1: Write the config file**

```yaml
name: "CodeQL config"

queries:
  - uses: security-extended
  - uses: security-and-quality

paths-ignore:
  - .pants.d
  - dist
  - site
  - .venv
  - "**/__pycache__"
  - node_modules
  # Keep 3rdparty/ included unless we confirm it contains only dependencies.
```

### Task 2: Add CodeQL workflow with language detection + matrix

**Files:**
- Create: `.github/workflows/codeql.yml`

**Step 1: Write the workflow**

```yaml
name: CodeQL

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]
  schedule:
    - cron: "0 3 * * 1"
  workflow_dispatch: {}

jobs:
  detect-languages:
    name: Detect languages
    runs-on: ubuntu-latest
    permissions:
      contents: read
    outputs:
      languages: ${{ steps.detect.outputs.languages }}
    steps:
      - name: Map Linguist to CodeQL languages
        id: detect
        uses: actions/github-script@v7
        with:
          script: |
            const linguistToCodeQL = {
              "C": "cpp",
              "C++": "cpp",
              "Objective-C": "cpp",
              "Objective-C++": "cpp",
              "C#": "csharp",
              "Go": "go",
              "Java": "java-kotlin",
              "Kotlin": "java-kotlin",
              "JavaScript": "javascript-typescript",
              "TypeScript": "javascript-typescript",
              "Python": "python",
              "Ruby": "ruby",
              "Swift": "swift",
            };

            const { owner, repo } = context.repo;
            const { data } = await github.rest.repos.listLanguages({ owner, repo });
            const detected = Object.keys(data)
              .map((name) => linguistToCodeQL[name])
              .filter((lang) => !!lang);

            const unique = Array.from(new Set(detected));
            if (unique.length === 0) {
              core.warning('No supported languages detected; falling back to ["python"].');
              unique.push('python');
            }

            core.info(`CodeQL languages: ${unique.join(', ')}`);
            core.setOutput('languages', JSON.stringify(unique));

  analyze:
    name: Analyze (${{ matrix.language }})
    needs: detect-languages
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      actions: read
      contents: read
    strategy:
      fail-fast: false
      matrix:
        language: ${{ fromJson(needs.detect-languages.outputs.languages) }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}
          config-file: ./.github/codeql/codeql-config.yml

      - name: Autobuild
        uses: github/codeql-action/autobuild@v3
        # If autobuild fails for a language, replace with manual build steps:
        # run: |
        #   <your build commands>

      - name: Analyze
        uses: github/codeql-action/analyze@v3
```

**Step 2: Quick syntax sanity check**

Run: `git diff --check`
Expected: no output

### Task 3: Verify baseline tests and commit

**Files:**
- Modify: `.github/codeql/codeql-config.yml`
- Modify: `.github/workflows/codeql.yml`

**Step 1: Run the test suite (baseline check)**

Run: `pants test ::`
Expected: all tests pass

**Step 2: Commit changes**

Run:

```bash
git add .github/codeql/codeql-config.yml .github/workflows/codeql.yml
git commit -m "ci: add CodeQL code scanning"
```
Expected: commit created
