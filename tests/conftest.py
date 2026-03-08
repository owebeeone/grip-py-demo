from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def _stub_openmeteo_http(monkeypatch: pytest.MonkeyPatch) -> None:
    from grip_py_demo import openmeteo_taps

    def fake_geocode(location: str, *, timeout_s: float = 5.0):
        _ = timeout_s
        by_name = {
            "sydney": (-33.8688, 151.2093, "Sydney"),
            "melbourne": (-37.8136, 144.9631, "Melbourne"),
            "san jose": (37.3382, -121.8863, "San Jose"),
            "palo alto": (37.4419, -122.1430, "Palo Alto"),
            "paris": (48.8566, 2.3522, "Paris"),
        }
        key = location.strip().lower()
        found = by_name.get(key)
        if found is None:
            return {"results": []}
        lat, lng, label = found
        return {"results": [{"latitude": lat, "longitude": lng, "name": label}]}

    def fake_weather(lat: float, lng: float, *, timeout_s: float = 7.0):
        _ = timeout_s
        base = abs(int(round(lat * 10))) + abs(int(round(lng * 10)))
        return {
            "current_weather": {
                "time": "2026-03-09T05:00",
                "temperature": 10 + (base % 25),
                "windspeed": 5 + (base % 20),
                "winddirection": base % 360,
            },
            "hourly": {
                "time": ["2026-03-09T04:00", "2026-03-09T05:00"],
                "relativehumidity_2m": [50, 55 + (base % 30)],
                "precipitation_probability": [10, base % 100],
                "cloudcover": [20, (base * 3) % 100],
                "uv_index": [2.0, 1.0 + ((base % 10) / 2.0)],
            },
        }

    monkeypatch.setattr(openmeteo_taps, "fetch_geocode_json", fake_geocode)
    monkeypatch.setattr(openmeteo_taps, "fetch_weather_json", fake_weather)
