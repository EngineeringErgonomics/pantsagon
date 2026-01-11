from pantsagon.adapters.pack_catalog.local import LocalPackCatalog


def test_local_pack_catalog_loads_manifest(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "pack.yaml").write_text("id: x\nversion: 1.0.0\n")
    (pack / "copier.yml").write_text("_min_copier_version: '9.0'\n")
    catalog = LocalPackCatalog()
    manifest = catalog.load_manifest(pack)
    assert manifest["id"] == "x"
