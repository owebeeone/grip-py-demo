from __future__ import annotations

import time

from PySide6.QtWidgets import QApplication

from grip_py_demo.controller import RuntimeBridge
from grip_py_demo.demo_runtime import DemoRuntime


def test_runtime_bridge_emits_context_and_grip_key_for_changed_value() -> None:
    app = QApplication.instance() or QApplication([])

    runtime = DemoRuntime()
    bridge = RuntimeBridge(runtime)
    seen: list[tuple[str, str]] = []
    bridge.grip_changed.connect(lambda ctx_id, grip_key: seen.append((ctx_id, grip_key)))

    runtime.increment_count()
    deadline = time.time() + 1.0
    while time.time() < deadline and (runtime.main_context.id, runtime.grips.COUNT.key) not in seen:
        app.processEvents()
        time.sleep(0.01)

    assert (runtime.main_context.id, runtime.grips.COUNT.key) in seen
    assert (runtime.main_context.id, runtime.grips.CALC_DISPLAY.key) not in seen

    bridge.dispose()
