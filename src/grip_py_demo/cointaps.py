"""Coin stream taps for grip-py-demo."""

from __future__ import annotations

import asyncio
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
        on_error=lambda error, request_key: print(
            f"[{exchange}] stream error for {request_key}: {error}"
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
