"""Qt bridge that maps drip updates to fine-grained UI notifications."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, Signal

from .demo_runtime import DemoRuntime


class RuntimeBridge(QObject):
    """Subscribe to relevant drips and emit change events per grip/context key."""

    grip_changed = Signal(str, str)

    def __init__(self, runtime: DemoRuntime):
        super().__init__()
        self._runtime = runtime
        self._unsubscribers: list[Callable[[], None]] = []
        self._drips: dict[tuple[str, str], Any] = {}
        self._subscribe_all()

    def _subscribe(self, grip, ctx) -> None:
        ctx_id = ctx.id
        grip_key = grip.key
        key = (ctx_id, grip_key)
        drip = self._runtime.get_or_create_drip(grip, ctx=ctx)
        self._drips[key] = drip

        async def on_value(
            _value,
            *,
            current_ctx_id: str = ctx_id,
            current_grip_key: str = grip_key,
        ) -> None:
            self.grip_changed.emit(current_ctx_id, current_grip_key)

        unsubscribe = drip.subscribe_async(on_value)
        self._unsubscribers.append(unsubscribe)

    def read(self, grip, *, ctx=None):
        context = ctx or self._runtime.main_context
        key = (context.id, grip.key)
        drip = self._drips.get(key)
        if drip is None:
            drip = self._runtime.get_or_create_drip(grip, ctx=context)
            self._drips[key] = drip
        return drip.get()

    def _subscribe_all(self) -> None:
        main = self._runtime.main_context
        for grip in (
            self._runtime.grips.CURRENT_TIME,
            self._runtime.grips.PAGE_SIZE,
            self._runtime.grips.DESCRIPTION,
            self._runtime.grips.COUNT,
            self._runtime.grips.CURRENT_TAB,
            self._runtime.grips.CALC_DISPLAY,
            self._runtime.grips.WEATHER_PROVIDER_NAME,
        ):
            self._subscribe(grip, main)

        for ctx in (self._runtime.header_context, *self._runtime.column_contexts.values()):
            for grip in (
                self._runtime.weather_grips.WEATHER_LOCATION,
                self._runtime.weather_grips.GEO_LABEL,
                self._runtime.weather_grips.WEATHER_TEMP_C,
                self._runtime.weather_grips.WEATHER_HUMIDITY,
                self._runtime.weather_grips.WEATHER_WIND_SPEED,
                self._runtime.weather_grips.WEATHER_WIND_DIR,
                self._runtime.weather_grips.WEATHER_RAIN_PCT,
                self._runtime.weather_grips.WEATHER_SUNNY_PCT,
                self._runtime.weather_grips.WEATHER_UV_INDEX,
            ):
                self._subscribe(grip, ctx)

    def dispose(self) -> None:
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        self._drips.clear()
