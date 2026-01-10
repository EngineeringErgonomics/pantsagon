__dependents_rules__(
  ("*", "*"),
)

__dependencies_rules__(
  ("*", "//shared/foundation/**", "!*"),
)

python_sources(
  name="lib",
  sources=["src/**/*.py"],
  tags=["shared:foundation"],
)

python_tests(
  name="tests",
  sources=["tests/**/*.py"],
  dependencies=[":lib"],
)
