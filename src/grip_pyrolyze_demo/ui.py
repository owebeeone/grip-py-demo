#@pyrolyze
"""PyRolyze UI for the grip-py demo runtime."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QBoxLayout

from grip_pyrolyze.core import use_grip
from pyrolyze.api import keyed, pyrolyze
from pyrolyze.backends.pyside6.generated_library import PySide6UiLibrary as Qt

from .demo_runtime import DemoRuntime


def _fmt(value: object) -> str:
    return "-" if value is None else str(value)


@pyrolyze
def app_header(runtime: DemoRuntime) -> None:
    temp = use_grip(runtime.weather_grips.WEATHER_TEMP_C, runtime.header_context)
    with Qt.CQHBoxLayout(objectName="header:row"):
        Qt.CQLabel(
            "Grip PyRolyze Demo",
            objectName="header:title",
            styleSheet="font-weight: bold; font-size: 16px;",
        )
        Qt.CQLabel(
            f"Sydney temp {_fmt(temp)}°C",
            objectName="header:temp",
        )


@pyrolyze
def tab_bar(runtime: DemoRuntime) -> None:
    current_tab = use_grip(runtime.grips.CURRENT_TAB, runtime.main_context)
    with Qt.CQHBoxLayout(objectName="tabs:row"):
        Qt.CQPushButton(
            f"Clock{' *' if current_tab == 'clock' else ''}",
            objectName="tabs:clock",
            on_clicked=lambda: runtime.set_tab("clock"),
        )
        Qt.CQPushButton(
            f"Calculator{' *' if current_tab == 'calc' else ''}",
            objectName="tabs:calc",
            on_clicked=lambda: runtime.set_tab("calc"),
        )
        Qt.CQPushButton(
            f"Weather{' *' if current_tab == 'weather' else ''}",
            objectName="tabs:weather",
            on_clicked=lambda: runtime.set_tab("weather"),
        )


@pyrolyze
def clock_panel(runtime: DemoRuntime) -> None:
    current_time = use_grip(runtime.grips.CURRENT_TIME, runtime.main_context)
    page_size = use_grip(runtime.grips.PAGE_SIZE, runtime.main_context)
    description = use_grip(runtime.grips.DESCRIPTION, runtime.main_context)
    count = int(use_grip(runtime.grips.COUNT, runtime.main_context) or 0)

    with Qt.CQVBoxLayout(objectName="clock:panel"):
        if isinstance(current_time, datetime) and count % 2 == 0:
            Qt.CQLabel(
                f"Time: {current_time:%H:%M:%S}",
                objectName="clock:time",
            )
        else:
            Qt.CQLabel("Count is odd - no time", objectName="clock:hidden")
        Qt.CQLabel(f"Page size: {_fmt(page_size)}", objectName="clock:page_size")
        with Qt.CQHBoxLayout(objectName="clock:count_row"):
            Qt.CQPushButton("-", objectName="clock:decrement", on_clicked=runtime.decrement_count)
            Qt.CQLabel(f"Count: {count}", objectName="clock:count")
            Qt.CQPushButton("+", objectName="clock:increment", on_clicked=runtime.increment_count)
        Qt.CQLabel(f"Description: {_fmt(description)}", objectName="clock:description")


@pyrolyze
def calculator_panel(runtime: DemoRuntime) -> None:
    display = use_grip(runtime.grips.CALC_DISPLAY, runtime.main_context) or "0"
    with Qt.CQVBoxLayout(objectName="calc:panel"):
        Qt.CQLabel(
            str(display),
            objectName="calc:display",
            styleSheet="font-family: monospace; font-size: 20px; padding: 8px; border: 1px solid #ccc;",
        )
        rows = (
            (("7", lambda: runtime.press_digit(7)), ("8", lambda: runtime.press_digit(8)), ("9", lambda: runtime.press_digit(9)), ("/", lambda: runtime.press_operator("/"))),
            (("4", lambda: runtime.press_digit(4)), ("5", lambda: runtime.press_digit(5)), ("6", lambda: runtime.press_digit(6)), ("*", lambda: runtime.press_operator("*"))),
            (("1", lambda: runtime.press_digit(1)), ("2", lambda: runtime.press_digit(2)), ("3", lambda: runtime.press_digit(3)), ("-", lambda: runtime.press_operator("-"))),
            (("0", lambda: runtime.press_digit(0)), ("C", runtime.press_clear), ("=", runtime.press_equals), ("+", lambda: runtime.press_operator("+"))),
        )
        for row_index, row in keyed(enumerate(rows), key=lambda item: item[0]):
            _ = row_index
            with Qt.CQHBoxLayout(objectName=f"calc:row:{row_index}"):
                for label, callback in keyed(row, key=lambda item: item[0]):
                    Qt.CQPushButton(
                        label,
                        objectName=f"calc:button:{label}",
                        on_clicked=callback,
                    )


@pyrolyze
def weather_column(runtime: DemoRuntime, column: str, title: str) -> None:
    ctx = runtime.column_contexts[column]
    location = use_grip(runtime.weather_grips.WEATHER_LOCATION, ctx)
    geo_label = use_grip(runtime.weather_grips.GEO_LABEL, ctx)
    temp = use_grip(runtime.weather_grips.WEATHER_TEMP_C, ctx)
    humidity = use_grip(runtime.weather_grips.WEATHER_HUMIDITY, ctx)
    wind = use_grip(runtime.weather_grips.WEATHER_WIND_SPEED, ctx)
    wind_dir = use_grip(runtime.weather_grips.WEATHER_WIND_DIR, ctx)
    rain = use_grip(runtime.weather_grips.WEATHER_RAIN_PCT, ctx)
    sunny = use_grip(runtime.weather_grips.WEATHER_SUNNY_PCT, ctx)
    uv = use_grip(runtime.weather_grips.WEATHER_UV_INDEX, ctx)

    with Qt.CQGroupBox(title, objectName=f"weather:{column}:group"):
        with Qt.CQVBoxLayout(objectName=f"weather:{column}:layout"):
            Qt.CQLabel(f"Location: {_fmt(geo_label or location)}", objectName=f"weather:{column}:location")
            with Qt.CQHBoxLayout(objectName=f"weather:{column}:locations"):
                for option in keyed(runtime.location_options, key=lambda entry: entry):
                    Qt.CQPushButton(
                        option,
                        objectName=f"weather:{column}:location:{option}",
                        on_clicked=lambda checked=False, next_location=option: runtime.set_weather_location(column, next_location),
                    )
            Qt.CQLabel(f"Temp (°C): {_fmt(temp)}", objectName=f"weather:{column}:temp")
            Qt.CQLabel(f"Humidity (%): {_fmt(humidity)}", objectName=f"weather:{column}:humidity")
            Qt.CQLabel(f"Wind (kph): {_fmt(wind)}", objectName=f"weather:{column}:wind")
            Qt.CQLabel(f"Wind Dir: {_fmt(wind_dir)}", objectName=f"weather:{column}:wind_dir")
            Qt.CQLabel(f"Rain chance (%): {_fmt(rain)}", objectName=f"weather:{column}:rain")
            Qt.CQLabel(f"Sunny (%): {_fmt(sunny)}", objectName=f"weather:{column}:sunny")
            Qt.CQLabel(f"UV Index: {_fmt(uv)}", objectName=f"weather:{column}:uv")


@pyrolyze
def weather_panel(runtime: DemoRuntime) -> None:
    provider = use_grip(runtime.grips.WEATHER_PROVIDER_NAME, runtime.main_context) or "meteo"

    with Qt.CQVBoxLayout(objectName="weather:panel"):
        with Qt.CQHBoxLayout(objectName="weather:provider_row"):
            Qt.CQLabel(
                f"Current weather provider: {provider}",
                objectName="weather:provider:label",
            )
            Qt.CQPushButton(
                "Meteo",
                objectName="weather:provider:meteo",
                on_clicked=lambda: runtime.set_weather_provider("meteo"),
            )
            Qt.CQPushButton(
                "Mock",
                objectName="weather:provider:mock",
                on_clicked=lambda: runtime.set_weather_provider("mock"),
            )
        with Qt.CQHBoxLayout(objectName="weather:columns"):
            weather_column(runtime, "A", "Location A")
            weather_column(runtime, "B", "Location B")


@pyrolyze
def grip_pyrolyze_demo_app(runtime: DemoRuntime) -> None:
    current_tab = use_grip(runtime.grips.CURRENT_TAB, runtime.main_context) or "clock"

    with Qt.CQMainWindow(
        windowTitle="Grip PyRolyze Demo",
        minimumWidth=980,
        minimumHeight=680,
    ):
        with Qt.CQWidget(objectName="demo:central_widget"):
            with Qt.CQBoxLayout(QBoxLayout.Direction.TopToBottom):
                app_header(runtime)
                tab_bar(runtime)
                if current_tab == "clock":
                    clock_panel(runtime)
                elif current_tab == "calc":
                    calculator_panel(runtime)
                else:
                    weather_panel(runtime)
