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
        "//services/pantsagon/src/pantsagon:pkg",
        "//services/pantsagon/src/pantsagon/__init__.py",
        "//shared/foundation/src/**",
        "//shared/adapters/**",
        "//3rdparty/python/**",
        "!*",
    ),
)

python_sources(
    name="adapters",
    sources=["**/*.py"],
    tags=["svc:pantsagon", "layer:adapters"],
    dependencies=[
        "//services/pantsagon/src/pantsagon/application:application",
        "//services/pantsagon/src/pantsagon/ports:ports",
        "//services/pantsagon/src/pantsagon/domain:domain",
        "//shared/foundation/src:lib",
    ],
)
