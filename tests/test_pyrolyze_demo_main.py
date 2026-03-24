from __future__ import annotations

from PySide6.QtWidgets import QMainWindow


def test_pyrolyze_demo_build_app_host_mounts_root_window() -> None:
    from grip_pyrolyze_demo.main import build_app_host

    host, ctx, runtime = build_app_host()
    try:
        assert isinstance(host.root_widget, QMainWindow)
        assert host.root_widget.windowTitle() == "Grip PyRolyze Demo"
        assert runtime.main_context is runtime.grok.main_presentation_context
        assert len(ctx.committed_ui()) == 1
    finally:
        host.close()
        ctx.close_app_contexts()
