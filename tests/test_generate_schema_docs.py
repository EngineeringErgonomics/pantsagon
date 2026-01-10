import json
import tempfile
import unittest
from pathlib import Path

from scripts import generate_schema_docs


class GenerateSchemaDocsTest(unittest.TestCase):
    def test_generates_markdown_from_schemas(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            schemas_dir = repo_root / "schemas"
            schemas_dir.mkdir(parents=True)
            (repo_root / "docs" / "reference").mkdir(parents=True)

            def write_schema(name: str, title: str) -> None:
                (schemas_dir / name).write_text(
                    json.dumps(
                        {
                            "$schema": "https://json-schema.org/draft/2020-12/schema",
                            "$id": f"https://example.test/{name}",
                            "title": title,
                            "description": f"{title} description",
                            "type": "object",
                            "properties": {"alpha": {"type": "string"}},
                            "required": ["alpha"],
                        }
                    ),
                    encoding="utf-8",
                )

            write_schema("pack.schema.v1.json", "Pack Schema")
            write_schema("repo-lock.schema.v1.json", "Repo Lock Schema")
            write_schema("result.schema.v1.json", "Result Schema")

            generate_schema_docs.generate(repo_root)

            out = (repo_root / "docs" / "reference" / "pack.schema.v1.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Generated file. Do not edit directly.", out)
            self.assertIn("# Pack Schema", out)
            self.assertIn("alpha", out)


if __name__ == "__main__":
    unittest.main()
