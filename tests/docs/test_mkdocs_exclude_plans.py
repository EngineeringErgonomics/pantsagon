from pathlib import Path
import re


def _extract_exclude_docs_patterns(text: str) -> list[str]:
    lines = text.splitlines()
    patterns: list[str] = []
    in_block = False
    indent = None

    for line in lines:
        if not in_block:
            if re.match(r"^\s*exclude_docs:\s*$", line):
                in_block = True
                continue
            match = re.match(r"^\s*exclude_docs:\s*(.+)$", line)
            if match:
                value = match.group(1).strip().strip('"\'')
                if value in {"|", ">"}:
                    in_block = True
                    continue
                patterns.append(value)
                break
            continue

        if not line.strip():
            continue

        current_indent = len(line) - len(line.lstrip())
        if indent is None:
            indent = current_indent

        if current_indent < indent:
            break

        patterns.append(line.strip().lstrip("-").strip())

    return patterns


def test_mkdocs_excludes_plans_from_build() -> None:
    mkdocs_path = Path(__file__).resolve().parents[2] / "mkdocs.yml"
    text = mkdocs_path.read_text(encoding="utf-8")

    patterns = _extract_exclude_docs_patterns(text)
    assert patterns, "mkdocs.yml must define exclude_docs to keep plans out of build"
    assert any("plans/" in pattern for pattern in patterns), (
        "exclude_docs must include a plans/ pattern to keep plans out of build"
    )
