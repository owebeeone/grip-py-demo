import time

from grip_py_demo.demo_runtime import DemoRuntime
from grip_py_demo.grips import CoinGrips, DemoGrips, REGISTRY, WeatherGrips


def _wait_until(predicate, timeout_s: float = 1.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition not satisfied before timeout")


def test_grip_catalog_uses_upper_case_constant_names() -> None:
    assert hasattr(DemoGrips, "COUNT")
    assert not hasattr(DemoGrips, "count")
    assert hasattr(DemoGrips, "CURRENT_TIME")
    assert not hasattr(DemoGrips, "current_time")

    assert hasattr(WeatherGrips, "WEATHER_TEMP_C")
    assert not hasattr(WeatherGrips, "weather_temp_c")
    assert hasattr(WeatherGrips, "GEO_LABEL")
    assert not hasattr(WeatherGrips, "geo_label")
    assert hasattr(CoinGrips, "COIN_PRICE_USD")
    assert not hasattr(CoinGrips, "coin_price_usd")


def test_grip_catalog_is_class_level_constants() -> None:
    runtime = DemoRuntime()

    assert runtime.registry is REGISTRY
    assert runtime.grips is DemoGrips
    assert runtime.weather_grips is WeatherGrips
    assert runtime.coin_grips is CoinGrips


def test_clock_visibility_follows_counter_parity() -> None:
    runtime = DemoRuntime()

    assert runtime.get_tab() == "clock"
    assert runtime.get_count() == 1
    assert runtime.is_clock_visible() is False

    runtime.increment_count()
    assert runtime.get_count() == 2
    assert runtime.is_clock_visible() is True

    runtime.decrement_count()
    assert runtime.get_count() == 1
    assert runtime.is_clock_visible() is False


def test_calculator_supports_success_failure_and_clear() -> None:
    runtime = DemoRuntime()

    runtime.set_tab("calc")
    runtime.press_digit(1)
    runtime.press_operator("+")
    runtime.press_digit(2)
    runtime.press_equals()
    assert runtime.get_calc_display() == "3"

    runtime.press_clear()
    assert runtime.get_calc_display() == "0"

    runtime.press_digit(1)
    runtime.press_operator("/")
    runtime.press_digit(0)
    runtime.press_equals()
    assert runtime.get_calc_display() == "1/0"


def test_weather_provider_switch_and_location_updates() -> None:
    runtime = DemoRuntime()

    assert runtime.get_weather_provider() == "meteo"
    initial_a = runtime.get_weather_snapshot("A")
    initial_b = runtime.get_weather_snapshot("B")
    assert initial_a.location_label != ""
    assert initial_b.location_label != ""
    assert initial_a.location_label != initial_b.location_label

    runtime.set_weather_provider("mock")
    _wait_until(
        lambda: (
            runtime.tick_weather() is None
            and runtime.get_weather_snapshot("A").provider == "mock"
        )
    )
    mock_a = runtime.get_weather_snapshot("A")
    assert mock_a.provider == "mock"
    assert mock_a.location_label == initial_a.location_label

    runtime.set_weather_location("A", "Nowhere")
    _wait_until(
        lambda: (
            runtime.tick_weather() is None
            and runtime.get_weather_snapshot("A").location_label == "Nowhere"
        )
    )
    updated_a = runtime.get_weather_snapshot("A")
    assert updated_a.location_label == "Nowhere"
    assert updated_a.temp_c is not None


def test_default_meteo_provider_uses_real_taps_with_http_stubs(monkeypatch) -> None:
    from grip_py_demo import openmeteo_taps

    async def fake_geocode(_location: str, *, timeout_s: float = 5.0):
        _ = timeout_s
        return {
            "results": [
                {
                    "latitude": -33.86,
                    "longitude": 151.20,
                    "name": "Sydney",
                }
            ]
        }

    async def fake_weather(_lat: float, _lng: float, *, timeout_s: float = 7.0):
        _ = timeout_s
        return {
            "current_weather": {
                "time": "2026-03-09T05:00",
                "temperature": 24.7,
                "windspeed": 13.2,
                "winddirection": 92,
            },
            "hourly": {
                "time": ["2026-03-09T04:00", "2026-03-09T05:00"],
                "relativehumidity_2m": [70, 68],
                "precipitation_probability": [20, 40],
                "cloudcover": [30, 60],
                "uv_index": [2.1, 5.4],
            },
        }

    monkeypatch.setattr(openmeteo_taps, "fetch_geocode_json_async", fake_geocode)
    monkeypatch.setattr(openmeteo_taps, "fetch_weather_json_async", fake_weather)

    runtime = DemoRuntime()
    deadline = time.time() + 1.0
    snapshot_a = runtime.get_weather_snapshot("A")
    while snapshot_a.temp_c is None and time.time() < deadline:
        runtime.tick_weather()
        time.sleep(0.01)
        snapshot_a = runtime.get_weather_snapshot("A")

    assert runtime.get_weather_provider() == "meteo"
    assert snapshot_a.location_label == "Sydney"
    assert snapshot_a.temp_c == 24.7
    assert snapshot_a.wind_dir == "E"
    assert snapshot_a.rain_pct == 40


def test_read_uses_cached_drip_without_requery(monkeypatch) -> None:
    runtime = DemoRuntime()
    cached = runtime.get_or_create_drip(runtime.grips.COUNT)

    def fail_query(_self, *_args, **_kwargs):
        raise AssertionError("grok.query should not be called for cached reads")

    monkeypatch.setattr(type(runtime.grok), "query", fail_query)
    assert runtime._read(runtime.grips.COUNT) == cached.get()


def test_meteo_reads_do_not_block_on_slow_network(monkeypatch) -> None:
    from grip_py_demo import openmeteo_taps

    async def slow_geocode(_location: str, *, timeout_s: float = 5.0):
        _ = timeout_s
        time.sleep(0.2)
        return {
            "results": [
                {
                    "latitude": -33.86,
                    "longitude": 151.20,
                    "name": "Sydney",
                }
            ]
        }

    async def slow_weather(_lat: float, _lng: float, *, timeout_s: float = 7.0):
        _ = timeout_s
        time.sleep(0.2)
        return {
            "current_weather": {
                "time": "2026-03-09T05:00",
                "temperature": 21.2,
                "windspeed": 13.2,
                "winddirection": 92,
            },
            "hourly": {
                "time": ["2026-03-09T04:00", "2026-03-09T05:00"],
                "relativehumidity_2m": [70, 68],
                "precipitation_probability": [20, 40],
                "cloudcover": [30, 60],
                "uv_index": [2.1, 5.4],
            },
        }

    monkeypatch.setattr(openmeteo_taps, "fetch_geocode_json_async", slow_geocode)
    monkeypatch.setattr(openmeteo_taps, "fetch_weather_json_async", slow_weather)

    runtime = DemoRuntime()
    start = time.perf_counter()
    snapshot = runtime.get_weather_snapshot("A")
    elapsed = time.perf_counter() - start
    assert elapsed < 0.1
    assert snapshot.location_label in {"Sydney", ""}


def test_coin_stream_contexts_are_independent_and_provider_selectable(monkeypatch) -> None:
    import asyncio

    from grip_py import create_async_stream_multi_tap
    from grip_py_demo import demo_runtime as demo_runtime_module

    class FakeBinanceFactory:
        def __init__(self, grips: type[CoinGrips]) -> None:
            self._grips = grips
            self.provides = (
                grips.COIN_PRICE_USD,
                grips.COIN_VOLUME,
                grips.COIN_EXCHANGE,
                grips.COIN_STATUS,
                grips.COIN_UPDATED_AT,
            )

        def build(self):
            async def stream(_params, _cancel_event):
                yield {
                    self._grips.COIN_PRICE_USD: 123.45,
                    self._grips.COIN_VOLUME: 6.7,
                    self._grips.COIN_EXCHANGE: "Binance",
                    self._grips.COIN_STATUS: "streaming",
                    self._grips.COIN_UPDATED_AT: None,
                }
                await asyncio.sleep(0)

            return create_async_stream_multi_tap(
                provides=self.provides,
                destination_param_grips=(self._grips.COIN_PRODUCT,),
                request_key_of=lambda params: str(params.destination_params[self._grips.COIN_PRODUCT]),
                subscribe=stream,
                map_event=lambda _params, event: event,
                cleanup_delay_ms=0,
            )

    monkeypatch.setattr(demo_runtime_module, "BinanceCoinTapFactory", FakeBinanceFactory)
    runtime = DemoRuntime()

    runtime.set_tab("coins")
    assert runtime.get_tab() == "coins"

    initial_a = runtime.get_coin_snapshot("A")
    initial_b = runtime.get_coin_snapshot("B")
    assert initial_a.product == "BTC-USD"
    assert initial_b.product == "ETH-USD"
    assert initial_a.source == "mock"
    assert initial_b.source == "mock"

    _wait_until(
        lambda: (
            runtime.tick_coins() is None
            and runtime.get_coin_snapshot("A").price_usd is not None
            and runtime.get_coin_snapshot("B").price_usd is not None
        )
    )

    runtime.set_coin_product("A", "SOL-USD")
    runtime.tick_coins()
    assert runtime.get_coin_snapshot("A").product == "SOL-USD"
    assert runtime.get_coin_snapshot("B").product == "ETH-USD"

    runtime.set_coin_source("B", "binance")
    _wait_until(
        lambda: (
            runtime.tick_coins() is None
            and runtime.get_coin_snapshot("B").exchange == "Binance"
        )
    )
    binance_b = runtime.get_coin_snapshot("B")
    assert binance_b.source == "binance"
    assert binance_b.exchange == "Binance"
    assert binance_b.status == "streaming"
