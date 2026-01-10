__dependents_rules__(
  ("*", {"tags": ["svc:pantsagon"]}, "!*"),
)

__dependencies_rules__(
  (
    "*",
    "//services/pantsagon/src/pantsagon/ports/**",
    "//services/pantsagon/src/pantsagon/domain/**",
    "//shared/foundation/**",
    "!*",
  ),
)

python_sources(
  name="ports",
  tags=["svc:pantsagon", "layer:ports"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/domain:domain",
    "//shared/foundation:lib",
  ],
)
