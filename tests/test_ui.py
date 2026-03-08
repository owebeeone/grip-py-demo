from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from grip_py_demo.demo_runtime import DemoRuntime
from grip_py_demo.ui import MainWindow


def test_exit_button_closes_window_and_disposes_bridge(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])

    runtime = DemoRuntime()
    window = MainWindow(runtime)

    dispose_count = {"value": 0}
    original_dispose = window._bridge.dispose

    def wrapped_dispose() -> None:
        dispose_count["value"] += 1
        original_dispose()

    monkeypatch.setattr(window._bridge, "dispose", wrapped_dispose)

    window.show()
    app.processEvents()
    assert window.isVisible()

    window.exit_button.click()
    app.processEvents()

    assert dispose_count["value"] == 1
    assert not window.isVisible()
