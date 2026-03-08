"""Qt bridge that turns drip updates into explicit render signals."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Signal

from .demo_runtime import DemoRuntime


class RuntimeBridge(QObject):
    """Subscribe to relevant drips and emit a render signal on each update."""

    state_changed = Signal()

    def __init__(self, runtime: DemoRuntime):
        super().__init__()
        self._runtime = runtime
        self._unsubscribers: list[Callable[[], None]] = []
        self._subscribe_all()

    def _subscribe(self, grip, ctx) -> None:
        drip = self._runtime.grok.query(grip, ctx)
        unsubscribe = drip.subscribe_priority(lambda _value: self.state_changed.emit())
        self._unsubscribers.append(unsubscribe)

    def _subscribe_all(self) -> None:
        main = self._runtime.main_context
        for grip in (
            self._runtime.grips.current_time,
            self._runtime.grips.page_size,
            self._runtime.grips.description,
            self._runtime.grips.count,
            self._runtime.grips.current_tab,
            self._runtime.grips.calc_display,
            self._runtime.grips.weather_provider_name,
        ):
            self._subscribe(grip, main)

        for ctx in (self._runtime.header_context, *self._runtime.column_contexts.values()):
            for grip in (
                self._runtime.weather_grips.weather_location,
                self._runtime.weather_grips.geo_label,
                self._runtime.weather_grips.weather_temp_c,
                self._runtime.weather_grips.weather_humidity,
                self._runtime.weather_grips.weather_wind_speed,
                self._runtime.weather_grips.weather_wind_dir,
                self._runtime.weather_grips.weather_rain_pct,
                self._runtime.weather_grips.weather_sunny_pct,
                self._runtime.weather_grips.weather_uv_index,
            ):
                self._subscribe(grip, ctx)

    def dispose(self) -> None:
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
