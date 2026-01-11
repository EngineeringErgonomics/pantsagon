from pantsagon.adapters.errors import RendererExecutionError


def test_adapter_error_has_message_and_details():
    err = RendererExecutionError("boom", details={"x": 1})
    assert "boom" in str(err)
    assert err.details["x"] == 1
