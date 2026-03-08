from __future__ import annotations

import runpy
from pathlib import Path


def test_main_entrypoint_supports_path_execution() -> None:
    project_root = Path(__file__).resolve().parents[1]
    entrypoint = project_root / "src" / "grip_py_demo" / "main.py"
    runpy.run_path(str(entrypoint), run_name="__grip_test__")
