__dependents_rules__(
  ("*", {"tags": ["svc:pantsagon"]}, "!*"),
)

__dependencies_rules__(
  (
    "*",
    "//services/pantsagon/src/pantsagon/application/**",
    "//services/pantsagon/src/pantsagon/ports/**",
    "//services/pantsagon/src/pantsagon/domain/**",
    "//shared/foundation/**",
    "!*",
  ),
)

python_sources(
  name="application",
  tags=["svc:pantsagon", "layer:application"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/domain:domain",
    "//services/pantsagon/src/pantsagon/ports:ports",
    "//shared/foundation:lib",
  ],
)
