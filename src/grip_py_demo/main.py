"""Application entry point."""

from __future__ import annotations

import logging
import signal
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

if __package__ in {None, ""}:
    # Support direct path execution: `python src/grip_py_demo/main.py`
    src_root = Path(__file__).resolve().parents[1]
    workspace_root = Path(__file__).resolve().parents[3]
    for candidate in (
        src_root,
        workspace_root / "grip-py" / "src",
        workspace_root / "glial-local-py" / "src",
        workspace_root / "glial-net-py" / "src",
    ):
        if candidate.exists() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
    from grip_py_demo.demo_runtime import DemoRuntime
    from grip_py_demo.demo_session import DemoSessionManager
    from grip_py_demo.ui import MainWindow
else:
    from .demo_runtime import DemoRuntime
    from .demo_session import DemoSessionManager
    from .ui import MainWindow

LOGGER = logging.getLogger(__name__)


def configure_logging() -> None:
    """Enable INFO-level application logging for demo debugging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


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
    configure_logging()
    app = QApplication(sys.argv)
    session_manager = DemoSessionManager()
    runtime = session_manager.build_current_runtime()
    LOGGER.info(
        "startup_session_loaded session_id=%s session_kind=%s count=%s",
        runtime.session_id,
        runtime.session_kind,
        runtime.get_count(),
    )
    window = MainWindow(runtime, session_manager=session_manager)
    install_signal_handlers(app, window)
    window.resize(980, 680)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
