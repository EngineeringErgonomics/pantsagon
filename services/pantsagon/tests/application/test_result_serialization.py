from pantsagon.domain.diagnostics import Diagnostic, Severity, FileLocation
from pantsagon.domain.result import Result
from pantsagon.application.result_serialization import serialize_result


def test_result_serializes_with_schema_version():
    result = Result(
        diagnostics=[
            Diagnostic(
                code="X",
                rule="r",
                severity=Severity.ERROR,
                message="m",
                location=FileLocation("x.py", 1, 2),
            )
        ]
    )
    data = serialize_result(result, command="init", args=["."])
    assert data["result_schema_version"] == 1
    assert data["exit_code"] == result.exit_code
    assert data["diagnostics"][0]["location"]["path"] == "x.py"
