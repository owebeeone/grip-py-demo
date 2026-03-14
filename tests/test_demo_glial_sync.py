from __future__ import annotations

from dataclasses import asdict
from typing import Any

from glial_local.in_memory import InMemoryGripSessionStore
from glial_local.types import NewSessionRequest
from grip_py_demo.demo_glial_sync import DemoGlialSessionSync
from grip_py_demo.demo_runtime import DemoRuntime


def _read_count_from_snapshot(snapshot: dict[str, Any]) -> int | None:
    contexts = snapshot.get("contexts", {})
    for context in contexts.values():
        drips = context.get("drips", {})
        value = drips.get("app:Count", {}).get("value")
        if isinstance(value, int):
            return value
    return None


class FakeDemoGlialClient:
    def __init__(self, snapshot: dict[str, Any], last_modified_ms: int = 1) -> None:
        self.remote_snapshot = snapshot
        self.remote_last_modified_ms = last_modified_ms
        self.load_calls = 0
        self.save_calls = 0
        self.shared_save_calls = 0

    def load_remote_session(self, _user_id: str, _session_id: str) -> dict[str, Any]:
        self.load_calls += 1
        return {
            "session_id": "demo-sync",
            "snapshot": self.remote_snapshot,
            "last_modified_ms": self.remote_last_modified_ms,
        }

    def save_remote_session(
        self,
        _user_id: str,
        _session_id: str,
        snapshot: dict[str, Any],
        *,
        title: str | None = None,
    ) -> dict[str, Any]:
        _ = title
        self.save_calls += 1
        self.remote_snapshot = snapshot
        self.remote_last_modified_ms += 1
        return {
            "session_id": "demo-sync",
            "snapshot": self.remote_snapshot,
            "last_modified_ms": self.remote_last_modified_ms,
        }

    def save_shared_session(
        self,
        _user_id: str,
        _session_id: str,
        snapshot: dict[str, Any],
        *,
        title: str | None = None,
    ) -> dict[str, Any]:
        _ = title
        self.shared_save_calls += 1
        return {
            "session_id": "demo-sync",
            "snapshot": snapshot,
            "leases": {},
            "last_modified_ms": self.remote_last_modified_ms,
        }

    def close(self) -> None:
        return None


def _create_runtime() -> tuple[DemoRuntime, InMemoryGripSessionStore]:
    store = InMemoryGripSessionStore()
    session = store.new_session(NewSessionRequest(session_id="demo-sync", title="Demo Sync"))
    runtime = DemoRuntime(
        session_id=session.session_id,
        store=store,
        session_kind="local",
    )
    runtime.flush_local_persistence()
    return runtime, store


def test_sync_prefers_unsynced_local_changes_over_newer_remote_snapshot() -> None:
    runtime, store = _create_runtime()
    initial_snapshot = asdict(store.hydrate("demo-sync").snapshot)
    client = FakeDemoGlialClient(initial_snapshot, last_modified_ms=10)
    now = 0

    sync = DemoGlialSessionSync(
        runtime,
        session_id="demo-sync",
        title="Grip Py Demo",
        base_url="http://glial.test",
        user_id="demo-user",
        session_kind="glial-shared",
        client=client,
        remote_poll_min_ms=100,
        remote_poll_max_ms=500,
        now_ms=lambda: now,
    )

    sync.start()

    runtime.increment_count()
    runtime.flush_local_persistence()
    stale_remote_snapshot = asdict(store.hydrate("demo-sync").snapshot)

    runtime.increment_count()
    client.remote_snapshot = stale_remote_snapshot
    client.remote_last_modified_ms = 11

    now = 200
    sync.sync_now()

    assert runtime.get_count() == 3
    assert _read_count_from_snapshot(client.remote_snapshot) == 3
    assert client.save_calls == 1
    runtime.close()


def test_sync_backs_off_remote_polling_while_idle() -> None:
    runtime, store = _create_runtime()
    initial_snapshot = asdict(store.hydrate("demo-sync").snapshot)
    client = FakeDemoGlialClient(initial_snapshot, last_modified_ms=10)
    now = 0

    sync = DemoGlialSessionSync(
        runtime,
        session_id="demo-sync",
        title="Grip Py Demo",
        base_url="http://glial.test",
        user_id="demo-user",
        session_kind="glial-shared",
        client=client,
        remote_poll_min_ms=100,
        remote_poll_max_ms=400,
        now_ms=lambda: now,
    )

    sync.start()
    assert client.load_calls == 1

    sync.sync_now()
    assert client.load_calls == 1

    now = 100
    sync.sync_now()
    assert client.load_calls == 2

    now = 250
    sync.sync_now()
    assert client.load_calls == 2

    now = 350
    sync.sync_now()
    assert client.load_calls == 3
    runtime.close()
