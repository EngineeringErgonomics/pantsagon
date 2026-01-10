__dependents_rules__ = [{"type": "*"}]

python_sources(
  name="lib",
  tags=["shared:foundation"],
  __dependencies_rules__=[
    {"path": "shared/foundation/src/**"},
  ],
)

python_tests(
  name="tests",
  dependencies=[":lib"],
)
