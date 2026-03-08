"""PySide6 widgets for grip-py-demo."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .controller import RuntimeBridge
from .demo_runtime import DemoRuntime, WeatherSnapshot


class WeatherColumnWidget(QWidget):
    """Single weather destination view (location selector + metrics)."""

    def __init__(self, runtime: DemoRuntime, column: str, title: str):
        super().__init__()
        self._runtime = runtime
        self._column = column

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel(title))
        self.location_combo = QComboBox()
        self.location_combo.addItems(list(runtime.location_options))
        self.location_combo.currentTextChanged.connect(self._on_location_changed)
        selector_row.addWidget(self.location_combo)
        layout.addLayout(selector_row)

        self.location_label = QLabel("Location: -")
        layout.addWidget(self.location_label)

        metrics_grid = QGridLayout()
        self.value_labels: dict[str, QLabel] = {}
        rows = [
            ("Temp (°C)", "temp"),
            ("Humidity (%)", "humidity"),
            ("Wind (kph)", "wind"),
            ("Wind Dir", "wind_dir"),
            ("Rain chance (%)", "rain"),
            ("Sunny (%)", "sunny"),
            ("UV Index", "uv"),
        ]
        for row_index, (label, key) in enumerate(rows):
            metrics_grid.addWidget(QLabel(label), row_index, 0)
            value = QLabel("-")
            metrics_grid.addWidget(value, row_index, 1)
            self.value_labels[key] = value
        layout.addLayout(metrics_grid)

        self.setStyleSheet(
            "QWidget { border: 1px solid #ddd; border-radius: 6px; }"
            "QLabel { border: none; }"
        )

    def _on_location_changed(self, location: str) -> None:
        self._runtime.set_weather_location(self._column, location)

    def set_location(self, location: str) -> None:
        index = self.location_combo.findText(location)
        if index < 0 and location:
            self.location_combo.addItem(location)
            index = self.location_combo.findText(location)
        if index >= 0 and self.location_combo.currentIndex() != index:
            self.location_combo.blockSignals(True)
            self.location_combo.setCurrentIndex(index)
            self.location_combo.blockSignals(False)

    def set_snapshot(self, snapshot: WeatherSnapshot) -> None:
        self.location_label.setText(f"Location: {snapshot.location_label or '-'}")
        self.value_labels["temp"].setText(_fmt(snapshot.temp_c))
        self.value_labels["humidity"].setText(_fmt(snapshot.humidity_pct))
        self.value_labels["wind"].setText(_fmt(snapshot.wind_speed_kph))
        self.value_labels["wind_dir"].setText(snapshot.wind_dir or "-")
        self.value_labels["rain"].setText(_fmt(snapshot.rain_pct))
        self.value_labels["sunny"].setText(_fmt(snapshot.sunny_pct))
        self.value_labels["uv"].setText(_fmt(snapshot.uv_index))


class MainWindow(QWidget):
    """Top-level application window mirroring grip-react/grip-vue demo UI."""

    def __init__(self, runtime: DemoRuntime):
        super().__init__()
        self._runtime = runtime
        self._bridge = RuntimeBridge(runtime)
        self._bridge.state_changed.connect(self.render)

        self.setWindowTitle("Grip Py Demo")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        self.title_label = QLabel("Grip Py Demo")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.header_temp_label = QLabel("- Sydney temp --°C")
        header.addWidget(self.title_label)
        header.addWidget(self.header_temp_label)
        header.addStretch(1)
        root.addLayout(header)

        tabs = QHBoxLayout()
        self.clock_tab_button = QPushButton("Clock & Counter")
        self.clock_tab_button.clicked.connect(lambda: self._runtime.set_tab("clock"))
        self.calc_tab_button = QPushButton("Calculator")
        self.calc_tab_button.clicked.connect(lambda: self._runtime.set_tab("calc"))
        self.weather_tab_button = QPushButton("Weather")
        self.weather_tab_button.clicked.connect(lambda: self._runtime.set_tab("weather"))
        tabs.addWidget(self.clock_tab_button)
        tabs.addWidget(self.calc_tab_button)
        tabs.addWidget(self.weather_tab_button)
        tabs.addStretch(1)
        root.addLayout(tabs)

        self.stack = QStackedWidget()
        self.clock_page = self._build_clock_page()
        self.calc_page = self._build_calc_page()
        self.weather_page = self._build_weather_page()
        self.stack.addWidget(self.clock_page)
        self.stack.addWidget(self.calc_page)
        self.stack.addWidget(self.weather_page)
        root.addWidget(self.stack)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._runtime.tick)
        self._timer.start()

        self.render()

    def _build_clock_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)

        self.clock_time_label = QLabel("Time: --:--:--")
        self.clock_blocked_label = QLabel("Count is odd - no time")
        self.clock_blocked_label.setStyleSheet("color: #a00000;")

        self.page_size_label = QLabel("Page size: -")
        self.count_label = QLabel("Count: -")
        self.description_label = QLabel("Description: -")

        counter_row = QHBoxLayout()
        dec_button = QPushButton("-")
        dec_button.clicked.connect(self._runtime.decrement_count)
        inc_button = QPushButton("+")
        inc_button.clicked.connect(self._runtime.increment_count)
        counter_row.addWidget(dec_button)
        counter_row.addWidget(self.count_label)
        counter_row.addWidget(inc_button)
        counter_row.addStretch(1)

        layout.addWidget(self.clock_time_label)
        layout.addWidget(self.clock_blocked_label)
        layout.addWidget(self.page_size_label)
        layout.addLayout(counter_row)
        layout.addWidget(self.description_label)
        layout.addStretch(1)
        return page

    def _build_calc_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)

        self.calc_display_label = QLabel("0")
        self.calc_display_label.setStyleSheet(
            "font-family: monospace; font-size: 20px;"
            "padding: 8px; border: 1px solid #ccc;"
        )
        layout.addWidget(self.calc_display_label)

        grid = QGridLayout()
        buttons = [
            ("7", lambda: self._runtime.press_digit(7)),
            ("8", lambda: self._runtime.press_digit(8)),
            ("9", lambda: self._runtime.press_digit(9)),
            ("/", lambda: self._runtime.press_operator("/")),
            ("4", lambda: self._runtime.press_digit(4)),
            ("5", lambda: self._runtime.press_digit(5)),
            ("6", lambda: self._runtime.press_digit(6)),
            ("*", lambda: self._runtime.press_operator("*")),
            ("1", lambda: self._runtime.press_digit(1)),
            ("2", lambda: self._runtime.press_digit(2)),
            ("3", lambda: self._runtime.press_digit(3)),
            ("-", lambda: self._runtime.press_operator("-")),
            ("0", lambda: self._runtime.press_digit(0)),
            ("C", self._runtime.press_clear),
            ("=", self._runtime.press_equals),
            ("+", lambda: self._runtime.press_operator("+")),
        ]
        for idx, (label, callback) in enumerate(buttons):
            button = QPushButton(label)
            button.clicked.connect(callback)
            row = idx // 4
            col = idx % 4
            grid.addWidget(button, row, col)
        layout.addLayout(grid)
        layout.addStretch(1)
        return page

    def _build_weather_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        provider_row = QHBoxLayout()
        self.provider_label = QLabel("Current weather provider: meteo")
        self.provider_meteo_button = QPushButton("Meteo")
        self.provider_meteo_button.clicked.connect(
            lambda: self._runtime.set_weather_provider("meteo")
        )
        self.provider_mock_button = QPushButton("Mock")
        self.provider_mock_button.clicked.connect(
            lambda: self._runtime.set_weather_provider("mock")
        )
        provider_row.addWidget(self.provider_label)
        provider_row.addStretch(1)
        provider_row.addWidget(self.provider_meteo_button)
        provider_row.addWidget(self.provider_mock_button)
        layout.addLayout(provider_row)

        columns = QHBoxLayout()
        self.column_a = WeatherColumnWidget(self._runtime, "A", "Location A")
        self.column_b = WeatherColumnWidget(self._runtime, "B", "Location B")
        columns.addWidget(self.column_a)
        columns.addWidget(self.column_b)
        layout.addLayout(columns)
        layout.addStretch(1)
        return page

    def render(self) -> None:
        tab = self._runtime.get_tab()
        tab_index = {"clock": 0, "calc": 1, "weather": 2}[tab]
        self.stack.setCurrentIndex(tab_index)
        self.clock_tab_button.setDisabled(tab == "clock")
        self.calc_tab_button.setDisabled(tab == "calc")
        self.weather_tab_button.setDisabled(tab == "weather")

        header_temp = self._runtime.get_header_temp()
        header_text = "--" if header_temp is None else f"{header_temp:.1f}"
        self.header_temp_label.setText(f"- Sydney temp {header_text}°C")

        if self._runtime.is_clock_visible():
            self.clock_time_label.setText(
                f"Time: {self._runtime.get_time().strftime('%H:%M:%S')}"
            )
            self.clock_time_label.show()
            self.clock_blocked_label.hide()
        else:
            self.clock_time_label.hide()
            self.clock_blocked_label.show()

        self.page_size_label.setText(f"Page size: {self._runtime.get_page_size()}")
        self.count_label.setText(f"Count: {self._runtime.get_count()}")
        self.description_label.setText(f"Description: {self._runtime.get_description()}")

        self.calc_display_label.setText(self._runtime.get_calc_display())

        provider = self._runtime.get_weather_provider()
        self.provider_label.setText(f"Current weather provider: {provider}")
        self.provider_meteo_button.setDisabled(provider == "meteo")
        self.provider_mock_button.setDisabled(provider == "mock")

        snapshot_a = self._runtime.get_weather_snapshot("A")
        snapshot_b = self._runtime.get_weather_snapshot("B")
        self.column_a.set_location(self._runtime.get_weather_location("A"))
        self.column_b.set_location(self._runtime.get_weather_location("B"))
        self.column_a.set_snapshot(snapshot_a)
        self.column_b.set_snapshot(snapshot_b)

    def closeEvent(self, event):  # type: ignore[override]
        self._timer.stop()
        self._bridge.dispose()
        super().closeEvent(event)


def _fmt(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)
