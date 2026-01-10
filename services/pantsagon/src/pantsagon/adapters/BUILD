__dependents_rules__(
  ("*", {"tags": ["svc:pantsagon"]}, "!*"),
)

__dependencies_rules__(
  (
    "*",
    "//services/pantsagon/src/pantsagon/adapters/**",
    "//services/pantsagon/src/pantsagon/application/**",
    "//services/pantsagon/src/pantsagon/ports/**",
    "//services/pantsagon/src/pantsagon/domain/**",
    "//shared/foundation/**",
    "//shared/adapters/**",
    "//3rdparty/python/**",
    "!*",
  ),
)

python_sources(
  name="adapters",
  tags=["svc:pantsagon", "layer:adapters"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/application:application",
    "//services/pantsagon/src/pantsagon/ports:ports",
    "//services/pantsagon/src/pantsagon/domain:domain",
    "//shared/foundation:lib",
  ],
)
