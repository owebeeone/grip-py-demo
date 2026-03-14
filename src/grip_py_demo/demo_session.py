"""Desktop session helpers for grip-py-demo."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import os
from pathlib import Path

from glial_local import (
    FilesystemGripSessionStore,
    GripSessionStore,
    LauncherSessionKind,
    LauncherSessionRecord,
    LauncherSessionRecordStore,
    LauncherSessionStorageMode,
    NewSessionRequest,
    SessionSummary,
    bind_launcher_session_to_existing_session,
    create_launcher_session_id,
    ensure_launcher_session_record,
)
from glial_net import HttpGlialClient

if False:  # pragma: no cover
    from .demo_runtime import DemoRuntime


DEFAULT_STATE_DIR = Path.home() / ".grip-py-demo"


@dataclass(frozen=True, slots=True)
class DemoLauncherSession:
    launcher_session_id: str
    glial_session_id: str
    storage_mode: str
    session_kind: LauncherSessionKind
    title: str | None
    store: GripSessionStore
    glial_base_url: str
    glial_user_id: str


class DemoSessionStore(GripSessionStore, LauncherSessionRecordStore):
    """Combined store interface used by the demo."""


class DemoSessionManager:
    """Owns local demo session browsing and current-session selection."""

    def __init__(
        self,
        *,
        base_path: str | Path | None = None,
        store: DemoSessionStore | None = None,
        glial_base_url: str | None = None,
        glial_user_id: str | None = None,
    ) -> None:
        self._base_path = Path(base_path) if base_path is not None else DEFAULT_STATE_DIR
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._store = store or FilesystemGripSessionStore(self._base_path / "sessions")
        self._glial_base_url = (
            glial_base_url or os.environ.get("GLIAL_BASE_URL") or "http://127.0.0.1:8000"
        ).rstrip("/")
        self._glial_user_id = glial_user_id or os.environ.get("GLIAL_USER_ID") or "demo-user"

    @property
    def store(self) -> DemoSessionStore:
        return self._store

    @property
    def glial_base_url(self) -> str:
        return self._glial_base_url

    @property
    def glial_user_id(self) -> str:
        return self._glial_user_id

    def ensure_current_session(self) -> DemoLauncherSession:
        launcher_session_id = self._get_or_create_launcher_session_id()
        record = ensure_launcher_session_record(
            self._store,
            launcher_session_id,
            title="Grip Py Demo",
            storage_mode="local",
            session_kind="local",
        )
        return self._wrap_record(record)

    def ensure_runnable_current_session(self) -> DemoLauncherSession:
        session = self.ensure_current_session()
        if session.session_kind == "local":
            return session
        client = self._create_glial_client()
        try:
            client.load_remote_session(self._glial_user_id, session.glial_session_id)
            return session
        except Exception:
            return self._downgrade_launcher_session_to_local(session)
        finally:
            self._close_glial_client(client)

    def list_local_sessions(self) -> list[SessionSummary]:
        return self._store.list_sessions()

    def list_remote_sessions(self) -> list[SessionSummary]:
        client = self._create_glial_client()
        try:
            sessions = client.list_remote_sessions(self._glial_user_id)
            return [
                SessionSummary(
                    session_id=str(session["session_id"]),
                    title=session.get("title"),
                    mode="shared",
                    last_modified_ms=int(session["last_modified_ms"]),
                )
                for session in sessions
            ]
        finally:
            self._close_glial_client(client)

    def probe_glial_availability(self) -> bool:
        client = self._create_glial_client()
        try:
            client.list_remote_sessions(self._glial_user_id)
            return True
        except Exception:
            return False
        finally:
            self._close_glial_client(client)

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
            "local",
        )
        return self._wrap_record(record)

    def select_remote_session(
        self,
        glial_session_id: str,
        *,
        session_kind: LauncherSessionKind,
        storage_mode: LauncherSessionStorageMode,
    ) -> DemoLauncherSession:
        launcher_session_id = self._get_or_create_launcher_session_id()
        client = self._create_glial_client()
        try:
            remote = client.load_remote_session(
                self._glial_user_id,
                glial_session_id,
            )
        finally:
            self._close_glial_client(client)
        if self._store.get_session(glial_session_id) is None:
            self._store.new_session(
                NewSessionRequest(
                    session_id=glial_session_id,
                    title=remote.get("title"),
                )
            )
        record = LauncherSessionRecord(
            launcher_session_id=launcher_session_id,
            glial_session_id=glial_session_id,
            title=remote.get("title"),
            storage_mode=storage_mode,
            session_kind=session_kind,
            last_opened_ms=int(datetime.now().timestamp() * 1000),
        )
        self._store.put_launcher_session(record)
        return self._wrap_record(record)

    def create_and_select_new_remote_session(
        self,
        *,
        session_kind: LauncherSessionKind,
        storage_mode: LauncherSessionStorageMode,
    ) -> DemoLauncherSession:
        launcher_session_id = self._get_or_create_launcher_session_id()
        session = self._store.new_session(NewSessionRequest(title="Grip Py Demo (Glial)"))
        hydrated = self._store.hydrate(session.session_id)
        client = self._create_glial_client()
        try:
            remote = client.save_remote_session(
                self._glial_user_id,
                session.session_id,
                asdict(hydrated.snapshot),
                title=session.title or "Grip Py Demo (Glial)",
            )
        finally:
            self._close_glial_client(client)
        record = LauncherSessionRecord(
            launcher_session_id=launcher_session_id,
            glial_session_id=session.session_id,
            title=remote.get("title"),
            storage_mode=storage_mode,
            session_kind=session_kind,
            last_opened_ms=int(datetime.now().timestamp() * 1000),
        )
        self._store.put_launcher_session(record)
        return self._wrap_record(record)

    def build_current_runtime(self, *, initial_time: datetime | None = None):
        session = self.ensure_runnable_current_session()
        return self.build_runtime(
            session.glial_session_id,
            initial_time=initial_time,
            session_kind=session.session_kind,
        )

    def build_runtime(
        self,
        glial_session_id: str,
        *,
        initial_time: datetime | None = None,
        session_kind: LauncherSessionKind = "local",
    ):
        from .demo_runtime import DemoRuntime

        return DemoRuntime(
            initial_time=initial_time,
            session_id=glial_session_id,
            store=self._store,
            session_kind=session_kind,
            glial_base_url=self._glial_base_url,
            glial_user_id=self._glial_user_id,
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
            session_kind=record.session_kind,
            title=record.title,
            store=self._store,
            glial_base_url=self._glial_base_url,
            glial_user_id=self._glial_user_id,
        )

    def _create_glial_client(self) -> HttpGlialClient:
        return HttpGlialClient(base_url=self._glial_base_url)

    def _downgrade_launcher_session_to_local(
        self,
        session: DemoLauncherSession,
    ) -> DemoLauncherSession:
        local_session = self._store.get_session(session.glial_session_id)
        if local_session is None:
            local_session = self._store.new_session(
                NewSessionRequest(
                    session_id=session.glial_session_id,
                    title=session.title or "Grip Py Demo",
                )
            )
        record = bind_launcher_session_to_existing_session(
            self._store,
            session.launcher_session_id,
            local_session,
            "local",
            "local",
        )
        return self._wrap_record(record)

    @staticmethod
    def _close_glial_client(client: HttpGlialClient) -> None:
        client.close()
