__dependents_rules__(
    ("*", {"tags": ["svc:pantsagon"]}, "!*"),
)

__dependencies_rules__(
    (
        "*",
        "//services/pantsagon/src/pantsagon/ports/**",
        "//services/pantsagon/src/pantsagon/domain/**",
        "//services/pantsagon/src/pantsagon:pkg",
        "//services/pantsagon/src/pantsagon/__init__.py",
        "//shared/foundation/src/**",
        "!*",
    ),
)

python_sources(
    name="ports",
    tags=["svc:pantsagon", "layer:ports"],
    dependencies=[
        "//services/pantsagon/src/pantsagon/domain:domain",
        "//shared/foundation/src:lib",
    ],
)
