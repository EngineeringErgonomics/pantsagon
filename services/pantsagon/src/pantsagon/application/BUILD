__dependents_rules__(
    ("*", {"tags": ["svc:pantsagon"]}, "!*"),
)

__dependencies_rules__(
    (
        "*",
        "//services/pantsagon/src/pantsagon/application/**",
        "//services/pantsagon/src/pantsagon/ports/**",
        "//services/pantsagon/src/pantsagon/domain/**",
        "//services/pantsagon/src/pantsagon:pkg",
        "//services/pantsagon/src/pantsagon/__init__.py",
        "//shared/foundation/src/**",
        "!*",
    ),
)

python_sources(
    name="application",
    tags=["svc:pantsagon", "layer:application"],
    dependencies=[
        "//services/pantsagon/src/pantsagon/domain:domain",
        "//services/pantsagon/src/pantsagon/ports:ports",
        "//shared/foundation/src:lib",
    ],
)
