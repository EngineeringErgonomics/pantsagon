from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from pantsagon.domain.diagnostics import Diagnostic, Severity
from pantsagon.domain.result import Result


@dataclass(frozen=True)
class PackIndex:
    base_packs: list[str]
    languages: dict[str, list[str]]
    features: dict[str, list[str]]


def _as_list_map(raw: Any) -> dict[str, list[str]]:
    if not isinstance(raw, dict):
        return {}
    mapped: dict[str, list[str]] = {}
    for key, value in raw.items():
        if isinstance(value, list):
            mapped[str(key)] = [str(item) for item in value]
    return mapped


def load_pack_index(path: Path) -> PackIndex:
    raw = json.loads(path.read_text(encoding="utf-8"))
    base = raw.get("base_packs")
    base_packs = [str(item) for item in base] if isinstance(base, list) else []
    languages = _as_list_map(raw.get("languages"))
    features = _as_list_map(raw.get("features"))
    return PackIndex(base_packs=base_packs, languages=languages, features=features)


def resolve_pack_ids(
    index: PackIndex, languages: list[str], features: list[str]
) -> Result[list[str]]:
    diagnostics: list[Diagnostic] = []
    packs: list[str] = []
    packs.extend(index.base_packs)

    for lang in languages:
        if lang not in index.languages:
            diagnostics.append(
                Diagnostic(
                    code="PACK_INDEX_UNKNOWN_LANGUAGE",
                    rule="pack.index.language",
                    severity=Severity.ERROR,
                    message=f"Unknown language in pack index: {lang}",
                )
            )
            continue
        packs.extend(index.languages[lang])

    for feature in features:
        if feature not in index.features:
            diagnostics.append(
                Diagnostic(
                    code="PACK_INDEX_UNKNOWN_FEATURE",
                    rule="pack.index.feature",
                    severity=Severity.ERROR,
                    message=f"Unknown feature in pack index: {feature}",
                )
            )
            continue
        packs.extend(index.features[feature])

    seen: set[str] = set()
    ordered: list[str] = []
    for pack_id in packs:
        if pack_id not in seen:
            seen.add(pack_id)
            ordered.append(pack_id)

    return Result(value=ordered, diagnostics=diagnostics)
