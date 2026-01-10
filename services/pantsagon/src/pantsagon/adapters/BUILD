__dependents_rules__ = [{"tags": ["svc:pantsagon"]}]

python_sources(
  name="adapters",
  tags=["svc:pantsagon", "layer:adapters"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/application:application",
    "//services/pantsagon/src/pantsagon/ports:ports",
    "//services/pantsagon/src/pantsagon/domain:domain",
    "//shared/foundation:lib",
  ],
  __dependencies_rules__=[
    {"path": "services/pantsagon/src/pantsagon/adapters/**"},
    {"path": "services/pantsagon/src/pantsagon/application/**"},
    {"path": "services/pantsagon/src/pantsagon/ports/**"},
    {"path": "services/pantsagon/src/pantsagon/domain/**"},
    {"path": "shared/foundation/src/**"},
    {"path": "shared/adapters/**"},
    {"path": "3rdparty/python/**"},
  ],
)
