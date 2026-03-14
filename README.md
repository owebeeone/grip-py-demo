# grip-py-demo

`grip-py-demo` is a PySide6 desktop demo for [`grip-py`](../grip-py).

It mirrors the same core demo surface as the React/Vue demos while keeping the Qt side intentionally simple: no reactive framework layer, just grip/drip subscriptions and explicit widget updates.

## What This Demo Shows

- Clock tab:
  - Current time via a clock tap
  - Counter controls
  - Visibility edge case: clock hides when count is odd
- Calculator tab:
  - Calculator state stored in grips
  - Button actions exposed as callable grips
- Weather tab:
  - Provider switching between `meteo` and `mock`
  - Two independent location contexts (`A` and `B`)
  - Real Open-Meteo path:
    - Geocoding tap: location text -> lat/lng/label
    - Weather tap: lat/lng -> weather metrics

## Requirements

- Python `>=3.10`
- [`grip-py`](../grip-py)
- `PySide6>=6.6`

## Install

From the `grip-dev` workspace root:

```bash
uv pip install -e ./grip-py -e ./grip-py-demo
```

## Run

Installed script:

```bash
grip-py-demo
```

Module mode (no script install required):

```bash
PYTHONPATH=./grip-py-demo/src:./grip-py/src python -m grip_py_demo.main
```

Direct file execution is also supported:

```bash
PYTHONPATH=./grip-py/src python ./grip-py-demo/src/grip_py_demo/main.py
```

Notes:
- Use `:` to separate `PYTHONPATH` entries on macOS/Linux.
- `Ctrl-C` (`SIGINT`) is handled for clean shutdown.
- Local-only demo mode works without a Glial server.
- Glial-backed shared/storage sessions are optional and only require `GLIAL_BASE_URL` when you want those remote features.

## Test

```bash
cd grip-py-demo
PYTHONPATH=src:../grip-py/src pytest -q
```

## Project Layout

- `src/grip_py_demo/grips.py`: demo grip catalog
- `src/grip_py_demo/demo_runtime.py`: runtime orchestration and test-facing API
- `src/grip_py_demo/controller.py`: drip subscriptions -> UI invalidation bridge
- `src/grip_py_demo/ui.py`: PySide6 widget tree and per-section updates
- `src/grip_py_demo/taps.py`: clock, calculator, and mock weather taps
- `src/grip_py_demo/openmeteo_taps.py`: real geocode/weather taps for Open-Meteo
- `src/grip_py_demo/main.py`: application entrypoint
- `tests/`: runtime, UI, entrypoint, and weather mapping tests
