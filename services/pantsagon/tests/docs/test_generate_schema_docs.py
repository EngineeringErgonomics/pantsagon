import json
import tempfile
import unittest
from pathlib import Path

import generate_schema_docs


class GenerateSchemaDocsTest(unittest.TestCase):
    def test_generates_markdown_from_schemas(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            schemas_dir = repo_root / "schemas"
            pack_schema_dir = repo_root / "shared" / "contracts" / "schemas"
            schemas_dir.mkdir(parents=True)
            pack_schema_dir.mkdir(parents=True)
            (repo_root / "docs" / "reference").mkdir(parents=True)

            def write_schema(path: Path, title: str) -> None:
                path.write_text(
                    json.dumps(
                        {
                            "$schema": "https://json-schema.org/draft/2020-12/schema",
                            "$id": f"https://example.test/{path.name}",
                            "title": title,
                            "description": f"{title} description",
                            "type": "object",
                            "properties": {"alpha": {"type": "string"}},
                            "required": ["alpha"],
                        }
                    ),
                    encoding="utf-8",
                )

            write_schema(pack_schema_dir / "pack.schema.v1.json", "Pack Schema")
            write_schema(schemas_dir / "repo-lock.schema.v1.json", "Repo Lock Schema")
            write_schema(schemas_dir / "result.schema.v1.json", "Result Schema")

            generate_schema_docs.generate(repo_root)

            out = (repo_root / "docs" / "reference" / "pack.schema.v1.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Generated file. Do not edit directly.", out)
            self.assertIn("# Pack Schema", out)
            self.assertIn("alpha", out)


if __name__ == "__main__":
    unittest.main()
