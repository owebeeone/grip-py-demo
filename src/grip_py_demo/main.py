"""Application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .demo_runtime import DemoRuntime
from .ui import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    runtime = DemoRuntime()
    window = MainWindow(runtime)
    window.resize(980, 680)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
