"""Demo-oriented Glial source-state synchronization helpers."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, cast

from glial_net import HttpGlialClient
from glial_local.types import ContextState, DripState, SessionSnapshot, TapExport
from grip_py.core.local_persistence import (
    apply_local_persistence_snapshot,
    build_shared_projection_snapshot,
)

if False:  # pragma: no cover
    from .demo_runtime import DemoRuntime


def _tap_from_dict(data: dict[str, Any]) -> TapExport:
    return TapExport(
        tap_id=str(data["tap_id"]),
        tap_type=str(data["tap_type"]),
        mode=str(data["mode"]),
        role=cast(str | None, data.get("role")),
        provides=[str(item) for item in data.get("provides", [])],
        home_param_grips=[str(item) for item in data.get("home_param_grips", [])],
        destination_param_grips=[str(item) for item in data.get("destination_param_grips", [])],
        purpose=cast(str | None, data.get("purpose")),
        description=cast(str | None, data.get("description")),
        metadata=cast(dict[str, Any] | None, data.get("metadata")),
        cache_state=cast(dict[str, Any] | None, data.get("cache_state")),
    )


def _drip_from_dict(data: dict[str, Any]) -> DripState:
    return DripState(
        grip_id=str(data["grip_id"]),
        name=str(data["name"]),
        value=data.get("value"),
        taps=[_tap_from_dict(cast(dict[str, Any], item)) for item in data.get("taps", [])],
    )


def _context_from_dict(data: dict[str, Any]) -> ContextState:
    return ContextState(
        path=str(data["path"]),
        name=str(data["name"]),
        children=[str(item) for item in data.get("children", [])],
        drips={
            str(key): _drip_from_dict(cast(dict[str, Any], value))
            for key, value in cast(dict[str, Any], data.get("drips", {})).items()
        },
        purpose=cast(str | None, data.get("purpose")),
        description=cast(str | None, data.get("description")),
    )


def _snapshot_from_dict(data: dict[str, Any]) -> SessionSnapshot:
    return SessionSnapshot(
        session_id=cast(str | None, data.get("session_id")),
        contexts={
            str(key): _context_from_dict(cast(dict[str, Any], value))
            for key, value in cast(dict[str, Any], data.get("contexts", {})).items()
        },
    )


def _stable_snapshot_signature(snapshot: SessionSnapshot) -> str:
    return str(asdict(snapshot))


def _is_missing_remote_session_error(error: BaseException) -> bool:
    return isinstance(error, Exception) and "404" in str(error)


class DemoGlialSessionSync:
    """Poll-based source-state synchronization for the headed demos."""

    def __init__(
        self,
        runtime: DemoRuntime,
        *,
        session_id: str,
        title: str | None,
        base_url: str,
        user_id: str,
        session_kind: str,
    ) -> None:
        self._runtime = runtime
        self._store = runtime.session_store
        self._session_id = session_id
        self._title = title
        self._client = HttpGlialClient(base_url=base_url)
        self._user_id = user_id
        self._session_kind = session_kind
        self._last_remote_modified_ms = 0
        self._last_applied_signature = ""
        self._last_shared_signature = ""
        self._syncing = False

    def start(self) -> None:
        local_snapshot = self._read_local_snapshot()
        self._last_applied_signature = _stable_snapshot_signature(local_snapshot)
        if self._session_kind == "glial-shared":
            self._last_shared_signature = ""
        try:
            remote = self._client.load_remote_session(self._user_id, self._session_id)
        except Exception as error:
            if not _is_missing_remote_session_error(error):
                raise
            saved = self._client.save_remote_session(
                self._user_id,
                self._session_id,
                asdict(local_snapshot),
                title=self._title,
            )
            self._last_remote_modified_ms = int(saved["last_modified_ms"])
            if self._session_kind == "glial-shared":
                self._save_shared_snapshot()
            return

        self._last_remote_modified_ms = int(remote["last_modified_ms"])
        remote_snapshot = _snapshot_from_dict(cast(dict[str, Any], remote["snapshot"]))
        remote_signature = _stable_snapshot_signature(remote_snapshot)
        if remote_signature != self._last_applied_signature:
            self._apply_remote_snapshot(remote_snapshot)
            self._last_applied_signature = remote_signature
        if self._session_kind == "glial-shared":
            self._save_shared_snapshot()

    def sync_now(self) -> None:
        if self._syncing:
            return
        self._syncing = True
        try:
            local_snapshot = self._read_local_snapshot()
            local_signature = _stable_snapshot_signature(local_snapshot)

            if self._session_kind == "glial-shared":
                try:
                    remote = self._client.load_remote_session(self._user_id, self._session_id)
                    remote_modified_ms = int(remote["last_modified_ms"])
                    remote_snapshot = _snapshot_from_dict(cast(dict[str, Any], remote["snapshot"]))
                    remote_signature = _stable_snapshot_signature(remote_snapshot)
                    if (
                        remote_modified_ms > self._last_remote_modified_ms
                        and remote_signature != local_signature
                    ):
                        self._apply_remote_snapshot(remote_snapshot)
                        self._last_remote_modified_ms = remote_modified_ms
                        self._last_applied_signature = remote_signature
                        return
                    self._last_remote_modified_ms = max(self._last_remote_modified_ms, remote_modified_ms)
                except Exception as error:
                    if not _is_missing_remote_session_error(error):
                        raise

            if local_signature == self._last_applied_signature:
                return

            saved = self._client.save_remote_session(
                self._user_id,
                self._session_id,
                asdict(local_snapshot),
                title=self._title,
            )
            self._last_remote_modified_ms = int(saved["last_modified_ms"])
            self._last_applied_signature = local_signature
            if self._session_kind == "glial-shared":
                self._save_shared_snapshot()
        finally:
            self._syncing = False

    def stop(self) -> None:
        self.sync_now()
        self._client.close()

    def _read_local_snapshot(self) -> SessionSnapshot:
        self._runtime.flush_local_persistence()
        return self._store.hydrate(self._session_id).snapshot

    def _apply_remote_snapshot(self, snapshot: SessionSnapshot) -> None:
        self._runtime.grok.run_with_local_persistence_suppressed(
            lambda: apply_local_persistence_snapshot(self._runtime.grok, snapshot)
        )
        self._store.replace_snapshot(self._session_id, snapshot, "glial_resync")

    def _read_local_shared_snapshot(self) -> dict[str, Any]:
        snapshot = build_shared_projection_snapshot(self._runtime.grok, self._session_id)
        return cast(dict[str, Any], asdict(snapshot))

    def _save_shared_snapshot(self) -> None:
        shared_snapshot = self._read_local_shared_snapshot()
        shared_signature = str(shared_snapshot)
        if shared_signature == self._last_shared_signature:
            return
        self._client.save_shared_session(
            self._user_id,
            self._session_id,
            shared_snapshot,
            title=self._title,
        )
        self._last_shared_signature = shared_signature
