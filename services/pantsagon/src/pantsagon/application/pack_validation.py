from pathlib import Path

from pantsagon.domain.json_types import JsonDict
from pantsagon.domain.result import Result
from pantsagon.ports.policy_engine import PolicyEnginePort


def validate_pack(pack_path: Path, engine: PolicyEnginePort) -> Result[JsonDict]:
    return engine.validate_pack(pack_path)
