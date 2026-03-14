from __future__ import annotations

from glial_local import LauncherSessionRecord

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


def test_build_current_runtime_downgrades_persisted_remote_session_when_glial_is_unavailable(
    tmp_path,
    monkeypatch,
) -> None:
    manager = DemoSessionManager(base_path=tmp_path)
    initial = manager.ensure_current_session()
    manager.store.put_launcher_session(
        LauncherSessionRecord(
            launcher_session_id=initial.launcher_session_id,
            glial_session_id=initial.glial_session_id,
            title=initial.title,
            storage_mode="remote",
            session_kind="glial-shared",
            last_opened_ms=1,
        )
    )

    class OfflineClient:
        def load_remote_session(self, _user_id: str, _session_id: str) -> dict[str, object]:
            raise RuntimeError("offline")

        def list_remote_sessions(self, _user_id: str) -> list[dict[str, object]]:
            raise RuntimeError("offline")

        def close(self) -> None:
            return None

    monkeypatch.setattr(manager, "_create_glial_client", lambda: OfflineClient())

    runtime = manager.build_current_runtime()
    current = manager.ensure_current_session()

    assert runtime.session_kind == "local"
    assert current.session_kind == "local"
    assert current.glial_session_id == initial.glial_session_id
