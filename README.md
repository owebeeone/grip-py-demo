# grip-py-demo

PySide6 desktop demo for [`grip-py`](../grip-py) that mirrors the `grip-react-demo` / `grip-vue-demo` UI and interactions:

- Clock + counter tab (clock hidden when count is odd)
- Calculator tab with function-grip actions
- Weather tab with provider switching (`meteo` / `mock`) and two independent location contexts

The UI is rendered manually by subscribing to drips and updating widgets. This intentionally avoids introducing a higher-level reactive framework for Qt.

## Requirements

- Python 3.10+
- `grip-py` available in the environment
- `PySide6`

## Install (workspace-local)

From `grip-dev`:

```bash
uv pip install -e ./grip-py -e ./grip-py-demo
```

## Run

```bash
grip-py-demo
```

Or without installing scripts:

```bash
PYTHONPATH=./grip-py-demo/src:./grip-py/src python -m grip_py_demo.main
```

## Test

```bash
cd grip-py-demo
PYTHONPATH=src:../grip-py/src pytest -q
```

## Structure

- `src/grip_py_demo/grips.py`: grip catalog
- `src/grip_py_demo/taps.py`: clock, calculator, and weather taps
- `src/grip_py_demo/demo_runtime.py`: runtime orchestration + testable API
- `src/grip_py_demo/controller.py`: drip-to-render bridge for Qt
- `src/grip_py_demo/ui.py`: PySide6 widget tree
- `src/grip_py_demo/main.py`: app entry point
- `tests/test_demo_runtime.py`: regression and behavior tests
