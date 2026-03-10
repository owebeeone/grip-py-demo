"""Runtime orchestration and test-friendly interface for grip-py-demo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from glial_local.types import LauncherSessionKind
from glial_local import GripSessionStore
from grip_py import (
    Drip,
    GripContext,
    Grok,
    QueryBinding,
    TapMatcher,
    create_atom_value_tap,
    with_one_of,
)

from .constants import LOCATION_OPTIONS
from .demo_glial_sync import DemoGlialSessionSync
from .grips import DemoGrips, ProviderName, REGISTRY, TabName, WeatherGrips
from .openmeteo_taps import LocationToGeoTap, OpenMeteoWeatherTap
from .taps import CalculatorTap, ClockTap, FormulaWeatherTap


@dataclass(frozen=True, slots=True)
class WeatherSnapshot:
    provider: ProviderName
    location_label: str
    temp_c: float | None
    humidity_pct: int | None
    wind_speed_kph: int | None
    wind_dir: str
    rain_pct: int | None
    sunny_pct: int | None
    uv_index: float | None


class DemoRuntime:
    """High-level API around grip-py runtime used by tests and UI."""

    location_options = LOCATION_OPTIONS

    def __init__(
        self,
        *,
        initial_time: datetime | None = None,
        session_id: str | None = None,
        store: GripSessionStore | None = None,
        session_kind: LauncherSessionKind = "local",
        glial_base_url: str | None = None,
        glial_user_id: str = "demo-user",
    ) -> None:
        if (session_id is None) != (store is None):
            raise ValueError("session_id and store must either both be provided or both be omitted")
        self.registry = REGISTRY
        self.grips = DemoGrips
        self.weather_grips = WeatherGrips
        self.grok = Grok(self.registry)
        self._drips: dict[tuple[str, str], Drip[Any]] = {}
        self.session_id = session_id
        self._session_store = store
        self._session_kind = session_kind
        self._glial_sync: DemoGlialSessionSync | None = None

        self.main_context = self.grok.main_presentation_context

        self.clock_tap = ClockTap(self.grips, initial_time=initial_time)
        self.count_tap = create_atom_value_tap(self.grips.COUNT, initial=1)
        self.tab_tap = create_atom_value_tap(self.grips.CURRENT_TAB, initial="clock")
        self.page_size_tap = create_atom_value_tap(self.grips.PAGE_SIZE, initial=50)
        self.description_tap = create_atom_value_tap(
            self.grips.DESCRIPTION,
            initial="PySide6 demo using grip-py with manual refresh",
        )
        self.weather_provider_tap = create_atom_value_tap(
            self.grips.WEATHER_PROVIDER_NAME,
            initial="meteo",
        )
        self.calculator_tap = CalculatorTap(self.grips)
        self.location_to_geo_tap = LocationToGeoTap(self.weather_grips)

        home = self.grok.main_home_context
        home.register_tap(self.clock_tap)
        home.register_tap(self.count_tap)
        home.register_tap(self.tab_tap)
        home.register_tap(self.page_size_tap)
        home.register_tap(self.description_tap)
        home.register_tap(self.weather_provider_tap)
        home.register_tap(self.calculator_tap)
        home.register_tap(self.location_to_geo_tap)

        self.meteo_weather_tap = OpenMeteoWeatherTap(self.weather_grips)
        self.mock_weather_tap = FormulaWeatherTap(self.weather_grips, provider="mock")

        self._matcher = TapMatcher(self.grok.main_home_context, self.main_context)
        self._matcher.add_binding(
            QueryBinding(
                id="meteo-weather",
                query=with_one_of(self.grips.WEATHER_PROVIDER_NAME, "meteo").build(),
                tap=self.meteo_weather_tap,
                base_score=5,
            )
        )
        self._matcher.add_binding(
            QueryBinding(
                id="mock-weather",
                query=with_one_of(self.grips.WEATHER_PROVIDER_NAME, "mock").build(),
                tap=self.mock_weather_tap,
                base_score=5,
            )
        )

        self.header_context = self.main_context.create_child("header-weather")
        self.header_location_tap = create_atom_value_tap(
            self.weather_grips.WEATHER_LOCATION,
            initial="Sydney",
        )
        self.header_context.register_tap(self.header_location_tap)

        self.column_contexts: dict[str, GripContext] = {
            "A": self.main_context.create_child("weather-column-a"),
            "B": self.main_context.create_child("weather-column-b"),
        }
        self.location_taps = {
            "A": create_atom_value_tap(self.weather_grips.WEATHER_LOCATION, initial="Sydney"),
            "B": create_atom_value_tap(self.weather_grips.WEATHER_LOCATION, initial="Melbourne"),
        }
        self.column_contexts["A"].register_tap(self.location_taps["A"])
        self.column_contexts["B"].register_tap(self.location_taps["B"])

        if self._session_store is not None and self.session_id is not None:
            self.grok.attach_local_persistence(
                session_id=self.session_id,
                store=self._session_store,
                title="Grip Py Demo",
                flush_delay_ms=250,
            )
            if self._session_kind != "local" and glial_base_url is not None:
                self._glial_sync = DemoGlialSessionSync(
                    self,
                    session_id=self.session_id,
                    title="Grip Py Demo",
                    base_url=glial_base_url,
                    user_id=glial_user_id,
                    session_kind=self._session_kind,
                )
                self._glial_sync.start()

    @property
    def session_store(self) -> GripSessionStore:
        if self._session_store is None:
            raise RuntimeError("DemoRuntime was created without a session store")
        return self._session_store

    @property
    def session_kind(self) -> LauncherSessionKind:
        return self._session_kind

    def _read(self, grip: Any, *, ctx: GripContext | None = None) -> Any:
        return self.get_or_create_drip(grip, ctx=ctx).get()

    def get_or_create_drip(self, grip: Any, *, ctx: GripContext | None = None) -> Drip[Any]:
        context = ctx or self.main_context
        key = (context.id, grip.key)
        existing = self._drips.get(key)
        if existing is not None:
            return existing
        created = self.grok.query(grip, context)
        self._drips[key] = created
        return created

    def get_time(self) -> datetime:
        value = self._read(self.grips.CURRENT_TIME)
        return value if isinstance(value, datetime) else datetime.now().replace(microsecond=0)

    def get_page_size(self) -> int:
        return int(self._read(self.grips.PAGE_SIZE) or 0)

    def get_description(self) -> str:
        return str(self._read(self.grips.DESCRIPTION) or "")

    def get_count(self) -> int:
        return int(self._read(self.grips.COUNT) or 0)

    def increment_count(self) -> None:
        self.count_tap.update(lambda count: int(count or 0) + 1)

    def decrement_count(self) -> None:
        self.count_tap.update(lambda count: int(count or 0) - 1)

    def is_clock_visible(self) -> bool:
        return self.get_count() % 2 == 0

    def get_tab(self) -> TabName:
        tab = str(self._read(self.grips.CURRENT_TAB) or "clock")
        return tab if tab in {"clock", "calc", "weather"} else "clock"

    def set_tab(self, tab: TabName) -> None:
        if tab not in {"clock", "calc", "weather"}:
            raise ValueError(f"unsupported tab: {tab}")
        self.tab_tap.set(tab)

    def get_calc_display(self) -> str:
        return str(self._read(self.grips.CALC_DISPLAY) or "0")

    def _invoke_calc(self, grip: Any, *args: Any) -> None:
        fn = self._read(grip)
        if callable(fn):
            fn(*args)

    def press_digit(self, digit: int) -> None:
        self._invoke_calc(self.grips.CALC_DIGIT_PRESSED, digit)

    def press_operator(self, op: str) -> None:
        mapping = {
            "+": self.grips.CALC_ADD_PRESSED,
            "-": self.grips.CALC_SUB_PRESSED,
            "*": self.grips.CALC_MUL_PRESSED,
            "/": self.grips.CALC_DIV_PRESSED,
        }
        grip = mapping.get(op)
        if grip is None:
            raise ValueError(f"unsupported operator: {op}")
        self._invoke_calc(grip)

    def press_equals(self) -> None:
        self._invoke_calc(self.grips.CALC_EQUALS_PRESSED)

    def press_clear(self) -> None:
        self._invoke_calc(self.grips.CALC_CLEAR_PRESSED)

    def get_weather_provider(self) -> ProviderName:
        provider = str(self._read(self.grips.WEATHER_PROVIDER_NAME) or "meteo")
        return provider if provider in {"meteo", "mock"} else "meteo"

    def set_weather_provider(self, provider: ProviderName) -> None:
        if provider not in {"meteo", "mock"}:
            raise ValueError(f"unsupported provider: {provider}")
        self.weather_provider_tap.set(provider)

    def _column_context(self, column: str) -> GripContext:
        key = column.upper()
        if key not in self.column_contexts:
            raise ValueError(f"unsupported column: {column}")
        return self.column_contexts[key]

    def get_weather_location(self, column: str) -> str:
        context = self._column_context(column)
        return str(self._read(self.weather_grips.WEATHER_LOCATION, ctx=context) or "")

    def set_weather_location(self, column: str, location: str) -> None:
        key = column.upper()
        if key not in self.location_taps:
            raise ValueError(f"unsupported column: {column}")
        self.location_taps[key].set(location)

    def get_header_temp(self) -> float | None:
        temp = self._read(self.weather_grips.WEATHER_TEMP_C, ctx=self.header_context)
        return float(temp) if temp is not None else None

    def get_weather_snapshot(self, column: str) -> WeatherSnapshot:
        context = self._column_context(column)
        provider = self.get_weather_provider()
        return WeatherSnapshot(
            provider=provider,
            location_label=str(self._read(self.weather_grips.GEO_LABEL, ctx=context) or ""),
            temp_c=_to_float(self._read(self.weather_grips.WEATHER_TEMP_C, ctx=context)),
            humidity_pct=_to_int(self._read(self.weather_grips.WEATHER_HUMIDITY, ctx=context)),
            wind_speed_kph=_to_int(self._read(self.weather_grips.WEATHER_WIND_SPEED, ctx=context)),
            wind_dir=str(self._read(self.weather_grips.WEATHER_WIND_DIR, ctx=context) or ""),
            rain_pct=_to_int(self._read(self.weather_grips.WEATHER_RAIN_PCT, ctx=context)),
            sunny_pct=_to_int(self._read(self.weather_grips.WEATHER_SUNNY_PCT, ctx=context)),
            uv_index=_to_float(self._read(self.weather_grips.WEATHER_UV_INDEX, ctx=context)),
        )

    def tick_clock(self, seconds: int = 1) -> None:
        self.clock_tap.tick(seconds)

    def tick_weather(self, step: int = 1) -> None:
        # Poll asynchronous meteo taps and advance deterministic mock weather.
        self.location_to_geo_tap.produce()
        self.meteo_weather_tap.produce()
        self.mock_weather_tap.tick(step)

    def tick(self) -> None:
        self.tick_clock(1)
        self.tick_weather(1)
        if self._glial_sync is not None:
            self._glial_sync.sync_now()

    def flush_local_persistence(self) -> None:
        self.grok.flush_local_persistence()

    def close(self) -> None:
        self.flush_local_persistence()
        if self._glial_sync is not None:
            self._glial_sync.stop()
        self.grok.close()


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
