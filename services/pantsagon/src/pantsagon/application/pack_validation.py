from pathlib import Path
from typing import Any

from pantsagon.domain.result import Result
from pantsagon.ports.policy_engine import PolicyEnginePort


def validate_pack(pack_path: Path, engine: PolicyEnginePort) -> Result[dict[str, Any]]:
    return engine.validate_pack(pack_path)
