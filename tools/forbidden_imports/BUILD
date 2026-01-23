python_sources(name="lib", sources=["src/**/*.py"])

resources(
    name="config",
    sources=["forbidden_imports.yaml"],
)

pex_binary(
    name="check",
    entry_point="forbidden_imports.cli:main",
    dependencies=[":lib", ":config"],
)

python_tests(
    name="tests",
    sources=["tests/**/*.py"],
    dependencies=[":lib", ":config"],
)
