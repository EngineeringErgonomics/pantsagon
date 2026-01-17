shell_sources()

resources(
    name="test_speed_guard_resources",
    sources=[
        "test_speed_guard_config.json",
        "test_speed_guards.sh",
    ],
)

files(
    name="config",
    sources=["test_speed_guard_config.json"],
)

shunit2_tests(
    name="tests",
    dependencies=[":config"],
)
