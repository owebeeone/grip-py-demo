from grip_py_demo.demo_runtime import DemoRuntime


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
    runtime.tick_weather()
    mock_a = runtime.get_weather_snapshot("A")
    assert mock_a.provider == "mock"
    assert mock_a.temp_c != initial_a.temp_c

    runtime.set_weather_location("A", "Nowhere")
    runtime.tick_weather()
    updated_a = runtime.get_weather_snapshot("A")
    assert updated_a.location_label == "Nowhere"
    assert updated_a.temp_c is not None
