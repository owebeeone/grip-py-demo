"""Runtime orchestration and test-friendly interface for grip-py-demo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from grip_py import (
    Drip,
    GripContext,
    Grok,
    MatchingContext,
    QueryBinding,
    TapMatcher,
    create_atom_value_tap,
    with_one_of,
)

from .constants import LOCATION_OPTIONS
from .cointaps import (
    BinanceCoinTapFactory,
    COIN_PRODUCTS,
    COIN_SOURCES,
    CoinbaseCoinTapFactory,
    MockCoinTapFactory,
)
from .grips import CoinGrips, CoinSource, DemoGrips, ProviderName, REGISTRY, TabName, WeatherGrips
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


@dataclass(frozen=True, slots=True)
class CoinSnapshot:
    source: CoinSource
    product: str
    price_usd: float | None
    volume: float | None
    exchange: str
    status: str
    updated_at: datetime | None


class DemoRuntime:
    """High-level API around grip-py runtime used by tests and UI."""

    location_options = LOCATION_OPTIONS

    def __init__(self, *, initial_time: datetime | None = None) -> None:
        self.registry = REGISTRY
        self.grips = DemoGrips
        self.weather_grips = WeatherGrips
        self.coin_grips = CoinGrips
        self.grok = Grok(self.registry)
        self._drips: dict[tuple[str, str], Drip[Any]] = {}

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

        self.header_context = self.main_context.create_child()
        self.header_location_tap = create_atom_value_tap(
            self.weather_grips.WEATHER_LOCATION,
            initial="Sydney",
        )
        self.header_context.register_tap(self.header_location_tap)

        self.column_contexts: dict[str, GripContext] = {
            "A": self.main_context.create_child(),
            "B": self.main_context.create_child(),
        }
        self.location_taps = {
            "A": create_atom_value_tap(self.weather_grips.WEATHER_LOCATION, initial="Sydney"),
            "B": create_atom_value_tap(self.weather_grips.WEATHER_LOCATION, initial="Melbourne"),
        }
        self.column_contexts["A"].register_tap(self.location_taps["A"])
        self.column_contexts["B"].register_tap(self.location_taps["B"])

        self.coin_products = COIN_PRODUCTS
        self.coin_sources = COIN_SOURCES
        self.coin_contexts: dict[str, MatchingContext] = {}
        self.coin_source_taps = {}
        self.coin_product_taps = {}
        self._configure_coin_context("A", initial_product="BTC-USD")
        self._configure_coin_context("B", initial_product="ETH-USD")

    def _configure_coin_context(self, column: str, *, initial_product: str) -> None:
        def init(ctx: MatchingContext) -> None:
            ctx.add_binding(
                QueryBinding(
                    id=f"coin-{column}-mock",
                    query=with_one_of(self.coin_grips.COIN_SOURCE, "mock").build(),
                    tap=MockCoinTapFactory(self.coin_grips),
                    base_score=5,
                )
            )
            ctx.add_binding(
                QueryBinding(
                    id=f"coin-{column}-coinbase",
                    query=with_one_of(self.coin_grips.COIN_SOURCE, "coinbase").build(),
                    tap=CoinbaseCoinTapFactory(self.coin_grips),
                    base_score=5,
                )
            )
            ctx.add_binding(
                QueryBinding(
                    id=f"coin-{column}-binance",
                    query=with_one_of(self.coin_grips.COIN_SOURCE, "binance").build(),
                    tap=BinanceCoinTapFactory(self.coin_grips),
                    base_score=5,
                )
            )

        ctx = self.main_context.get_or_create_matching_context(f"coin:{column}", init=init)
        home = ctx.get_grip_home_context()
        source_tap = create_atom_value_tap(self.coin_grips.COIN_SOURCE, initial="mock")
        product_tap = create_atom_value_tap(self.coin_grips.COIN_PRODUCT, initial=initial_product)
        home.register_tap(source_tap)
        home.register_tap(product_tap)
        self.coin_contexts[column] = ctx
        self.coin_source_taps[column] = source_tap
        self.coin_product_taps[column] = product_tap

    def _read(self, grip: Any, *, ctx: GripContext | None = None) -> Any:
        return self.get_or_create_drip(grip, ctx=ctx).get()

    def get_or_create_drip(self, grip: Any, *, ctx: Any | None = None) -> Drip[Any]:
        context_like = ctx or self.main_context
        context = (
            context_like.get_grip_consumer_context()
            if hasattr(context_like, "get_grip_consumer_context")
            else context_like
        )
        key = (context.id, grip.key)
        existing = self._drips.get(key)
        if existing is not None:
            return existing
        created = self.grok.query(grip, context_like)
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
        return tab if tab in {"clock", "calc", "weather", "coins"} else "clock"

    def set_tab(self, tab: TabName) -> None:
        if tab not in {"clock", "calc", "weather", "coins"}:
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

    def _coin_context(self, column: str) -> MatchingContext:
        key = column.upper()
        if key not in self.coin_contexts:
            raise ValueError(f"unsupported coin column: {column}")
        return self.coin_contexts[key]

    def get_coin_source(self, column: str) -> CoinSource:
        context = self._coin_context(column)
        source = str(self._read(self.coin_grips.COIN_SOURCE, ctx=context) or "mock")
        return source if source in {"mock", "coinbase", "binance"} else "mock"

    def set_coin_source(self, column: str, source: CoinSource) -> None:
        key = column.upper()
        if source not in {"mock", "coinbase", "binance"}:
            raise ValueError(f"unsupported coin source: {source}")
        if key not in self.coin_source_taps:
            raise ValueError(f"unsupported coin column: {column}")
        self.coin_source_taps[key].set(source)

    def get_coin_product(self, column: str) -> str:
        context = self._coin_context(column)
        return str(self._read(self.coin_grips.COIN_PRODUCT, ctx=context) or "")

    def set_coin_product(self, column: str, product: str) -> None:
        key = column.upper()
        if product not in self.coin_products:
            raise ValueError(f"unsupported coin product: {product}")
        if key not in self.coin_product_taps:
            raise ValueError(f"unsupported coin column: {column}")
        self.coin_product_taps[key].set(product)

    def get_coin_snapshot(self, column: str) -> CoinSnapshot:
        context = self._coin_context(column)
        return CoinSnapshot(
            source=self.get_coin_source(column),
            product=self.get_coin_product(column),
            price_usd=_to_float(self._read(self.coin_grips.COIN_PRICE_USD, ctx=context)),
            volume=_to_float(self._read(self.coin_grips.COIN_VOLUME, ctx=context)),
            exchange=str(self._read(self.coin_grips.COIN_EXCHANGE, ctx=context) or ""),
            status=str(self._read(self.coin_grips.COIN_STATUS, ctx=context) or "idle"),
            updated_at=_to_datetime(self._read(self.coin_grips.COIN_UPDATED_AT, ctx=context)),
        )

    def tick_clock(self, seconds: int = 1) -> None:
        self.clock_tap.tick(seconds)

    def tick_weather(self, step: int = 1) -> None:
        # Poll asynchronous meteo taps and advance deterministic mock weather.
        self.location_to_geo_tap.produce()
        self.meteo_weather_tap.produce()
        self.mock_weather_tap.tick(step)

    def tick_coins(self) -> None:
        for column in self.coin_contexts:
            self.get_coin_snapshot(column)

    def tick(self) -> None:
        self.tick_clock(1)
        self.tick_weather(1)
        self.tick_coins()

    def close(self) -> None:
        """Release runtime graph resources and active stream tasks."""
        self.grok.close()


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _to_datetime(value: Any) -> datetime | None:
    return value if isinstance(value, datetime) else None
