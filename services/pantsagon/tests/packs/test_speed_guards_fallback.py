from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess


def test_guard_config_fallback_resolves_root_relative(tmp_path: Path) -> None:
    script_path = Path(
        "packs/core/templates/tools/guards/test_speed_enforce/test_speed_guards.sh"
    )
    assert script_path.exists()

    root = tmp_path / "root"
    guard_dir = root / "tools" / "guards" / "test_speed_enforce"
    guard_dir.mkdir(parents=True)
    shutil.copy(script_path, guard_dir / "test_speed_guards.sh")

    config_dir = root / "configs"
    config_dir.mkdir()
    (config_dir / "test_speed_guard_config.json").write_text('{"source_root":"src"}')

    workdir = root / "subdir"
    workdir.mkdir()
    result = subprocess.run(
        ["bash", str(guard_dir / "test_speed_guards.sh")],
        cwd=workdir,
        env={
            **os.environ,
            "TEST_SPEED_GUARD_CONFIG": "configs/test_speed_guard_config.json",
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_guard_config_fallback_handles_missing_config(tmp_path: Path) -> None:
    script_path = Path(
        "packs/core/templates/tools/guards/test_speed_enforce/test_speed_guards.sh"
    )
    assert script_path.exists()

    root = tmp_path / "root"
    guard_dir = root / "tools" / "guards" / "test_speed_enforce"
    guard_dir.mkdir(parents=True)
    shutil.copy(script_path, guard_dir / "test_speed_guards.sh")

    workdir = root / "subdir"
    workdir.mkdir()

    result = subprocess.run(
        ["bash", str(guard_dir / "test_speed_guards.sh")],
        cwd=workdir,
        env={
            **os.environ,
            "TEST_SPEED_GUARD_CONFIG": "configs/missing.json",
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.returncode == 0, result.stderr
