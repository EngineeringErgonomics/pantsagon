from pantsagon.domain.naming import (
    BUILTIN_RESERVED_SERVICES,
    validate_feature_name,
    validate_pack_id,
    validate_service_name,
)


def test_service_name_rules():
    assert validate_service_name("my-service", BUILTIN_RESERVED_SERVICES, set()) == []
    assert validate_service_name("MyService", BUILTIN_RESERVED_SERVICES, set())
    assert validate_service_name("bad--name", BUILTIN_RESERVED_SERVICES, set())
    assert validate_service_name("trailing-", BUILTIN_RESERVED_SERVICES, set())
    assert validate_service_name("services", BUILTIN_RESERVED_SERVICES, set())


def test_pack_id_rules():
    assert validate_pack_id("pantsagon.core") == []
    assert validate_pack_id("Pantsagon.Core")
    assert validate_pack_id("nope")


def test_feature_name_rules():
    assert validate_feature_name("openapi") == []
    assert validate_feature_name("snake_case") == []
    assert validate_feature_name("bad.name")
