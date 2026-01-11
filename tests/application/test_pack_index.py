import json
from pathlib import Path

from pantsagon.application.pack_index import load_pack_index, resolve_pack_ids


def test_resolve_pack_ids_from_index(tmp_path):
    index_path = tmp_path / "_index.json"
    index_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "base_packs": ["pantsagon.core"],
                "languages": {"python": ["pantsagon.python"]},
                "features": {"openapi": ["pantsagon.openapi"], "docker": ["pantsagon.docker"]},
            }
        ),
        encoding="utf-8",
    )
    index = load_pack_index(index_path)
    result = resolve_pack_ids(index, languages=["python"], features=["openapi", "docker"])
    assert result.diagnostics == []
    assert result.value == [
        "pantsagon.core",
        "pantsagon.python",
        "pantsagon.openapi",
        "pantsagon.docker",
    ]


def test_resolve_pack_ids_unknown_language(tmp_path):
    index_path = tmp_path / "_index.json"
    index_path.write_text(
        json.dumps({"schema_version": 1, "base_packs": ["pantsagon.core"], "languages": {}, "features": {}}),
        encoding="utf-8",
    )
    index = load_pack_index(index_path)
    result = resolve_pack_ids(index, languages=["elixir"], features=[])
    assert any(d.code == "PACK_INDEX_UNKNOWN_LANGUAGE" for d in result.diagnostics)
