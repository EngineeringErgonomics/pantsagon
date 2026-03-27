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
    (pack / "pack.yaml").write_text(
        "schema_version: 1\nid: x\nversion: 1.0.0\nvariables: [{name: name, type: string}]\n"
    )
    (pack / "copier.yml").write_text(
        "name: {type: str}\n_templates_suffix: '.jinja'\n_subdirectory: 'templates'\n"
    )
    (pack / "templates" / "README.md.jinja").write_text("Hello {{ name }}")
    out = tmp_path / "out"
    out.mkdir()
    req = RenderRequest(
        pack=PackRef(id="x", version="1.0.0", source="local"),
        pack_path=pack,
        staging_dir=out,
        answers={"name": "World"},
        allow_hooks=False,
    )
    CopierRenderer().render(req)
    assert (out / "README.md").read_text() == "Hello World"


def test_copier_creates_githooks_when_guards_absent(tmp_path):
    pack = tmp_path / "pack"
    (pack / "templates").mkdir(parents=True)
    (pack / "pack.yaml").write_text(
        "schema_version: 1\nid: x\nversion: 1.0.0\nvariables: [{name: name, type: string}]\n"
    )
    (pack / "copier.yml").write_text(
        "name: {type: str}\n_templates_suffix: '.jinja'\n_subdirectory: 'templates'\n"
    )
    (pack / "templates" / "README.md.jinja").write_text("Hello {{ name }}")
    out = tmp_path / "out"
    out.mkdir()
    req = RenderRequest(
        pack=PackRef(id="x", version="1.0.0", source="local"),
        pack_path=pack,
        staging_dir=out,
        answers={"name": "World"},
        allow_hooks=False,
    )
    CopierRenderer().render(req)
    assert (out / ".githooks").is_dir()


def test_copier_refreshes_githooks_when_existing(tmp_path):
    pack = tmp_path / "pack"
    (pack / "templates" / "tools" / "guards").mkdir(parents=True)
    (pack / "pack.yaml").write_text(
        "schema_version: 1\nid: x\nversion: 1.0.0\nvariables: [{name: name, type: string}]\n"
    )
    (pack / "copier.yml").write_text(
        "name: {type: str}\n_templates_suffix: '.jinja'\n_subdirectory: 'templates'\n"
    )
    (pack / "templates" / "README.md.jinja").write_text("Hello {{ name }}")
    (pack / "templates" / "tools" / "guards" / "pre-commit.sh").write_text(
        "#!/usr/bin/env bash\necho pre-commit\n"
    )
    (pack / "templates" / "tools" / "guards" / "pre-push.sh").write_text(
        "#!/usr/bin/env bash\necho pre-push\n"
    )
    out = tmp_path / "out"
    out.mkdir()
    (out / ".githooks").mkdir()
    (out / ".githooks" / "pre-commit").write_text("stale")
    req = RenderRequest(
        pack=PackRef(id="x", version="1.0.0", source="local"),
        pack_path=pack,
        staging_dir=out,
        answers={"name": "World"},
        allow_hooks=False,
    )
    CopierRenderer().render(req)
    expected = "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "",
            'ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"',
            'exec "$ROOT_DIR/tools/guards/pre-commit.sh"',
            "",
        ]
    )
    assert (out / ".githooks" / "pre-commit").read_text() == expected
