from pathlib import Path

from pantsagon.adapters.policy.pack_validator import (
    crosscheck_variables,
    load_copier_vars,
    load_manifest,
    validate_manifest_schema,
    validate_feature_names,
    validate_pack_id,
    validate_variable_names,
)
from pantsagon.domain.result import Result


def validate_pack(pack_path: Path) -> Result[dict]:
    manifest = load_manifest(pack_path)
    copier_vars = load_copier_vars(pack_path)
    diagnostics = []
    diagnostics.extend(validate_manifest_schema(manifest))
    diagnostics.extend(validate_pack_id(manifest))
    diagnostics.extend(validate_feature_names(manifest))
    diagnostics.extend(validate_variable_names(manifest))
    diagnostics.extend(crosscheck_variables(manifest, copier_vars))
    return Result(value=manifest, diagnostics=diagnostics)
