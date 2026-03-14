from __future__ import annotations

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from grip_py_demo.demo_runtime import DemoRuntime
from grip_py_demo.demo_session import DemoSessionManager
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


def test_session_controls_create_and_load_local_sessions(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])

    session_manager = DemoSessionManager(base_path=tmp_path)
    runtime = session_manager.build_current_runtime()
    window = MainWindow(runtime, session_manager=session_manager)
    window.show()
    app.processEvents()

    first_session_id = window._runtime.session_id
    assert first_session_id is not None
    window._runtime.increment_count()
    window._runtime.flush_local_persistence()

    window.new_session_button.click()
    app.processEvents()
    second_session_id = window._runtime.session_id
    assert second_session_id is not None
    assert second_session_id != first_session_id
    assert window._runtime.get_count() == 1

    index = window.session_combo.findData(first_session_id)
    assert index >= 0
    window.session_combo.setCurrentIndex(index)
    window.load_session_button.click()
    app.processEvents()

    assert window._runtime.session_id == first_session_id
    assert window._runtime.get_count() == 2
    window.close()
    app.processEvents()


def test_session_switch_preserves_ui_state_and_actions_target_current_runtime(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])

    session_manager = DemoSessionManager(base_path=tmp_path)
    runtime = session_manager.build_current_runtime()
    window = MainWindow(runtime, session_manager=session_manager)
    window.show()
    app.processEvents()

    first_session_id = window._runtime.session_id
    assert first_session_id is not None

    window.weather_tab_button.click()
    window.increment_button.click()
    app.processEvents()

    assert window._runtime.get_tab() == "weather"
    assert window._runtime.get_count() == 2
    assert window.stack.currentIndex() == 2
    assert not window.weather_tab_button.isEnabled()
    assert window.clock_tab_button.isEnabled()
    window.close()
    app.processEvents()
    window._runtime.flush_local_persistence()

    window.new_session_button.click()
    app.processEvents()

    second_session_id = window._runtime.session_id
    assert second_session_id is not None
    assert second_session_id != first_session_id
    assert window.stack.currentIndex() == 0
    assert not window.clock_tab_button.isEnabled()

    window.weather_tab_button.click()
    window.increment_button.click()
    app.processEvents()

    assert window._runtime.get_tab() == "weather"
    assert window._runtime.get_count() == 2
    assert window.stack.currentIndex() == 2
    assert not window.weather_tab_button.isEnabled()
    assert window.clock_tab_button.isEnabled()
    window._runtime.flush_local_persistence()

    index = window.session_combo.findData(first_session_id)
    assert index >= 0
    window.session_combo.setCurrentIndex(index)
    window.load_session_button.click()
    app.processEvents()

    assert window._runtime.session_id == first_session_id
    assert window._runtime.get_tab() == "weather"
    assert window._runtime.get_count() == 2
    assert window.stack.currentIndex() == 2
    assert not window.weather_tab_button.isEnabled()
    assert window.clock_tab_button.isEnabled()


def test_existing_session_can_be_loaded_after_startup(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])

    manager = DemoSessionManager(base_path=tmp_path)
    first = manager.ensure_current_session()
    first_runtime = manager.build_runtime(first.glial_session_id)
    first_runtime.set_tab("weather")
    first_runtime.increment_count()
    first_runtime.flush_local_persistence()
    first_runtime.close()

    second = manager.create_and_select_new_local_session()
    second_runtime = manager.build_runtime(second.glial_session_id)
    second_runtime.set_tab("calc")
    second_runtime.increment_count()
    second_runtime.increment_count()
    second_runtime.flush_local_persistence()
    second_runtime.close()

    restarted_manager = DemoSessionManager(base_path=tmp_path)
    runtime = restarted_manager.build_current_runtime()
    window = MainWindow(runtime, session_manager=restarted_manager)
    window.show()
    app.processEvents()

    assert window._runtime.session_id == second.glial_session_id
    assert window._runtime.get_tab() == "calc"
    assert window._runtime.get_count() == 3
    assert window.stack.currentIndex() == 1
    assert not window.calc_tab_button.isEnabled()

    index = window.session_combo.findData(first.glial_session_id)
    assert index >= 0
    window.session_combo.setCurrentIndex(index)
    window.load_session_button.click()
    app.processEvents()

    assert window._runtime.session_id == first.glial_session_id
    assert window._runtime.get_tab() == "weather"
    assert window._runtime.get_count() == 2
    assert window.stack.currentIndex() == 2
    assert not window.weather_tab_button.isEnabled()
    assert window.calc_tab_button.isEnabled()
    window.close()
    app.processEvents()


def test_switching_away_does_not_overwrite_previous_session_after_flush_delay(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])

    manager = DemoSessionManager(base_path=tmp_path)
    first = manager.ensure_current_session()
    first_runtime = manager.build_runtime(first.glial_session_id)
    _ = first_runtime.get_count()
    for _ in range(6):
        first_runtime.increment_count()
    first_runtime.flush_local_persistence()
    first_runtime.close()

    second = manager.create_and_select_new_local_session()
    second_runtime = manager.build_runtime(second.glial_session_id)
    _ = second_runtime.get_count()
    second_runtime.flush_local_persistence()
    second_runtime.close()

    manager.select_local_session(first.glial_session_id)

    restarted_manager = DemoSessionManager(base_path=tmp_path)
    runtime = restarted_manager.build_current_runtime()
    window = MainWindow(runtime, session_manager=restarted_manager)
    window.show()
    app.processEvents()

    assert window._runtime.session_id == first.glial_session_id
    assert window._runtime.get_count() == 7

    index = window.session_combo.findData(second.glial_session_id)
    assert index >= 0
    window.session_combo.setCurrentIndex(index)
    window.load_session_button.click()
    app.processEvents()

    time.sleep(0.5)
    app.processEvents()

    stored_first = restarted_manager.store.hydrate(first.glial_session_id)
    assert stored_first.snapshot.contexts["main-home"].drips["app:Count"].value == 7

    index = window.session_combo.findData(first.glial_session_id)
    assert index >= 0
    window.session_combo.setCurrentIndex(index)
    window.load_session_button.click()
    app.processEvents()

    assert window._runtime.session_id == first.glial_session_id
    assert window._runtime.get_count() == 7
    window.close()
    app.processEvents()


def test_remote_controls_are_disabled_when_glial_is_unavailable(tmp_path, monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])

    manager = DemoSessionManager(base_path=tmp_path)
    monkeypatch.setattr(manager, "probe_glial_availability", lambda: False)

    runtime = manager.build_current_runtime()
    window = MainWindow(runtime, session_manager=manager)
    window.show()
    app.processEvents()

    assert "Glial server unavailable" in window.glial_status_label.text()
    assert not window.storage_mode_combo.isEnabled()
    assert not window.shared_session_combo.isEnabled()
    assert not window.load_shared_button.isEnabled()
    assert not window.new_shared_button.isEnabled()
    assert not window.storage_session_combo.isEnabled()
    assert not window.load_storage_button.isEnabled()
    assert not window.new_storage_button.isEnabled()
    window.close()
    app.processEvents()
