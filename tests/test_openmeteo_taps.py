from __future__ import annotations

from grip_py_demo.openmeteo_taps import parse_geocode_payload, parse_weather_payload


def test_parse_geocode_payload_uses_first_result() -> None:
    lat, lng, label = parse_geocode_payload(
        {
            "results": [
                {
                    "latitude": -33.8688,
                    "longitude": 151.2093,
                    "name": "Sydney",
                }
            ]
        },
        fallback_label="Sydney",
    )

    assert lat == -33.8688
    assert lng == 151.2093
    assert label == "Sydney"


def test_parse_geocode_payload_falls_back_to_input_label() -> None:
    lat, lng, label = parse_geocode_payload({}, fallback_label="Nowhere")
    assert lat is None
    assert lng is None
    assert label == "Nowhere"


def test_parse_weather_payload_maps_current_hour_fields() -> None:
    payload = {
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

    mapped = parse_weather_payload(payload)

    assert mapped["temp_c"] == 24.7
    assert mapped["wind_speed_kph"] == 13.2
    assert mapped["wind_dir"] == "E"
    assert mapped["humidity_pct"] == 68
    assert mapped["rain_pct"] == 40
    assert mapped["sunny_pct"] == 40
    assert mapped["uv_index"] == 5.4
