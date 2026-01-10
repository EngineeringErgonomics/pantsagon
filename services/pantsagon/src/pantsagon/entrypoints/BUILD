__dependents_rules__(
  ("*", "//services/pantsagon:cli", "!*"),
)

__dependencies_rules__(
  (
    "*",
    "//services/pantsagon/src/pantsagon/entrypoints/**",
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
  name="entrypoints",
  tags=["svc:pantsagon", "layer:entrypoints"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/adapters:adapters",
    "//services/pantsagon/src/pantsagon/application:application",
    "//services/pantsagon/src/pantsagon/ports:ports",
    "//services/pantsagon/src/pantsagon/domain:domain",
    "//shared/foundation:lib",
  ],
)
