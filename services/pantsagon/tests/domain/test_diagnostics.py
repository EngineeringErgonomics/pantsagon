from pantsagon.domain.diagnostics import Diagnostic, Severity, FileLocation


def test_diagnostic_id_is_deterministic():
    d1 = Diagnostic(
        code="X",
        rule="r",
        severity=Severity.ERROR,
        message="m",
        location=FileLocation("a.txt", 1, 2),
    )
    d2 = Diagnostic(
        code="X",
        rule="r",
        severity=Severity.ERROR,
        message="m",
        location=FileLocation("a.txt", 1, 2),
    )
    assert d1.id == d2.id
