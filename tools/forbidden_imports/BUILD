python_sources(name="lib", sources=["src/**/*.py"])

resources(
  name="config",
  sources=["forbidden_imports.yaml"],
)

python_tests(
  name="tests",
  sources=["tests/**/*.py"],
  dependencies=[":lib", ":config"],
)
