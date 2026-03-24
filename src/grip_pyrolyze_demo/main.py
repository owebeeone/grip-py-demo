"""PyRolyze application entry point."""

from __future__ import annotations

import signal
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer

from pyrolyze.pyrolyze_native_pyside6 import create_host, reconcile_window_content
from pyrolyze.runtime import AppContextStore, RenderContext, dirtyof

from grip_pyrolyze import GRIP_PYROLYZE_SESSION_KEY, GripPyrolyzeSession

if __package__ in {None, ""}:
    src_root = Path(__file__).resolve().parents[1]
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))
    from grip_pyrolyze_demo.demo_runtime import DemoRuntime
    from grip_pyrolyze_demo.ui import grip_pyrolyze_demo_app
else:
    from .demo_runtime import DemoRuntime
    from .ui import grip_pyrolyze_demo_app


def _build_app_context_store(runtime: DemoRuntime, host_app: object | None) -> AppContextStore:
    store = AppContextStore(host_app=host_app)
    store._values[GRIP_PYROLYZE_SESSION_KEY] = GripPyrolyzeSession(
        grok=runtime.grok,
        main_home_context=runtime.grok.main_home_context,
        main_presentation_context=runtime.main_context,
        host_app=host_app,
    )
    store._creation_order.append(GRIP_PYROLYZE_SESSION_KEY)
    return store


def build_app_host() -> tuple[Any, RenderContext, DemoRuntime]:
    runtime = DemoRuntime()
    host = create_host()
    ctx = RenderContext(app_context_store=_build_app_context_store(runtime, host.app))

    def reconcile_host() -> None:
        reconcile_window_content(host, ctx.committed_ui())

    def render_root() -> None:
        grip_pyrolyze_demo_app._pyrolyze_meta._func(ctx, dirtyof(), runtime)
        reconcile_host()

    def post_flush(callback: Any) -> None:
        QTimer.singleShot(
            0,
            lambda: (
                callback(),
                reconcile_host(),
            ),
        )

    tick_timer = QTimer(host.app)
    tick_timer.setInterval(1000)
    tick_timer.timeout.connect(runtime.tick)
    tick_timer.start()
    setattr(host.app, "_demo_tick_timer", tick_timer)

    ctx.set_flush_poster(post_flush)
    ctx.mount(render_root)
    return host, ctx, runtime


def install_signal_handlers(host: Any, ctx: RenderContext) -> None:
    shutting_down = False

    def request_shutdown() -> None:
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        host.close()
        ctx.close_app_contexts()
        host.app.quit()

    def on_signal(_sig_num: int, _frame) -> None:
        QTimer.singleShot(0, request_shutdown)

    signal.signal(signal.SIGINT, on_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, on_signal)

    heartbeat = QTimer(host.app)
    heartbeat.setInterval(200)
    heartbeat.timeout.connect(lambda: None)
    heartbeat.start()
    setattr(host.app, "_signal_heartbeat", heartbeat)


def main() -> int:
    host, ctx, _runtime = build_app_host()
    install_signal_handlers(host, ctx)
    try:
        return host.exec()
    finally:
        ctx.close_app_contexts()


if __name__ == "__main__":
    raise SystemExit(main())
