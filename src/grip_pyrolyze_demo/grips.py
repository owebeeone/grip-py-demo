"""Grip catalog definitions for the PySide6 demo."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Literal

from grip_py import Grip
from grip_pyrolyze import define_grip

TabName = Literal["clock", "calc", "weather"]
ProviderName = Literal["meteo", "mock"]


class DemoGrips:
    """Core demo grips defined once as class-level constants."""

    CURRENT_TIME: Grip[datetime] = define_grip(
        "CurrentTime",
        datetime.now().replace(microsecond=0),
    )
    PAGE_SIZE: Grip[int] = define_grip("PageSize", 50)
    DESCRIPTION: Grip[str] = define_grip(
        "Description",
        "PySide6 demo using grip-py with manual refresh",
    )
    COUNT: Grip[int] = define_grip("Count", 1)
    CALC_DISPLAY: Grip[str] = define_grip("CalcDisplay", "0")
    CURRENT_TAB: Grip[TabName] = define_grip("CurrentTab", "clock")
    WEATHER_PROVIDER_NAME: Grip[ProviderName] = define_grip(
        "WeatherProvider",
        "meteo",
    )
    CALC_DIGIT_PRESSED: Grip[Callable[[int], None] | None] = define_grip(
        "Calc.DigitPressed",
        value_type=object,
    )
    CALC_ADD_PRESSED: Grip[Callable[[], None] | None] = define_grip(
        "Calc.AddPressed",
        value_type=object,
    )
    CALC_SUB_PRESSED: Grip[Callable[[], None] | None] = define_grip(
        "Calc.SubPressed",
        value_type=object,
    )
    CALC_MUL_PRESSED: Grip[Callable[[], None] | None] = define_grip(
        "Calc.MulPressed",
        value_type=object,
    )
    CALC_DIV_PRESSED: Grip[Callable[[], None] | None] = define_grip(
        "Calc.DivPressed",
        value_type=object,
    )
    CALC_EQUALS_PRESSED: Grip[Callable[[], None] | None] = define_grip(
        "Calc.EqualsPressed",
        value_type=object,
    )
    CALC_CLEAR_PRESSED: Grip[Callable[[], None] | None] = define_grip(
        "Calc.ClearPressed",
        value_type=object,
    )


class WeatherGrips:
    """Weather grips defined once as class-level constants."""

    WEATHER_TEMP_C: Grip[float | None] = define_grip(
        "Weather.TempC",
        value_type=float,
    )
    WEATHER_HUMIDITY: Grip[int | None] = define_grip(
        "Weather.HumidityPct",
        value_type=int,
    )
    WEATHER_WIND_SPEED: Grip[int | None] = define_grip(
        "Weather.WindSpeedKph",
        value_type=int,
    )
    WEATHER_WIND_DIR: Grip[str] = define_grip("Weather.WindDir", "")
    WEATHER_RAIN_PCT: Grip[int | None] = define_grip(
        "Weather.RainPct",
        value_type=int,
    )
    WEATHER_SUNNY_PCT: Grip[int | None] = define_grip(
        "Weather.SunnyPct",
        value_type=int,
    )
    WEATHER_UV_INDEX: Grip[float | None] = define_grip(
        "Weather.UV",
        value_type=float,
    )
    WEATHER_LOCATION: Grip[str | None] = define_grip(
        "Weather.Location",
        value_type=str,
    )
    GEO_LAT: Grip[float | None] = define_grip(
        "Geo.Lat",
        value_type=float,
    )
    GEO_LNG: Grip[float | None] = define_grip(
        "Geo.Lng",
        value_type=float,
    )
    GEO_LABEL: Grip[str] = define_grip("Geo.Label", "")
