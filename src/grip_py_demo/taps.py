"""Tap implementations for grip-py-demo."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from grip_py import BaseTap, GripContext, MultiAtomValueTap

from .grips import DemoGrips, ProviderName, WeatherGrips


class ClockTap(BaseTap):
    """Simple clock tap advanced by the host application timer."""

    def __init__(self, grips: DemoGrips, *, initial_time: datetime | None = None):
        super().__init__(provides=(grips.current_time,))
        self._grips = grips
        self._current = (initial_time or datetime.now()).replace(microsecond=0)

    def set_time(self, value: datetime) -> None:
        self._current = value.replace(microsecond=0)
        self.produce()

    def tick(self, seconds: int = 1) -> None:
        self._current = self._current + timedelta(seconds=seconds)
        self.produce()

    def produce(self, *, dest_context: GripContext | None = None) -> None:
        self.publish({self._grips.current_time: self._current}, dest_context=dest_context)


class CalculatorTap(MultiAtomValueTap):
    """Calculator tap with display value and callable action grips."""

    _BINARY_OPS = {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b,
    }
    _UNARY_OPS = {
        ast.UAdd: lambda a: +a,
        ast.USub: lambda a: -a,
    }

    def __init__(self, grips: DemoGrips):
        self._grips = grips
        super().__init__(
            {
                grips.calc_display: grips.calc_display.default or "0",
                grips.calc_digit_pressed: self.press_digit,
                grips.calc_add_pressed: lambda: self.press_operator("+"),
                grips.calc_sub_pressed: lambda: self.press_operator("-"),
                grips.calc_mul_pressed: lambda: self.press_operator("*"),
                grips.calc_div_pressed: lambda: self.press_operator("/"),
                grips.calc_equals_pressed: self.press_equals,
                grips.calc_clear_pressed: self.press_clear,
            }
        )

    def _display(self) -> str:
        value = self.get(self._grips.calc_display)
        return str(value if value is not None else "0")

    def _set_display(self, value: str) -> None:
        self.set(self._grips.calc_display, value)

    def press_digit(self, digit: int) -> None:
        if digit < 0 or digit > 9:
            return
        display = self._display()
        next_display = str(digit) if display == "0" else f"{display}{digit}"
        self._set_display(next_display)

    def press_operator(self, op: str) -> None:
        if op not in {"+", "-", "*", "/"}:
            return
        self._set_display(f"{self._display()}{op}")

    def press_clear(self) -> None:
        self._set_display("0")

    def press_equals(self) -> None:
        expression = self._display()
        evaluated = self._safe_eval(expression)
        if evaluated is None:
            return
        self._set_display(_format_number(evaluated))

    @classmethod
    def _safe_eval(cls, expression: str) -> float | int | None:
        """Evaluate limited arithmetic grammar only."""
        try:
            node = ast.parse(expression, mode="eval")
            value = cls._eval_node(node)
        except Exception:
            return None
        return value

    @classmethod
    def _eval_node(cls, node: ast.AST) -> float | int:
        if isinstance(node, ast.Expression):
            return cls._eval_node(node.body)

        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("unsupported constant")

        if isinstance(node, ast.BinOp):
            op = cls._BINARY_OPS.get(type(node.op))
            if op is None:
                raise ValueError("unsupported operator")
            return op(cls._eval_node(node.left), cls._eval_node(node.right))

        if isinstance(node, ast.UnaryOp):
            op = cls._UNARY_OPS.get(type(node.op))
            if op is None:
                raise ValueError("unsupported unary operator")
            return op(cls._eval_node(node.operand))

        raise ValueError("unsupported syntax")


def _format_number(value: float | int) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return f"{value:g}"


@dataclass
class WeatherMetrics:
    temp_c: float
    humidity_pct: int
    wind_speed_kph: int
    wind_dir: str
    rain_pct: int
    sunny_pct: int
    uv_index: float


class FormulaWeatherTap(BaseTap):
    """Deterministic weather tap keyed by location and provider name."""

    def __init__(self, weather_grips: WeatherGrips, *, provider: ProviderName):
        super().__init__(
            provides=(
                weather_grips.weather_temp_c,
                weather_grips.weather_humidity,
                weather_grips.weather_wind_speed,
                weather_grips.weather_wind_dir,
                weather_grips.weather_rain_pct,
                weather_grips.weather_sunny_pct,
                weather_grips.weather_uv_index,
                weather_grips.geo_label,
            ),
            destination_param_grips=(weather_grips.weather_location,),
        )
        self._grips = weather_grips
        self._provider = provider
        self._tick = 0

    @property
    def provider(self) -> ProviderName:
        return self._provider

    def tick(self, step: int = 1) -> None:
        self._tick += step
        self.produce()

    def produce(self, *, dest_context: GripContext | None = None) -> None:
        if dest_context is not None:
            self.publish(self._updates_for_context(dest_context), dest_context=dest_context)
            return

        if self._producer is None:
            return

        for node in tuple(self._producer.get_destinations().keys()):
            context = node.get_context()
            if context is None:
                continue
            self.publish(self._updates_for_context(context), dest_context=context)

    def _updates_for_context(self, context: GripContext) -> dict[Any, Any]:
        location = self.get_destination_param_value(context, self._grips.weather_location)
        location_text = str(location or "Unknown")
        metrics = compute_weather_metrics(location_text, provider=self._provider, tick=self._tick)
        return {
            self._grips.weather_temp_c: metrics.temp_c,
            self._grips.weather_humidity: metrics.humidity_pct,
            self._grips.weather_wind_speed: metrics.wind_speed_kph,
            self._grips.weather_wind_dir: metrics.wind_dir,
            self._grips.weather_rain_pct: metrics.rain_pct,
            self._grips.weather_sunny_pct: metrics.sunny_pct,
            self._grips.weather_uv_index: metrics.uv_index,
            self._grips.geo_label: location_text,
        }


def compute_weather_metrics(location: str, *, provider: ProviderName, tick: int) -> WeatherMetrics:
    """Generate deterministic weather values for a location/provider pair."""
    seed = _seed_from_location(location)
    phase = (tick + seed) % 24

    if provider == "meteo":
        temp_c = 11 + (seed % 13) + (phase % 6)
        humidity_pct = 38 + ((seed * 3 + phase * 7) % 57)
        wind_speed_kph = 6 + ((seed + phase * 2) % 30)
        rain_pct = (seed * 5 + phase * 11) % 100
    else:
        temp_c = 18 + (seed % 8) + ((phase // 2) % 4)
        humidity_pct = 45 + ((seed * 2 + phase * 5) % 45)
        wind_speed_kph = 4 + ((seed + phase * 3) % 20)
        rain_pct = (seed * 7 + phase * 13 + 25) % 100

    sunny_pct = max(0, 100 - rain_pct)
    uv_index = round(((seed % 7) + (sunny_pct / 25.0)), 1)
    directions = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    wind_dir = directions[(seed + phase) % len(directions)]

    return WeatherMetrics(
        temp_c=round(float(temp_c), 1),
        humidity_pct=int(humidity_pct),
        wind_speed_kph=int(wind_speed_kph),
        wind_dir=wind_dir,
        rain_pct=int(rain_pct),
        sunny_pct=int(sunny_pct),
        uv_index=uv_index,
    )


def _seed_from_location(location: str) -> int:
    text = location.strip().lower()
    if not text:
        return 1
    return sum((idx + 1) * ord(ch) for idx, ch in enumerate(text)) % 997
