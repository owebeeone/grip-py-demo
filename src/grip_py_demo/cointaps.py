"""Coin stream taps for grip-py-demo."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import time
from collections.abc import AsyncIterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from grip_py import (
    AsyncStreamRetryConfig,
    AsyncStreamTapParams,
    Grip,
    Tap,
    TapFactory,
    create_async_stream_multi_tap,
)

from .grips import CoinGrips

try:
    import websockets
except ImportError:  # pragma: no cover - exercised only in missing optional dep envs
    websockets = None

LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True, slots=True)
class CoinTick:
    price_usd: float | None
    volume: float | None
    exchange: str
    status: str
    updated_at: datetime | None


COIN_PRODUCTS = ("BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD")
COIN_SOURCES = ("mock", "coinbase", "binance")


def create_mock_coin_tap(grips: type[CoinGrips]) -> Tap:
    """Create deterministic local coin stream tap."""
    return _create_coin_stream_tap(
        grips,
        exchange="MockCoin",
        stream=lambda product, cancel_event: _mock_coin_stream(product, cancel_event),
        retry=None,
    )


def create_unavailable_coin_tap(grips: type[CoinGrips], *, exchange: str) -> Tap:
    """Create provider placeholder for demo providers without Python websocket deps."""
    return _create_coin_stream_tap(
        grips,
        exchange=exchange,
        stream=lambda product, cancel_event: _unavailable_stream(product, cancel_event, exchange),
        retry=None,
    )


def create_coinbase_coin_tap(grips: type[CoinGrips]) -> Tap:
    """Create Coinbase public ticker websocket tap."""
    return _create_coin_stream_tap(
        grips,
        exchange="Coinbase",
        stream=lambda product, cancel_event: _coinbase_stream(product, cancel_event),
        retry=AsyncStreamRetryConfig(initial_delay_ms=1000, max_delay_ms=30_000, jitter_ratio=0.5),
    )


def create_binance_coin_tap(grips: type[CoinGrips]) -> Tap:
    """Create Binance public ticker websocket tap."""
    return _create_coin_stream_tap(
        grips,
        exchange="Binance",
        stream=lambda product, cancel_event: _binance_stream(product, cancel_event),
        retry=AsyncStreamRetryConfig(initial_delay_ms=1000, max_delay_ms=30_000, jitter_ratio=0.5),
    )


def _create_coin_stream_tap(
    grips: type[CoinGrips],
    *,
    exchange: str,
    stream,
    retry: AsyncStreamRetryConfig | None,
) -> Tap:
    outputs: tuple[Grip[Any], ...] = (
        grips.COIN_PRICE_USD,
        grips.COIN_VOLUME,
        grips.COIN_EXCHANGE,
        grips.COIN_STATUS,
        grips.COIN_UPDATED_AT,
    )

    return create_async_stream_multi_tap(
        provides=outputs,
        destination_param_grips=(grips.COIN_PRODUCT,),
        request_key_of=lambda params: _product_from_params(params, grips),
        subscribe=lambda params, cancel_event: stream(_product_from_params(params, grips), cancel_event),
        map_event=lambda _params, event: _updates_for_tick(grips, event),
        get_reset_updates=lambda _params: _reset_updates(grips),
        cleanup_delay_ms=250,
        retry=retry,
        on_error=lambda error, request_key: LOGGER.warning(
            "%s stream error for %s: %s",
            exchange,
            request_key,
            error,
        ),
    )


async def _mock_coin_stream(
    product: str | None,
    cancel_event: asyncio.Event,
) -> AsyncIterable[CoinTick]:
    product_text = product or "BTC-USD"
    seed = _product_seed(product_text)
    base = _base_price(product_text)
    index = 0
    while not cancel_event.is_set():
        now = time.time()
        wave = math.sin((now / 0.9 + seed + index) / 7)
        drift = math.cos((now / 1.4 + seed) / 11)
        price = max(0.0001, base * (1 + wave * 0.006 + drift * 0.003))
        volume = 10 + ((seed + index * 17) % 90) + abs(wave) * 25
        yield CoinTick(
            price_usd=round(price, 6 if price < 1 else 2),
            volume=round(volume, 2),
            exchange="MockCoin",
            status="streaming",
            updated_at=datetime.now().replace(microsecond=0),
        )
        index += 1
        try:
            await asyncio.wait_for(cancel_event.wait(), timeout=0.9)
        except TimeoutError:
            pass


async def _unavailable_stream(
    _product: str | None,
    _cancel_event: asyncio.Event,
    exchange: str,
) -> AsyncIterable[CoinTick]:
    yield CoinTick(
        price_usd=None,
        volume=None,
        exchange=exchange,
        status="unavailable",
        updated_at=datetime.now().replace(microsecond=0),
    )


async def _coinbase_stream(
    product: str | None,
    cancel_event: asyncio.Event,
) -> AsyncIterable[CoinTick]:
    if websockets is None:
        raise RuntimeError("websockets package is required for Coinbase streams")

    product_id = (product or "BTC-USD").upper()
    url = "wss://ws-feed.exchange.coinbase.com"
    LOGGER.info("Coinbase stream connecting: product=%s url=%s", product_id, url)
    yield CoinTick(
        price_usd=None,
        volume=None,
        exchange="Coinbase",
        status="connecting",
        updated_at=datetime.now().replace(microsecond=0),
    )

    async with websockets.connect(url) as websocket:
        subscribe = {
            "type": "subscribe",
            "product_ids": [product_id],
            "channels": ["ticker"],
        }
        LOGGER.info("Coinbase stream subscribe: %s", subscribe)
        await websocket.send(json.dumps(subscribe))
        while not cancel_event.is_set():
            try:
                raw = await asyncio.wait_for(websocket.recv(), timeout=1.0)
            except TimeoutError:
                continue
            message = json.loads(raw)
            if message.get("type") != "ticker":
                LOGGER.debug("Coinbase ignored message: %s", message.get("type"))
                continue
            price = _to_float(message.get("price"))
            if price is None:
                LOGGER.warning("Coinbase ticker missing price: %s", message)
                continue
            volume = _to_float(message.get("last_size")) or _to_float(message.get("volume_24h"))
            LOGGER.debug("Coinbase ticker: product=%s price=%s volume=%s", product_id, price, volume)
            yield CoinTick(
                price_usd=price,
                volume=volume or 0,
                exchange="Coinbase",
                status="streaming",
                updated_at=_parse_coinbase_time(message.get("time")),
            )


async def _binance_stream(
    product: str | None,
    cancel_event: asyncio.Event,
) -> AsyncIterable[CoinTick]:
    if websockets is None:
        raise RuntimeError("websockets package is required for Binance streams")

    stream_name = f"{_binance_symbol(product or 'BTC-USD').lower()}@ticker"
    url = f"wss://stream.binance.com:9443/ws/{stream_name}"
    LOGGER.info("Binance stream connecting: product=%s url=%s", product, url)
    yield CoinTick(
        price_usd=None,
        volume=None,
        exchange="Binance",
        status="connecting",
        updated_at=datetime.now().replace(microsecond=0),
    )

    async with websockets.connect(url) as websocket:
        while not cancel_event.is_set():
            try:
                raw = await asyncio.wait_for(websocket.recv(), timeout=1.0)
            except TimeoutError:
                continue
            message = json.loads(raw)
            price = _to_float(message.get("c"))
            if price is None:
                LOGGER.warning("Binance ticker missing price: %s", message)
                continue
            volume = _to_float(message.get("v")) or 0
            LOGGER.debug("Binance ticker: stream=%s price=%s volume=%s", stream_name, price, volume)
            yield CoinTick(
                price_usd=price,
                volume=volume,
                exchange="Binance",
                status="streaming",
                updated_at=_datetime_from_epoch_ms(message.get("E")),
            )


def _product_from_params(params: AsyncStreamTapParams, grips: type[CoinGrips]) -> str | None:
    value = params.destination_params.get(grips.COIN_PRODUCT)
    return str(value).strip().upper() if value else None


def _updates_for_tick(grips: type[CoinGrips], tick: CoinTick) -> dict[Grip[Any], Any]:
    return {
        grips.COIN_PRICE_USD: tick.price_usd,
        grips.COIN_VOLUME: tick.volume,
        grips.COIN_EXCHANGE: tick.exchange,
        grips.COIN_STATUS: tick.status,
        grips.COIN_UPDATED_AT: tick.updated_at,
    }


def _reset_updates(grips: type[CoinGrips]) -> dict[Grip[Any], Any]:
    return {
        grips.COIN_PRICE_USD: None,
        grips.COIN_VOLUME: None,
        grips.COIN_EXCHANGE: "",
        grips.COIN_STATUS: "idle",
        grips.COIN_UPDATED_AT: None,
    }


def _product_seed(product: str) -> int:
    seed = 0
    for char in product:
        seed = ((seed * 31) + ord(char)) & 0xFFFFFFFF
    return seed or 1


def _base_price(product: str) -> float:
    upper = product.upper()
    if upper.startswith("BTC"):
        return 65000
    if upper.startswith("ETH"):
        return 3200
    if upper.startswith("SOL"):
        return 150
    if upper.startswith("DOGE"):
        return 0.16
    return 100


def _binance_symbol(product: str) -> str:
    compact = product.upper().replace("-", "").replace("_", "").replace("/", "")
    if compact.endswith("USD"):
        return f"{compact[:-3]}USDT"
    return compact


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_coinbase_time(value: Any) -> datetime:
    if not value:
        return datetime.now().replace(microsecond=0)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return datetime.now().replace(microsecond=0)


def _datetime_from_epoch_ms(value: Any) -> datetime:
    try:
        return datetime.fromtimestamp(float(value) / 1000).replace(microsecond=0)
    except (TypeError, ValueError):
        return datetime.now().replace(microsecond=0)


class MockCoinTapFactory:
    """Build mock coin stream taps for matcher-managed contexts."""

    provides: tuple[Grip[Any], ...]

    def __init__(self, grips: type[CoinGrips]) -> None:
        self._grips = grips
        self.provides = (
            grips.COIN_PRICE_USD,
            grips.COIN_VOLUME,
            grips.COIN_EXCHANGE,
            grips.COIN_STATUS,
            grips.COIN_UPDATED_AT,
        )

    def build(self) -> Tap:
        return create_mock_coin_tap(self._grips)


class UnavailableCoinTapFactory:
    """Build unavailable provider stream taps."""

    provides: tuple[Grip[Any], ...]

    def __init__(self, grips: type[CoinGrips], *, exchange: str) -> None:
        self._grips = grips
        self._exchange = exchange
        self.provides = (
            grips.COIN_PRICE_USD,
            grips.COIN_VOLUME,
            grips.COIN_EXCHANGE,
            grips.COIN_STATUS,
            grips.COIN_UPDATED_AT,
        )

    def build(self) -> Tap:
        return create_unavailable_coin_tap(self._grips, exchange=self._exchange)


class CoinbaseCoinTapFactory:
    """Build Coinbase stream taps."""

    provides: tuple[Grip[Any], ...]

    def __init__(self, grips: type[CoinGrips]) -> None:
        self._grips = grips
        self.provides = (
            grips.COIN_PRICE_USD,
            grips.COIN_VOLUME,
            grips.COIN_EXCHANGE,
            grips.COIN_STATUS,
            grips.COIN_UPDATED_AT,
        )

    def build(self) -> Tap:
        return create_coinbase_coin_tap(self._grips)


class BinanceCoinTapFactory:
    """Build Binance stream taps."""

    provides: tuple[Grip[Any], ...]

    def __init__(self, grips: type[CoinGrips]) -> None:
        self._grips = grips
        self.provides = (
            grips.COIN_PRICE_USD,
            grips.COIN_VOLUME,
            grips.COIN_EXCHANGE,
            grips.COIN_STATUS,
            grips.COIN_UPDATED_AT,
        )

    def build(self) -> Tap:
        return create_binance_coin_tap(self._grips)
