python_tests(
  name="domain",
  sources=["domain/**/*.py"],
  dependencies=["//services/pantsagon/src/pantsagon/domain:domain"],
)

python_tests(
  name="application",
  sources=["application/**/*.py"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/application:application",
    "//services/pantsagon/src/pantsagon/ports:ports",
    "//services/pantsagon/src/pantsagon/domain:domain",
  ],
)

python_tests(
  name="adapters",
  sources=["adapters/**/*.py"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/adapters:adapters",
    "//services/pantsagon/src/pantsagon/application:application",
    "//services/pantsagon/src/pantsagon/ports:ports",
    "//services/pantsagon/src/pantsagon/domain:domain",
  ],
)

python_tests(
  name="entrypoints",
  sources=["entrypoints/**/*.py"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/entrypoints:entrypoints",
    "//services/pantsagon/src/pantsagon/adapters:adapters",
    "//services/pantsagon/src/pantsagon/application:application",
    "//services/pantsagon/src/pantsagon/ports:ports",
    "//services/pantsagon/src/pantsagon/domain:domain",
  ],
)

python_tests(
  name="packs",
  sources=["packs/**/*.py"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/application:application",
    "//services/pantsagon/src/pantsagon/domain:domain",
    "//shared/contracts:schemas",
    "//packs:bundled",
  ],
)

python_tests(
  name="e2e",
  sources=["e2e/**/*.py"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/entrypoints:entrypoints",
  ],
)

python_tests(
  name="misc",
  sources=["test_imports.py"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/application:application",
    "//services/pantsagon/src/pantsagon/domain:domain",
  ],
)
