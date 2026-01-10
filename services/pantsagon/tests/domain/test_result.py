from pantsagon.domain.result import Result
from pantsagon.domain.diagnostics import Diagnostic, Severity


def test_exit_code_precedence_exec_over_validation():
    r = Result(diagnostics=[
        Diagnostic(code="VAL", rule="r", severity=Severity.ERROR, message="v"),
        Diagnostic(code="EXEC", rule="r", severity=Severity.ERROR, message="e", is_execution=True),
    ])
    assert r.exit_code == 3
