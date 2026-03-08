"""Application entry point."""

from __future__ import annotations

import signal
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

if __package__ in {None, ""}:
    # Support direct path execution: `python src/grip_py_demo/main.py`
    src_root = Path(__file__).resolve().parents[1]
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))
    from grip_py_demo.demo_runtime import DemoRuntime
    from grip_py_demo.ui import MainWindow
else:
    from .demo_runtime import DemoRuntime
    from .ui import MainWindow


def install_signal_handlers(app: QApplication, window: MainWindow) -> None:
    """Install POSIX signal handlers for clean Ctrl-C termination."""

    shutting_down = False

    def request_shutdown() -> None:
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        window.close()
        app.quit()

    def on_signal(_sig_num: int, _frame) -> None:
        QTimer.singleShot(0, request_shutdown)

    signal.signal(signal.SIGINT, on_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, on_signal)

    # Keep Python executing periodically so signal handlers run while Qt event
    # loop is otherwise idle.
    heartbeat = QTimer(app)
    heartbeat.setInterval(200)
    heartbeat.timeout.connect(lambda: None)
    heartbeat.start()
    setattr(app, "_signal_heartbeat", heartbeat)


def main() -> int:
    app = QApplication(sys.argv)
    runtime = DemoRuntime()
    window = MainWindow(runtime)
    install_signal_handlers(app, window)
    window.resize(980, 680)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
