__dependents_rules__ = [{"tags": ["svc:pantsagon"]}]

python_sources(
  name="ports",
  tags=["svc:pantsagon", "layer:ports"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/domain:domain",
    "//shared/foundation:lib",
  ],
  __dependencies_rules__=[
    {"path": "services/pantsagon/src/pantsagon/ports/**"},
    {"path": "services/pantsagon/src/pantsagon/domain/**"},
    {"path": "shared/foundation/src/**"},
  ],
)
