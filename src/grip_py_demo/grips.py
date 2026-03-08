"""Grip catalog definitions for the PySide6 demo."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from grip_py import Grip, GripRegistry

TabName = Literal["clock", "calc", "weather"]
ProviderName = Literal["meteo", "mock"]


@dataclass(frozen=True, slots=True)
class DemoGrips:
    current_time: Grip[datetime]
    page_size: Grip[int]
    description: Grip[str]
    count: Grip[int]
    calc_display: Grip[str]
    current_tab: Grip[TabName]
    weather_provider_name: Grip[ProviderName]
    calc_digit_pressed: Grip[Callable[[int], None] | None]
    calc_add_pressed: Grip[Callable[[], None] | None]
    calc_sub_pressed: Grip[Callable[[], None] | None]
    calc_mul_pressed: Grip[Callable[[], None] | None]
    calc_div_pressed: Grip[Callable[[], None] | None]
    calc_equals_pressed: Grip[Callable[[], None] | None]
    calc_clear_pressed: Grip[Callable[[], None] | None]


@dataclass(frozen=True, slots=True)
class WeatherGrips:
    weather_temp_c: Grip[float | None]
    weather_humidity: Grip[int | None]
    weather_wind_speed: Grip[int | None]
    weather_wind_dir: Grip[str]
    weather_rain_pct: Grip[int | None]
    weather_sunny_pct: Grip[int | None]
    weather_uv_index: Grip[float | None]
    weather_location: Grip[str | None]
    geo_label: Grip[str]


def define_demo_grips(registry: GripRegistry) -> DemoGrips:
    """Create non-weather grips in the target registry."""
    return DemoGrips(
        current_time=registry.add("CurrentTime", datetime.now().replace(microsecond=0)),
        page_size=registry.add("PageSize", 50),
        description=registry.add(
            "Description",
            "PySide6 demo using grip-py with manual refresh",
        ),
        count=registry.add("Count", 1),
        calc_display=registry.add("CalcDisplay", "0"),
        current_tab=registry.add("CurrentTab", "clock"),
        weather_provider_name=registry.add("WeatherProvider", "meteo"),
        calc_digit_pressed=registry.add("Calc.DigitPressed", value_type=object),
        calc_add_pressed=registry.add("Calc.AddPressed", value_type=object),
        calc_sub_pressed=registry.add("Calc.SubPressed", value_type=object),
        calc_mul_pressed=registry.add("Calc.MulPressed", value_type=object),
        calc_div_pressed=registry.add("Calc.DivPressed", value_type=object),
        calc_equals_pressed=registry.add("Calc.EqualsPressed", value_type=object),
        calc_clear_pressed=registry.add("Calc.ClearPressed", value_type=object),
    )


def define_weather_grips(registry: GripRegistry) -> WeatherGrips:
    """Create weather-related grips in the target registry."""
    return WeatherGrips(
        weather_temp_c=registry.add("Weather.TempC", value_type=float),
        weather_humidity=registry.add("Weather.HumidityPct", value_type=int),
        weather_wind_speed=registry.add("Weather.WindSpeedKph", value_type=int),
        weather_wind_dir=registry.add("Weather.WindDir", ""),
        weather_rain_pct=registry.add("Weather.RainPct", value_type=int),
        weather_sunny_pct=registry.add("Weather.SunnyPct", value_type=int),
        weather_uv_index=registry.add("Weather.UV", value_type=float),
        weather_location=registry.add("Weather.Location", value_type=str),
        geo_label=registry.add("Geo.Label", ""),
    )
