from __future__ import annotations

from grip_py_demo.demo_session import DemoSessionManager


def test_demo_session_manager_reuses_launcher_mapping_and_switches_sessions(tmp_path) -> None:
    manager = DemoSessionManager(base_path=tmp_path)

    initial = manager.ensure_current_session()
    restored = DemoSessionManager(base_path=tmp_path).ensure_current_session()
    assert restored.launcher_session_id == initial.launcher_session_id
    assert restored.glial_session_id == initial.glial_session_id

    created = manager.create_and_select_new_local_session()
    assert created.launcher_session_id == initial.launcher_session_id
    assert created.glial_session_id != initial.glial_session_id

    listed = manager.list_local_sessions()
    listed_ids = {entry.session_id for entry in listed}
    assert initial.glial_session_id in listed_ids
    assert created.glial_session_id in listed_ids

    selected = manager.select_local_session(initial.glial_session_id)
    assert selected.glial_session_id == initial.glial_session_id
