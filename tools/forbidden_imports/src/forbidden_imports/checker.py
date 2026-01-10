from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import ast
import fnmatch
import yaml


@dataclass(frozen=True)
class LayerRule:
    name: str
    include: list[str]
    deny: list[str]


@dataclass(frozen=True)
class Config:
    layers: list[LayerRule]


def load_config(path: Path) -> Config:
    data = yaml.safe_load(path.read_text()) or {}
    layers = []
    for name, rules in (data.get("layers") or {}).items():
        layers.append(LayerRule(name=name, include=rules.get("include", []), deny=rules.get("deny", [])))
    return Config(layers=layers)


def _matches_any(path: Path, patterns: list[str]) -> bool:
    rel = path.as_posix()
    return any(
        fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(rel, f"**/{pattern}")
        for pattern in patterns
    )


def _deny_hit(import_name: str, deny: list[str]) -> bool:
    return any(import_name == d or import_name.startswith(d + ".") for d in deny)


def scan_files(config: Config, files: list[Path]) -> list[str]:
    violations: list[str] = []
    for file in files:
        for layer in config.layers:
            if _matches_any(file, layer.include):
                tree = ast.parse(file.read_text(), filename=str(file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if _deny_hit(alias.name, layer.deny):
                                violations.append(
                                    f"{file}:{node.lineno} forbidden import '{alias.name}' in layer {layer.name}"
                                )
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        if _deny_hit(node.module, layer.deny):
                            violations.append(
                                f"{file}:{node.lineno} forbidden import '{node.module}' in layer {layer.name}"
                            )
    return violations


def scan_tree(config: Config, root: Path) -> list[str]:
    files: list[Path] = [p for p in root.rglob("*.py") if p.is_file()]
    return scan_files(config, files)
