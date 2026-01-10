from pathlib import Path
import importlib.util

import pytest

from pantsagon.adapters.renderer.copier_renderer import CopierRenderer
from pantsagon.domain.pack import PackRef
from pantsagon.ports.renderer import RenderRequest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("copier") is None,
    reason="copier not installed",
)


def test_copier_renders_template(tmp_path):
    pack = tmp_path / "pack"
    (pack / "templates").mkdir(parents=True)
    (pack / "pack.yaml").write_text("schema_version: 1\nid: x\nversion: 1.0.0\nvariables: [{name: name, type: string}]\n")
    (pack / "copier.yml").write_text("name: {type: str}\n_templates_suffix: '.jinja'\n_subdirectory: 'templates'\n")
    (pack / "templates" / "README.md.jinja").write_text("Hello {{ name }}")
    out = tmp_path / "out"
    out.mkdir()
    req = RenderRequest(pack=PackRef(id="x", version="1.0.0", source="local"), pack_path=pack, staging_dir=out, answers={"name": "World"}, allow_hooks=False)
    result = CopierRenderer().render(req)
    assert (out / "README.md").read_text() == "Hello World"
