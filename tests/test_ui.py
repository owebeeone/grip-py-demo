from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

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


def test_coin_tab_renders_coin_columns() -> None:
    app = QApplication.instance() or QApplication([])

    runtime = DemoRuntime()
    window = MainWindow(runtime)
    try:
        window.show()
        runtime.set_tab("coins")
        window.render()
        app.processEvents()

        labels = [label.text() for label in window.findChildren(QLabel)]
        assert "Market A" in labels
        assert "Market B" in labels
        assert any(text.startswith("Feed:") for text in labels)
        assert window.stack.currentWidget() is window.coins_page
    finally:
        window.close()
