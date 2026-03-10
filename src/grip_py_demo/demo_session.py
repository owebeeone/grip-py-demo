"""Desktop session helpers for grip-py-demo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from glial_local import (
    FilesystemGripSessionStore,
    GripSessionStore,
    LauncherSessionRecord,
    LauncherSessionRecordStore,
    NewSessionRequest,
    bind_launcher_session_to_existing_session,
    create_launcher_session_id,
    ensure_launcher_session_record,
)

if False:  # pragma: no cover
    from .demo_runtime import DemoRuntime


DEFAULT_STATE_DIR = Path.home() / ".grip-py-demo"


@dataclass(frozen=True, slots=True)
class DemoLauncherSession:
    launcher_session_id: str
    glial_session_id: str
    storage_mode: str
    title: str | None
    store: GripSessionStore


class DemoSessionStore(GripSessionStore, LauncherSessionRecordStore):
    """Combined store interface used by the demo."""


class DemoSessionManager:
    """Owns local demo session browsing and current-session selection."""

    def __init__(
        self,
        *,
        base_path: str | Path | None = None,
        store: DemoSessionStore | None = None,
    ) -> None:
        self._base_path = Path(base_path) if base_path is not None else DEFAULT_STATE_DIR
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._store = store or FilesystemGripSessionStore(self._base_path / "sessions")

    @property
    def store(self) -> DemoSessionStore:
        return self._store

    def ensure_current_session(self) -> DemoLauncherSession:
        launcher_session_id = self._get_or_create_launcher_session_id()
        record = ensure_launcher_session_record(
            self._store,
            launcher_session_id,
            title="Grip Py Demo",
            storage_mode="local",
        )
        return self._wrap_record(record)

    def list_local_sessions(self):
        return self._store.list_sessions()

    def select_local_session(self, glial_session_id: str) -> DemoLauncherSession:
        launcher_session_id = self._get_or_create_launcher_session_id()
        session = self._store.get_session(glial_session_id)
        if session is None:
            raise KeyError(f"unknown session: {glial_session_id}")
        record = bind_launcher_session_to_existing_session(
            self._store,
            launcher_session_id,
            session,
            "local",
        )
        return self._wrap_record(record)

    def create_and_select_new_local_session(self) -> DemoLauncherSession:
        launcher_session_id = self._get_or_create_launcher_session_id()
        session = self._store.new_session(NewSessionRequest(title="Grip Py Demo"))
        record = bind_launcher_session_to_existing_session(
            self._store,
            launcher_session_id,
            session,
            "local",
        )
        return self._wrap_record(record)

    def build_current_runtime(self, *, initial_time: datetime | None = None):
        session = self.ensure_current_session()
        return self.build_runtime(session.glial_session_id, initial_time=initial_time)

    def build_runtime(
        self,
        glial_session_id: str,
        *,
        initial_time: datetime | None = None,
    ):
        from .demo_runtime import DemoRuntime

        return DemoRuntime(
            initial_time=initial_time,
            session_id=glial_session_id,
            store=self._store,
        )

    def _get_or_create_launcher_session_id(self) -> str:
        path = self._current_launcher_session_path()
        if path.exists():
            value = path.read_text().strip()
            if value:
                return value
        launcher_session_id = create_launcher_session_id("demo")
        path.write_text(launcher_session_id)
        return launcher_session_id

    def _current_launcher_session_path(self) -> Path:
        return self._base_path / "current_launcher_session_id.txt"

    def _wrap_record(self, record: LauncherSessionRecord) -> DemoLauncherSession:
        return DemoLauncherSession(
            launcher_session_id=record.launcher_session_id,
            glial_session_id=record.glial_session_id,
            storage_mode=record.storage_mode,
            title=record.title,
            store=self._store,
        )
