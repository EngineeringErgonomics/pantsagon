__dependents_rules__(
  ("*", {"tags": ["svc:pantsagon"]}, "!*"),
)

__dependencies_rules__(
  (
    "*",
    "//services/pantsagon/src/pantsagon/domain/**",
    "//shared/foundation/**",
    "!*",
  ),
)

python_sources(
  name="domain",
  tags=["svc:pantsagon", "layer:domain"],
  dependencies=["//shared/foundation:lib"],
)
