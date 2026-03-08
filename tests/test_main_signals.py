from __future__ import annotations

import signal

from PySide6.QtWidgets import QApplication

from grip_py_demo.demo_runtime import DemoRuntime
from grip_py_demo.main import install_signal_handlers
from grip_py_demo.ui import MainWindow


def test_install_signal_handlers_closes_window_and_quits(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    runtime = DemoRuntime()
    window = MainWindow(runtime)
    window.show()
    app.processEvents()

    registered: dict[int, object] = {}

    def fake_signal(sig_num: int, handler):
        registered[sig_num] = handler
        return handler

    monkeypatch.setattr(signal, "signal", fake_signal)

    def fake_single_shot(_delay_ms: int, callback) -> None:
        callback()

    monkeypatch.setattr("grip_py_demo.main.QTimer.singleShot", fake_single_shot)

    close_count = {"value": 0}
    quit_count = {"value": 0}

    original_close = window.close

    def wrapped_close() -> bool:
        close_count["value"] += 1
        return original_close()

    def wrapped_quit() -> None:
        quit_count["value"] += 1

    monkeypatch.setattr(window, "close", wrapped_close)
    monkeypatch.setattr(app, "quit", wrapped_quit)

    install_signal_handlers(app, window)

    assert signal.SIGINT in registered
    if hasattr(signal, "SIGTERM"):
        assert signal.SIGTERM in registered

    handler = registered[signal.SIGINT]
    handler(signal.SIGINT, None)
    handler(signal.SIGINT, None)
    app.processEvents()

    assert close_count["value"] == 1
    assert quit_count["value"] == 1
