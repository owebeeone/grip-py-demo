"""Open-Meteo geocoding and weather taps for grip-py-demo."""

from __future__ import annotations

import asyncio
import queue
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx
from grip_py import BaseTap, GripContext

from .grips import WeatherGrips


async def fetch_geocode_json_async(location: str, *, timeout_s: float = 5.0) -> dict[str, Any]:
    """Fetch geocoding payload from Open-Meteo."""
    url = (
        "https://geocoding-api.open-meteo.com/v1/search"
        f"?name={quote(location)}&count=1&language=en&format=json"
    )
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def fetch_weather_json_async(lat: float, lng: float, *, timeout_s: float = 7.0) -> dict[str, Any]:
    """Fetch weather payload from Open-Meteo."""
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lng}"
        "&current_weather=true"
        "&hourly=relativehumidity_2m,precipitation_probability,cloudcover,uv_index"
    )
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


def parse_geocode_payload(
    payload: dict[str, Any],
    *,
    fallback_label: str,
) -> tuple[float | None, float | None, str]:
    """Map Open-Meteo geocode response into grip values."""
    results = payload.get("results") or []
    if not results:
        return None, None, fallback_label

    first = results[0] or {}
    lat = first.get("latitude")
    lng = first.get("longitude")
    label = str(first.get("name") or fallback_label)

    return _to_float(lat), _to_float(lng), label


def parse_weather_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Map Open-Meteo weather response into weather grip fields."""
    current = payload.get("current_weather") or {}
    hourly = payload.get("hourly") or {}

    times = list(hourly.get("time") or [])
    current_iso = str(current.get("time") or "")
    hour_ix = nearest_hour_index(times, current_iso)

    humidity_values = list(hourly.get("relativehumidity_2m") or [])
    rain_values = list(hourly.get("precipitation_probability") or [])
    cloud_values = list(hourly.get("cloudcover") or [])
    uv_values = list(hourly.get("uv_index") or [])

    humidity = _value_at(humidity_values, hour_ix)
    rain = _value_at(rain_values, hour_ix)
    cloud = _value_at(cloud_values, hour_ix)
    uv = _value_at(uv_values, hour_ix)

    rain_pct = _to_int(rain)
    sunny_pct = None if cloud is None else max(0, 100 - _to_int(cloud))

    return {
        "temp_c": _to_float(current.get("temperature")),
        "humidity_pct": _to_int(humidity),
        "wind_speed_kph": _to_float(current.get("windspeed")),
        "wind_dir": to_compass(_to_float(current.get("winddirection"))),
        "rain_pct": rain_pct,
        "sunny_pct": sunny_pct,
        "uv_index": _to_float(uv),
    }


def to_compass(degrees: float | None) -> str:
    """Convert wind direction degrees to 16-point compass text."""
    if degrees is None:
        return ""
    directions = (
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    )
    index = int(round((degrees % 360) / 22.5)) % 16
    return directions[index]


def nearest_hour_index(hourly_times: list[str], current_iso: str) -> int:
    """Pick nearest hourly index for the provided current timestamp."""
    if not hourly_times:
        return 0

    try:
        exact_ix = hourly_times.index(current_iso)
        return exact_ix
    except ValueError:
        pass

    try:
        current_key = _iso_to_epoch_minutes(current_iso)
    except ValueError:
        return 0

    best_ix = 0
    best_delta = 10**18
    for index, iso in enumerate(hourly_times):
        try:
            value = _iso_to_epoch_minutes(iso)
        except ValueError:
            continue
        delta = abs(value - current_key)
        if delta < best_delta:
            best_delta = delta
            best_ix = index
    return best_ix


def _iso_to_epoch_minutes(value: str) -> int:
    from datetime import datetime

    dt = datetime.fromisoformat(value)
    return int(dt.timestamp() // 60)


def _value_at(values: list[Any], index: int) -> Any:
    if index < 0 or index >= len(values):
        return None
    return values[index]


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return 0


@dataclass(slots=True)
class _CacheEntry:
    value: dict[str, Any]
    expires_at: float


class _AsyncWorker:
    """Single background asyncio loop for non-blocking network fetches."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="grip-py-demo-asyncio",
            daemon=True,
        )
        self._thread.start()
        self._ready.wait(timeout=2.0)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        self._loop.run_forever()

    def submit(self, coroutine):
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop)


_ASYNC_WORKER = _AsyncWorker()


class LocationToGeoTap(BaseTap):
    """Resolve `Weather.Location` into geo coordinates + display label."""

    def __init__(self, weather_grips: type[WeatherGrips], *, cache_ttl_s: int = 30 * 60):
        super().__init__(
            provides=(
                weather_grips.GEO_LAT,
                weather_grips.GEO_LNG,
                weather_grips.GEO_LABEL,
            ),
            destination_param_grips=(weather_grips.WEATHER_LOCATION,),
        )
        self._grips = weather_grips
        self._cache_ttl_s = cache_ttl_s
        self._cache: dict[str, _CacheEntry] = {}
        self._worker = _ASYNC_WORKER
        self._inflight: dict[str, Future[tuple[float | None, float | None, str]]] = {}
        self._completed: queue.SimpleQueue[tuple[str, float | None, float | None, str]] = (
            queue.SimpleQueue()
        )

    def on_detach(self) -> None:
        for future in tuple(self._inflight.values()):
            future.cancel()
        self._inflight.clear()
        super().on_detach()

    def produce(self, *, dest_context: GripContext | None = None) -> None:
        self._drain_completed_fetches()
        if dest_context is not None:
            self.publish(self._updates_for(dest_context), dest_context=dest_context)
            return

        if self._producer is None:
            return
        for node in tuple(self._producer.get_destinations().keys()):
            ctx = node.get_context()
            if ctx is None:
                continue
            self.publish(self._updates_for(ctx), dest_context=ctx)

    def _updates_for(self, context: GripContext) -> dict[Any, Any]:
        location = str(
            self.get_destination_param_value(context, self._grips.WEATHER_LOCATION) or ""
        ).strip()
        if not location:
            return {
                self._grips.GEO_LAT: None,
                self._grips.GEO_LNG: None,
                self._grips.GEO_LABEL: "",
            }

        key = location.lower()
        now = time.time()
        cached = self._cache.get(key)
        if cached is not None and cached.expires_at > now:
            data = cached.value
            return {
                self._grips.GEO_LAT: data["lat"],
                self._grips.GEO_LNG: data["lng"],
                self._grips.GEO_LABEL: data["label"],
            }

        if key not in self._inflight:
            self._start_fetch(key, location)
            if cached is not None:
                stale = cached.value
                return {
                    self._grips.GEO_LAT: stale["lat"],
                    self._grips.GEO_LNG: stale["lng"],
                    self._grips.GEO_LABEL: stale["label"],
                }

        return {
            self._grips.GEO_LAT: None,
            self._grips.GEO_LNG: None,
            self._grips.GEO_LABEL: location,
        }

    def _start_fetch(self, key: str, location: str) -> None:
        future = self._worker.submit(self._fetch_and_parse_geocode(location))
        self._inflight[key] = future

        def on_done(done: Future[tuple[float | None, float | None, str]]) -> None:
            try:
                lat, lng, label = done.result()
            except Exception:
                lat, lng, label = None, None, location
            self._completed.put((key, lat, lng, label))

        future.add_done_callback(on_done)

    async def _fetch_and_parse_geocode(self, location: str) -> tuple[float | None, float | None, str]:
        payload = await fetch_geocode_json_async(location)
        return parse_geocode_payload(payload, fallback_label=location)

    def _drain_completed_fetches(self) -> None:
        now = time.time()
        while True:
            try:
                key, lat, lng, label = self._completed.get_nowait()
            except queue.Empty:
                break
            self._inflight.pop(key, None)
            self._cache[key] = _CacheEntry(
                value={"lat": lat, "lng": lng, "label": label},
                expires_at=now + self._cache_ttl_s,
            )


class OpenMeteoWeatherTap(BaseTap):
    """Fetch live weather using destination geo coordinates."""

    def __init__(self, weather_grips: type[WeatherGrips], *, cache_ttl_s: int = 10 * 60):
        super().__init__(
            provides=(
                weather_grips.WEATHER_TEMP_C,
                weather_grips.WEATHER_HUMIDITY,
                weather_grips.WEATHER_WIND_SPEED,
                weather_grips.WEATHER_WIND_DIR,
                weather_grips.WEATHER_RAIN_PCT,
                weather_grips.WEATHER_SUNNY_PCT,
                weather_grips.WEATHER_UV_INDEX,
            ),
            destination_param_grips=(weather_grips.GEO_LAT, weather_grips.GEO_LNG),
        )
        self._grips = weather_grips
        self._cache_ttl_s = cache_ttl_s
        self._cache: dict[str, _CacheEntry] = {}
        self._worker = _ASYNC_WORKER
        self._inflight: dict[str, Future[dict[str, Any]]] = {}
        self._completed: queue.SimpleQueue[tuple[str, dict[str, Any]]] = queue.SimpleQueue()

    def on_detach(self) -> None:
        for future in tuple(self._inflight.values()):
            future.cancel()
        self._inflight.clear()
        super().on_detach()

    def produce(self, *, dest_context: GripContext | None = None) -> None:
        self._drain_completed_fetches()
        if dest_context is not None:
            self.publish(self._updates_for(dest_context), dest_context=dest_context)
            return

        if self._producer is None:
            return
        for node in tuple(self._producer.get_destinations().keys()):
            ctx = node.get_context()
            if ctx is None:
                continue
            self.publish(self._updates_for(ctx), dest_context=ctx)

    def _updates_for(self, context: GripContext) -> dict[Any, Any]:
        lat = _to_float(self.get_destination_param_value(context, self._grips.GEO_LAT))
        lng = _to_float(self.get_destination_param_value(context, self._grips.GEO_LNG))
        if lat is None or lng is None:
            return _weather_defaults(self._grips)

        key = f"{lat:.4f}:{lng:.4f}"
        now = time.time()
        cached = self._cache.get(key)
        if cached is not None and cached.expires_at > now:
            mapped = cached.value
        else:
            if key not in self._inflight:
                self._start_fetch(key, lat, lng)
            mapped = cached.value if cached is not None else _weather_payload_defaults()

        return {
            self._grips.WEATHER_TEMP_C: mapped.get("temp_c"),
            self._grips.WEATHER_HUMIDITY: mapped.get("humidity_pct"),
            self._grips.WEATHER_WIND_SPEED: mapped.get("wind_speed_kph"),
            self._grips.WEATHER_WIND_DIR: str(mapped.get("wind_dir") or ""),
            self._grips.WEATHER_RAIN_PCT: mapped.get("rain_pct"),
            self._grips.WEATHER_SUNNY_PCT: mapped.get("sunny_pct"),
            self._grips.WEATHER_UV_INDEX: mapped.get("uv_index"),
        }

    def _start_fetch(self, key: str, lat: float, lng: float) -> None:
        future = self._worker.submit(self._fetch_and_parse_weather(lat, lng))
        self._inflight[key] = future

        def on_done(done: Future[dict[str, Any]]) -> None:
            try:
                mapped = done.result()
            except Exception:
                mapped = _weather_payload_defaults()
            self._completed.put((key, mapped))

        future.add_done_callback(on_done)

    async def _fetch_and_parse_weather(self, lat: float, lng: float) -> dict[str, Any]:
        payload = await fetch_weather_json_async(lat, lng)
        return parse_weather_payload(payload)

    def _drain_completed_fetches(self) -> None:
        now = time.time()
        while True:
            try:
                key, mapped = self._completed.get_nowait()
            except queue.Empty:
                break
            self._inflight.pop(key, None)
            self._cache[key] = _CacheEntry(value=mapped, expires_at=now + self._cache_ttl_s)


def _weather_defaults(grips: type[WeatherGrips]) -> dict[Any, Any]:
    mapped = _weather_payload_defaults()
    return {
        grips.WEATHER_TEMP_C: mapped["temp_c"],
        grips.WEATHER_HUMIDITY: mapped["humidity_pct"],
        grips.WEATHER_WIND_SPEED: mapped["wind_speed_kph"],
        grips.WEATHER_WIND_DIR: mapped["wind_dir"],
        grips.WEATHER_RAIN_PCT: mapped["rain_pct"],
        grips.WEATHER_SUNNY_PCT: mapped["sunny_pct"],
        grips.WEATHER_UV_INDEX: mapped["uv_index"],
    }


def _weather_payload_defaults() -> dict[str, Any]:
    return {
        "temp_c": None,
        "humidity_pct": None,
        "wind_speed_kph": None,
        "wind_dir": "",
        "rain_pct": None,
        "sunny_pct": None,
        "uv_index": None,
    }
