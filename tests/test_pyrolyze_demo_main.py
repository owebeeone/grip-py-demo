from __future__ import annotations

from PySide6.QtWidgets import QMainWindow
from PySide6.QtWidgets import QLabel


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


def test_pyrolyze_demo_initial_view_is_clock_and_tab_switches() -> None:
    from grip_pyrolyze_demo.main import build_app_host

    host, ctx, runtime = build_app_host()
    try:
        root = host.root_widget
        labels = [widget.text() for widget in root.findChildren(QLabel)]
        assert "Page size: 50" in labels
        assert not any(text.startswith("Current weather provider:") for text in labels)

        runtime.set_tab("weather")
        host.app.processEvents()
        host.app.processEvents()

        labels = [widget.text() for widget in root.findChildren(QLabel)]
        assert any(text.startswith("Current weather provider:") for text in labels)
    finally:
        host.close()
        ctx.close_app_contexts()
