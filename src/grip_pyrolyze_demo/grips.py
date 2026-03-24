"""Grip catalog definitions for the PySide6 demo."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Literal

from grip_py import Grip, GripRegistry

TabName = Literal["clock", "calc", "weather"]
ProviderName = Literal["meteo", "mock"]

REGISTRY = GripRegistry()


class DemoGrips:
    """Core demo grips defined once as class-level constants."""

    CURRENT_TIME: Grip[datetime] = REGISTRY.add(
        "CurrentTime",
        datetime.now().replace(microsecond=0),
    )
    PAGE_SIZE: Grip[int] = REGISTRY.add("PageSize", 50)
    DESCRIPTION: Grip[str] = REGISTRY.add(
        "Description",
        "PySide6 demo using grip-py with manual refresh",
    )
    COUNT: Grip[int] = REGISTRY.add("Count", 1)
    CALC_DISPLAY: Grip[str] = REGISTRY.add("CalcDisplay", "0")
    CURRENT_TAB: Grip[TabName] = REGISTRY.add("CurrentTab", "clock")
    WEATHER_PROVIDER_NAME: Grip[ProviderName] = REGISTRY.add(
        "WeatherProvider",
        "meteo",
    )
    CALC_DIGIT_PRESSED: Grip[Callable[[int], None] | None] = REGISTRY.add(
        "Calc.DigitPressed",
        value_type=object,
    )
    CALC_ADD_PRESSED: Grip[Callable[[], None] | None] = REGISTRY.add(
        "Calc.AddPressed",
        value_type=object,
    )
    CALC_SUB_PRESSED: Grip[Callable[[], None] | None] = REGISTRY.add(
        "Calc.SubPressed",
        value_type=object,
    )
    CALC_MUL_PRESSED: Grip[Callable[[], None] | None] = REGISTRY.add(
        "Calc.MulPressed",
        value_type=object,
    )
    CALC_DIV_PRESSED: Grip[Callable[[], None] | None] = REGISTRY.add(
        "Calc.DivPressed",
        value_type=object,
    )
    CALC_EQUALS_PRESSED: Grip[Callable[[], None] | None] = REGISTRY.add(
        "Calc.EqualsPressed",
        value_type=object,
    )
    CALC_CLEAR_PRESSED: Grip[Callable[[], None] | None] = REGISTRY.add(
        "Calc.ClearPressed",
        value_type=object,
    )


class WeatherGrips:
    """Weather grips defined once as class-level constants."""

    WEATHER_TEMP_C: Grip[float | None] = REGISTRY.add(
        "Weather.TempC",
        value_type=float,
    )
    WEATHER_HUMIDITY: Grip[int | None] = REGISTRY.add(
        "Weather.HumidityPct",
        value_type=int,
    )
    WEATHER_WIND_SPEED: Grip[int | None] = REGISTRY.add(
        "Weather.WindSpeedKph",
        value_type=int,
    )
    WEATHER_WIND_DIR: Grip[str] = REGISTRY.add("Weather.WindDir", "")
    WEATHER_RAIN_PCT: Grip[int | None] = REGISTRY.add(
        "Weather.RainPct",
        value_type=int,
    )
    WEATHER_SUNNY_PCT: Grip[int | None] = REGISTRY.add(
        "Weather.SunnyPct",
        value_type=int,
    )
    WEATHER_UV_INDEX: Grip[float | None] = REGISTRY.add(
        "Weather.UV",
        value_type=float,
    )
    WEATHER_LOCATION: Grip[str | None] = REGISTRY.add(
        "Weather.Location",
        value_type=str,
    )
    GEO_LAT: Grip[float | None] = REGISTRY.add(
        "Geo.Lat",
        value_type=float,
    )
    GEO_LNG: Grip[float | None] = REGISTRY.add(
        "Geo.Lng",
        value_type=float,
    )
    GEO_LABEL: Grip[str] = REGISTRY.add("Geo.Label", "")
