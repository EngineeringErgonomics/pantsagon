from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import ast
import fnmatch
import os
import re
import tomllib
import yaml


@dataclass(frozen=True)
class LayerRule:
    name: str
    include: list[str]
    deny: list[str]


@dataclass(frozen=True)
class LanguageRule:
    name: str
    extensions: list[str]
    layers: list[LayerRule]


@dataclass(frozen=True)
class Config:
    languages: dict[str, LanguageRule]


def load_config(path: Path) -> Config:
    data = yaml.safe_load(path.read_text()) or {}
    languages: dict[str, LanguageRule] = {}
    raw_languages = data.get("languages") or {}
    if isinstance(raw_languages, dict):
        for lang_name, lang_rules in raw_languages.items():
            if not isinstance(lang_rules, dict):
                continue
            raw_exts = lang_rules.get("extensions") or []
            extensions = [str(ext) for ext in raw_exts if ext]
            layers: list[LayerRule] = []
            raw_layers = lang_rules.get("layers") or {}
            if isinstance(raw_layers, dict):
                for layer_name, rules in raw_layers.items():
                    if not isinstance(rules, dict):
                        continue
                    include = (
                        list(rules.get("include", []))
                        if isinstance(rules.get("include"), list)
                        else []
                    )
                    deny = (
                        list(rules.get("deny", []))
                        if isinstance(rules.get("deny"), list)
                        else []
                    )
                    layers.append(
                        LayerRule(name=str(layer_name), include=include, deny=deny)
                    )
            languages[str(lang_name)] = LanguageRule(
                name=str(lang_name), extensions=extensions, layers=layers
            )
    return Config(languages=languages)


def find_repo_root(start: Path | None = None) -> Path:
    buildroot = os.environ.get("PANTS_BUILDROOT")
    if buildroot:
        candidate = Path(buildroot)
        if (candidate / ".pantsagon.toml").exists():
            return candidate
    cwd = (start or Path.cwd()).resolve()
    for parent in (cwd, *cwd.parents):
        if (parent / ".pantsagon.toml").exists():
            return parent
    return cwd


def load_languages(lock_path: Path) -> list[str]:
    if not lock_path.exists():
        return ["python"]
    try:
        lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    except Exception:
        return ["python"]
    selection = lock.get("selection") if isinstance(lock.get("selection"), dict) else {}
    raw = selection.get("languages")
    if isinstance(raw, list) and raw:
        return [str(item) for item in raw]
    return ["python"]


def _matches_any(path: Path, patterns: list[str]) -> bool:
    rel = path.as_posix()
    return any(
        fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(rel, f"**/{pattern}")
        for pattern in patterns
    )


def _deny_hit(import_name: str, deny: list[str]) -> bool:
    for entry in deny:
        if import_name == entry:
            return True
        if import_name.startswith(entry + "."):
            return True
        if import_name.startswith(entry + "/"):
            return True
        if import_name.startswith(entry + "::"):
            return True
    return False


def _extract_imports_python(text: str) -> list[tuple[str, int]]:
    hits: list[tuple[str, int]] = []
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                hits.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module:
            hits.append((node.module, node.lineno))
    return hits


_TS_IMPORT_RE = re.compile(
    r'^\s*(?:import|export)\s+(?:.+\s+from\s+)?[\'"]([^\'"]+)[\'"]'
)
_TS_REQUIRE_RE = re.compile(r'require\(\s*[\'"]([^\'"]+)[\'"]\s*\)')


def _extract_imports_typescript(text: str) -> list[tuple[str, int]]:
    hits: list[tuple[str, int]] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        match = _TS_IMPORT_RE.search(line)
        if match:
            hits.append((match.group(1), idx))
        for req in _TS_REQUIRE_RE.findall(line):
            hits.append((req, idx))
    return hits


_RUST_USE_RE = re.compile(r"^\s*use\s+([A-Za-z0-9_:]+)")


def _extract_imports_rust(text: str) -> list[tuple[str, int]]:
    hits: list[tuple[str, int]] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        match = _RUST_USE_RE.search(line)
        if match:
            hits.append((match.group(1), idx))
    return hits


def _extract_imports_go(text: str) -> list[tuple[str, int]]:
    hits: list[tuple[str, int]] = []
    in_block = False
    for idx, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        if stripped.startswith("import ("):
            in_block = True
            continue
        if in_block:
            if stripped.startswith(")"):
                in_block = False
                continue
            match = re.search(r'"([^"]+)"', stripped)
            if match:
                hits.append((match.group(1), idx))
            continue
        match = re.match(r'^\s*import\s+(?:\w+\s+)?"([^"]+)"', line)
        if match:
            hits.append((match.group(1), idx))
    return hits


_IMPORT_EXTRACTORS = {
    "python": _extract_imports_python,
    "typescript": _extract_imports_typescript,
    "rust": _extract_imports_rust,
    "go": _extract_imports_go,
}


def _normalize_languages(languages: list[str] | None, config: Config) -> list[str]:
    if languages:
        return [lang for lang in languages if lang in config.languages]
    if "python" in config.languages:
        return ["python"]
    return list(config.languages.keys())


def scan_files(
    config: Config, files: list[Path], languages: list[str] | None = None
) -> list[str]:
    violations: list[str] = []
    active = _normalize_languages(languages, config)
    for lang in active:
        lang_rule = config.languages.get(lang)
        if lang_rule is None:
            continue
        extractor = _IMPORT_EXTRACTORS.get(lang)
        if extractor is None:
            continue
        extensions = set(lang_rule.extensions)
        for file in files:
            if file.suffix not in extensions:
                continue
            text = file.read_text()
            for layer in lang_rule.layers:
                if _matches_any(file, layer.include):
                    for name, lineno in extractor(text):
                        if _deny_hit(name, layer.deny):
                            violations.append(
                                f"{file}:{lineno} forbidden import '{name}' in layer {layer.name}"
                            )
    return violations


def scan_tree(
    config: Config, root: Path, languages: list[str] | None = None
) -> list[str]:
    files: list[Path] = [p for p in root.rglob("*") if p.is_file()]
    return scan_files(config, files, languages=languages)
