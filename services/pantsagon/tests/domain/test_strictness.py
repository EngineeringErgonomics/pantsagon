from pantsagon.domain.diagnostics import Diagnostic, Severity
from pantsagon.domain.strictness import apply_strictness


def test_strictness_only_upgrades_upgradeable_warnings():
    diags = [
        Diagnostic(
            code="W_UP",
            rule="r",
            severity=Severity.WARN,
            message="warn",
            upgradeable=True,
        ),
        Diagnostic(
            code="W_NO",
            rule="r",
            severity=Severity.WARN,
            message="warn",
            upgradeable=False,
        ),
        Diagnostic(code="E", rule="r", severity=Severity.ERROR, message="err"),
    ]
    strict = apply_strictness(diags, strict=True)
    assert [d.severity.value for d in strict] == ["error", "warn", "error"]

    non_strict = apply_strictness(diags, strict=False)
    assert [d.severity.value for d in non_strict] == ["warn", "warn", "error"]
