__dependents_rules__ = [{"tags": ["svc:pantsagon"]}]

python_sources(
  name="application",
  tags=["svc:pantsagon", "layer:application"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/domain:domain",
    "//services/pantsagon/src/pantsagon/ports:ports",
    "//shared/foundation:lib",
  ],
  __dependencies_rules__=[
    {"path": "services/pantsagon/src/pantsagon/application/**"},
    {"path": "services/pantsagon/src/pantsagon/ports/**"},
    {"path": "services/pantsagon/src/pantsagon/domain/**"},
    {"path": "shared/foundation/src/**"},
  ],
)
