from pantsagon.domain.pack import PackRef


def test_packref_supports_future_fields():
    ref = PackRef(id="pantsagon.core", version="1.0.0", source="bundled", location=None, git_ref=None, commit=None, digest=None, subdir=None)
    assert ref.source == "bundled"
