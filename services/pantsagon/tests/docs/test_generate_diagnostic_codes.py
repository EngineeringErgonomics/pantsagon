import tempfile
import unittest
from pathlib import Path

import generate_diagnostic_codes


class GenerateDiagnosticCodesTest(unittest.TestCase):
    def test_generates_markdown_from_codes_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            src = (
                repo_root
                / "services"
                / "pantsagon"
                / "src"
                / "pantsagon"
                / "diagnostics"
            )
            src.mkdir(parents=True)
            (repo_root / "docs" / "reference").mkdir(parents=True)

            (src / "codes.yaml").write_text(
                """
version: 1
codes:
  - code: EXAMPLE_CODE
    severity: error
    rule: example.rule
    message: Example message
    hint: Example hint
""".lstrip(),
                encoding="utf-8",
            )

            generate_diagnostic_codes.generate(repo_root)

            out = (repo_root / "docs" / "reference" / "diagnostic-codes.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Generated file. Do not edit directly.", out)
            self.assertIn("EXAMPLE_CODE", out)


if __name__ == "__main__":
    unittest.main()
