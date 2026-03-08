"""Runtime orchestration and test-friendly interface for grip-py-demo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from grip_py import (
    GripContext,
    GripRegistry,
    Grok,
    Query,
    QueryBinding,
    TapMatcher,
    create_atom_value_tap,
    use_grip,
)

from .constants import LOCATION_OPTIONS
from .grips import DemoGrips, ProviderName, TabName, WeatherGrips, define_demo_grips, define_weather_grips
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

    def __init__(self, *, initial_time: datetime | None = None) -> None:
        self.registry = GripRegistry()
        self.grips: DemoGrips = define_demo_grips(self.registry)
        self.weather_grips: WeatherGrips = define_weather_grips(self.registry)
        self.grok = Grok(self.registry)

        self.main_context = self.grok.main_presentation_context

        self.clock_tap = ClockTap(self.grips, initial_time=initial_time)
        self.count_tap = create_atom_value_tap(self.grips.count, initial=1)
        self.tab_tap = create_atom_value_tap(self.grips.current_tab, initial="clock")
        self.page_size_tap = create_atom_value_tap(self.grips.page_size, initial=50)
        self.description_tap = create_atom_value_tap(
            self.grips.description,
            initial="PySide6 demo using grip-py with manual refresh",
        )
        self.weather_provider_tap = create_atom_value_tap(
            self.grips.weather_provider_name,
            initial="meteo",
        )
        self.calculator_tap = CalculatorTap(self.grips)

        home = self.grok.main_home_context
        home.register_tap(self.clock_tap)
        home.register_tap(self.count_tap)
        home.register_tap(self.tab_tap)
        home.register_tap(self.page_size_tap)
        home.register_tap(self.description_tap)
        home.register_tap(self.weather_provider_tap)
        home.register_tap(self.calculator_tap)

        self.meteo_weather_tap = FormulaWeatherTap(self.weather_grips, provider="meteo")
        self.mock_weather_tap = FormulaWeatherTap(self.weather_grips, provider="mock")

        self._matcher = TapMatcher(self.grok.main_home_context, self.main_context)
        self._matcher.add_binding(
            QueryBinding(
                id="meteo-weather",
                query=Query({self.grips.weather_provider_name: "meteo"}),
                tap=self.meteo_weather_tap,
                base_score=5,
            )
        )
        self._matcher.add_binding(
            QueryBinding(
                id="mock-weather",
                query=Query({self.grips.weather_provider_name: "mock"}),
                tap=self.mock_weather_tap,
                base_score=5,
            )
        )

        self.header_context = self.main_context.create_child()
        self.header_location_tap = create_atom_value_tap(
            self.weather_grips.weather_location,
            initial="Sydney",
        )
        self.header_context.register_tap(self.header_location_tap)

        self.column_contexts: dict[str, GripContext] = {
            "A": self.main_context.create_child(),
            "B": self.main_context.create_child(),
        }
        self.location_taps = {
            "A": create_atom_value_tap(self.weather_grips.weather_location, initial="Sydney"),
            "B": create_atom_value_tap(self.weather_grips.weather_location, initial="Melbourne"),
        }
        self.column_contexts["A"].register_tap(self.location_taps["A"])
        self.column_contexts["B"].register_tap(self.location_taps["B"])

    def _read(self, grip: Any, *, ctx: GripContext | None = None) -> Any:
        return use_grip(self.grok, grip, ctx or self.main_context)

    def get_time(self) -> datetime:
        value = self._read(self.grips.current_time)
        return value if isinstance(value, datetime) else datetime.now().replace(microsecond=0)

    def get_page_size(self) -> int:
        return int(self._read(self.grips.page_size) or 0)

    def get_description(self) -> str:
        return str(self._read(self.grips.description) or "")

    def get_count(self) -> int:
        return int(self._read(self.grips.count) or 0)

    def increment_count(self) -> None:
        self.count_tap.update(lambda count: int(count or 0) + 1)

    def decrement_count(self) -> None:
        self.count_tap.update(lambda count: int(count or 0) - 1)

    def is_clock_visible(self) -> bool:
        return self.get_count() % 2 == 0

    def get_tab(self) -> TabName:
        tab = str(self._read(self.grips.current_tab) or "clock")
        return tab if tab in {"clock", "calc", "weather"} else "clock"

    def set_tab(self, tab: TabName) -> None:
        if tab not in {"clock", "calc", "weather"}:
            raise ValueError(f"unsupported tab: {tab}")
        self.tab_tap.set(tab)

    def get_calc_display(self) -> str:
        return str(self._read(self.grips.calc_display) or "0")

    def _invoke_calc(self, grip: Any, *args: Any) -> None:
        fn = self._read(grip)
        if callable(fn):
            fn(*args)

    def press_digit(self, digit: int) -> None:
        self._invoke_calc(self.grips.calc_digit_pressed, digit)

    def press_operator(self, op: str) -> None:
        mapping = {
            "+": self.grips.calc_add_pressed,
            "-": self.grips.calc_sub_pressed,
            "*": self.grips.calc_mul_pressed,
            "/": self.grips.calc_div_pressed,
        }
        grip = mapping.get(op)
        if grip is None:
            raise ValueError(f"unsupported operator: {op}")
        self._invoke_calc(grip)

    def press_equals(self) -> None:
        self._invoke_calc(self.grips.calc_equals_pressed)

    def press_clear(self) -> None:
        self._invoke_calc(self.grips.calc_clear_pressed)

    def get_weather_provider(self) -> ProviderName:
        provider = str(self._read(self.grips.weather_provider_name) or "meteo")
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
        return str(self._read(self.weather_grips.weather_location, ctx=context) or "")

    def set_weather_location(self, column: str, location: str) -> None:
        key = column.upper()
        if key not in self.location_taps:
            raise ValueError(f"unsupported column: {column}")
        self.location_taps[key].set(location)

    def get_header_temp(self) -> float | None:
        temp = self._read(self.weather_grips.weather_temp_c, ctx=self.header_context)
        return float(temp) if temp is not None else None

    def get_weather_snapshot(self, column: str) -> WeatherSnapshot:
        context = self._column_context(column)
        provider = self.get_weather_provider()
        return WeatherSnapshot(
            provider=provider,
            location_label=str(self._read(self.weather_grips.geo_label, ctx=context) or ""),
            temp_c=_to_float(self._read(self.weather_grips.weather_temp_c, ctx=context)),
            humidity_pct=_to_int(self._read(self.weather_grips.weather_humidity, ctx=context)),
            wind_speed_kph=_to_int(self._read(self.weather_grips.weather_wind_speed, ctx=context)),
            wind_dir=str(self._read(self.weather_grips.weather_wind_dir, ctx=context) or ""),
            rain_pct=_to_int(self._read(self.weather_grips.weather_rain_pct, ctx=context)),
            sunny_pct=_to_int(self._read(self.weather_grips.weather_sunny_pct, ctx=context)),
            uv_index=_to_float(self._read(self.weather_grips.weather_uv_index, ctx=context)),
        )

    def tick_clock(self, seconds: int = 1) -> None:
        self.clock_tap.tick(seconds)

    def tick_weather(self, step: int = 1) -> None:
        # Tick both taps; only the active one has destinations attached.
        self.meteo_weather_tap.tick(step)
        self.mock_weather_tap.tick(step)

    def tick(self) -> None:
        self.tick_clock(1)
        self.tick_weather(1)


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
