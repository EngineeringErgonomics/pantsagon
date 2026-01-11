__dependents_rules__(
    ("*", {"tags": ["svc:pantsagon"]}, "!*"),
)

__dependencies_rules__(
    (
        "*",
        "//services/pantsagon/src/pantsagon/domain/**",
        "//services/pantsagon/src/pantsagon:pkg",
        "//services/pantsagon/src/pantsagon/__init__.py",
        "//shared/foundation/src/**",
        "!*",
    ),
)

python_sources(
    name="domain",
    tags=["svc:pantsagon", "layer:domain"],
    dependencies=["//shared/foundation/src:lib"],
)
