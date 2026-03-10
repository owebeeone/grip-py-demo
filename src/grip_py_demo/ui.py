"""PySide6 widgets for grip-py-demo."""

from __future__ import annotations

from collections.abc import Callable
import logging

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .controller import RuntimeBridge
from .demo_runtime import DemoRuntime, WeatherSnapshot
from .demo_session import DemoSessionManager

LOGGER = logging.getLogger(__name__)


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

    def set_runtime(self, runtime: DemoRuntime) -> None:
        self._runtime = runtime

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

    def __init__(self, runtime: DemoRuntime, session_manager: DemoSessionManager | None = None):
        super().__init__()
        self._runtime = runtime
        self._session_manager = session_manager
        self._bridge = RuntimeBridge(runtime)
        self._bridge.grip_changed.connect(self._on_grip_changed)
        self._handlers: dict[tuple[str, str], list[Callable[[], None]]] = {}

        self.setWindowTitle("Grip Py Demo")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        session_row = QVBoxLayout()
        session_top_row = QHBoxLayout()
        self.current_session_label = QLabel("Current session: -")
        self.current_session_kind_label = QLabel("Session kind: local")
        self.storage_mode_combo = QComboBox()
        self.storage_mode_combo.addItems(["local", "remote", "both"])
        self.session_combo = QComboBox()
        self.load_session_button = QPushButton("Load Local Session")
        self.load_session_button.clicked.connect(self._load_selected_session)
        self.new_session_button = QPushButton("New Local Session")
        self.new_session_button.clicked.connect(self._create_new_session)
        session_top_row.addWidget(self.current_session_label)
        session_top_row.addWidget(self.current_session_kind_label)
        session_top_row.addWidget(QLabel("Storage mode:"))
        session_top_row.addWidget(self.storage_mode_combo)
        session_top_row.addStretch(1)
        session_top_row.addWidget(self.session_combo)
        session_top_row.addWidget(self.load_session_button)
        session_top_row.addWidget(self.new_session_button)
        session_row.addLayout(session_top_row)

        shared_row = QHBoxLayout()
        self.shared_session_combo = QComboBox()
        self.load_shared_button = QPushButton("Load Glial Shared Session")
        self.load_shared_button.clicked.connect(self._load_selected_shared_session)
        self.new_shared_button = QPushButton("New Glial Shared Session")
        self.new_shared_button.clicked.connect(self._create_new_shared_session)
        shared_row.addWidget(self.shared_session_combo)
        shared_row.addWidget(self.load_shared_button)
        shared_row.addWidget(self.new_shared_button)
        session_row.addLayout(shared_row)

        storage_row = QHBoxLayout()
        self.storage_session_combo = QComboBox()
        self.load_storage_button = QPushButton("Load Glial Storage Session")
        self.load_storage_button.clicked.connect(self._load_selected_storage_session)
        self.new_storage_button = QPushButton("New Glial Storage Session")
        self.new_storage_button.clicked.connect(self._create_new_storage_session)
        storage_row.addWidget(self.storage_session_combo)
        storage_row.addWidget(self.load_storage_button)
        storage_row.addWidget(self.new_storage_button)
        session_row.addLayout(storage_row)
        root.addLayout(session_row)

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
        self.clock_tab_button.clicked.connect(lambda: self._set_tab("clock"))
        self.calc_tab_button = QPushButton("Calculator")
        self.calc_tab_button.clicked.connect(lambda: self._set_tab("calc"))
        self.weather_tab_button = QPushButton("Weather")
        self.weather_tab_button.clicked.connect(lambda: self._set_tab("weather"))
        tabs.addWidget(self.clock_tab_button)
        tabs.addWidget(self.calc_tab_button)
        tabs.addWidget(self.weather_tab_button)
        tabs.addStretch(1)
        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.close)
        tabs.addWidget(self.exit_button)
        root.addLayout(tabs)

        self.stack = QStackedWidget()
        self.clock_page = self._build_clock_page()
        self.calc_page = self._build_calc_page()
        self.weather_page = self._build_weather_page()
        self.stack.addWidget(self.clock_page)
        self.stack.addWidget(self.calc_page)
        self.stack.addWidget(self.weather_page)
        root.addWidget(self.stack)

        self._configure_handlers()

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick_runtime)
        self._timer.start()

        self._refresh_session_controls()
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
        self.decrement_button = QPushButton("-")
        self.decrement_button.clicked.connect(self._decrement_count)
        self.increment_button = QPushButton("+")
        self.increment_button.clicked.connect(self._increment_count)
        counter_row.addWidget(self.decrement_button)
        counter_row.addWidget(self.count_label)
        counter_row.addWidget(self.increment_button)
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
            ("7", lambda: self._press_digit(7)),
            ("8", lambda: self._press_digit(8)),
            ("9", lambda: self._press_digit(9)),
            ("/", lambda: self._press_operator("/")),
            ("4", lambda: self._press_digit(4)),
            ("5", lambda: self._press_digit(5)),
            ("6", lambda: self._press_digit(6)),
            ("*", lambda: self._press_operator("*")),
            ("1", lambda: self._press_digit(1)),
            ("2", lambda: self._press_digit(2)),
            ("3", lambda: self._press_digit(3)),
            ("-", lambda: self._press_operator("-")),
            ("0", lambda: self._press_digit(0)),
            ("C", self._press_clear),
            ("=", self._press_equals),
            ("+", lambda: self._press_operator("+")),
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
        self.provider_meteo_button.clicked.connect(lambda: self._set_weather_provider("meteo"))
        self.provider_mock_button = QPushButton("Mock")
        self.provider_mock_button.clicked.connect(lambda: self._set_weather_provider("mock"))
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

    def _bind(self, ctx, grip, handler: Callable[[], None]) -> None:
        key = (ctx.id, grip.key)
        self._handlers.setdefault(key, []).append(handler)

    def _configure_handlers(self) -> None:
        self._handlers.clear()
        main = self._runtime.main_context
        grips = self._runtime.grips
        weather = self._runtime.weather_grips

        self._bind(main, grips.CURRENT_TAB, self._update_tab_controls)
        self._bind(main, grips.COUNT, self._update_count)
        self._bind(main, grips.CURRENT_TIME, self._update_clock_time)
        self._bind(main, grips.PAGE_SIZE, self._update_page_size)
        self._bind(main, grips.DESCRIPTION, self._update_description)
        self._bind(main, grips.CALC_DISPLAY, self._update_calc_display)
        self._bind(main, grips.WEATHER_PROVIDER_NAME, self._update_provider)

        self._bind(self._runtime.header_context, weather.WEATHER_TEMP_C, self._update_header_temp)

        for column_name, column_ctx in self._runtime.column_contexts.items():
            updater = lambda current_column=column_name: self._update_weather_column(current_column)
            for grip in (
                weather.WEATHER_LOCATION,
                weather.GEO_LABEL,
                weather.WEATHER_TEMP_C,
                weather.WEATHER_HUMIDITY,
                weather.WEATHER_WIND_SPEED,
                weather.WEATHER_WIND_DIR,
                weather.WEATHER_RAIN_PCT,
                weather.WEATHER_SUNNY_PCT,
                weather.WEATHER_UV_INDEX,
            ):
                self._bind(column_ctx, grip, updater)

    def _on_grip_changed(self, ctx_id: str, grip_key: str) -> None:
        handlers = self._handlers.get((ctx_id, grip_key), ())
        for handler in handlers:
            handler()

    def _update_tab_controls(self) -> None:
        tab = self._runtime.get_tab()
        tab_index = {"clock": 0, "calc": 1, "weather": 2}[tab]
        self.stack.setCurrentIndex(tab_index)
        self.clock_tab_button.setDisabled(tab == "clock")
        self.calc_tab_button.setDisabled(tab == "calc")
        self.weather_tab_button.setDisabled(tab == "weather")

    def _update_header_temp(self) -> None:
        header_temp = self._runtime.get_header_temp()
        header_text = "--" if header_temp is None else f"{header_temp:.1f}"
        self.header_temp_label.setText(f"- Sydney temp {header_text}°C")

    def _update_count(self) -> None:
        count_value = int(self._bridge.read(self._runtime.grips.COUNT) or 0)
        self.count_label.setText(f"Count: {count_value}")
        LOGGER.info(
            "count_ui_updated session_id=%s drip_value=%r widget_text=%s",
            self._runtime.session_id,
            count_value,
            self.count_label.text(),
        )
        self._update_clock_time()

    def _update_clock_time(self) -> None:
        if self._runtime.is_clock_visible():
            self.clock_time_label.setText(
                f"Time: {self._runtime.get_time().strftime('%H:%M:%S')}"
            )
            self.clock_time_label.show()
            self.clock_blocked_label.hide()
        else:
            self.clock_time_label.hide()
            self.clock_blocked_label.show()

    def _update_page_size(self) -> None:
        self.page_size_label.setText(f"Page size: {self._runtime.get_page_size()}")

    def _update_description(self) -> None:
        self.description_label.setText(f"Description: {self._runtime.get_description()}")

    def _update_calc_display(self) -> None:
        self.calc_display_label.setText(self._runtime.get_calc_display())

    def _update_provider(self) -> None:
        provider = self._runtime.get_weather_provider()
        self.provider_label.setText(f"Current weather provider: {provider}")
        self.provider_meteo_button.setDisabled(provider == "meteo")
        self.provider_mock_button.setDisabled(provider == "mock")

    def _update_weather_column(self, column: str) -> None:
        snapshot = self._runtime.get_weather_snapshot(column)
        location = self._runtime.get_weather_location(column)
        if column == "A":
            self.column_a.set_location(location)
            self.column_a.set_snapshot(snapshot)
            return
        self.column_b.set_location(location)
        self.column_b.set_snapshot(snapshot)

    def render(self) -> None:
        self._refresh_session_controls()
        self._update_tab_controls()
        self._update_header_temp()
        self._update_count()
        self._update_page_size()
        self._update_description()
        self._update_calc_display()
        self._update_provider()
        self._update_weather_column("A")
        self._update_weather_column("B")

    def _tick_runtime(self) -> None:
        self._runtime.tick()

    def _set_tab(self, tab: str) -> None:
        self._runtime.set_tab(tab)

    def _increment_count(self) -> None:
        self._runtime.increment_count()

    def _decrement_count(self) -> None:
        self._runtime.decrement_count()

    def _set_weather_provider(self, provider: str) -> None:
        self._runtime.set_weather_provider(provider)

    def _press_digit(self, digit: int) -> None:
        self._runtime.press_digit(digit)

    def _press_operator(self, operator: str) -> None:
        self._runtime.press_operator(operator)

    def _press_clear(self) -> None:
        self._runtime.press_clear()

    def _press_equals(self) -> None:
        self._runtime.press_equals()

    def _refresh_session_controls(self) -> None:
        current_session_id = self._runtime.session_id or "-"
        self.current_session_label.setText(f"Current session: {current_session_id}")
        if self._session_manager is None:
            self.session_combo.setEnabled(False)
            self.load_session_button.setEnabled(False)
            self.new_session_button.setEnabled(False)
            self.shared_session_combo.setEnabled(False)
            self.load_shared_button.setEnabled(False)
            self.new_shared_button.setEnabled(False)
            self.storage_session_combo.setEnabled(False)
            self.load_storage_button.setEnabled(False)
            self.new_storage_button.setEnabled(False)
            return
        current_session = self._session_manager.ensure_current_session()
        self.current_session_kind_label.setText(f"Session kind: {current_session.session_kind}")
        storage_mode = current_session.storage_mode
        mode_index = self.storage_mode_combo.findText(storage_mode)
        if mode_index >= 0:
            self.storage_mode_combo.setCurrentIndex(mode_index)
        sessions = self._session_manager.list_local_sessions()
        self.session_combo.blockSignals(True)
        self.session_combo.clear()
        current_index = -1
        for index, session in enumerate(sessions):
            label = (
                f"{session.title} ({session.session_id})"
                if session.title
                else session.session_id
            )
            self.session_combo.addItem(label, session.session_id)
            if session.session_id == self._runtime.session_id:
                current_index = index
        if current_index >= 0:
            self.session_combo.setCurrentIndex(current_index)
        self.session_combo.blockSignals(False)
        has_selection = self.session_combo.count() > 0
        self.session_combo.setEnabled(has_selection)
        self.load_session_button.setEnabled(has_selection)
        self.new_session_button.setEnabled(True)
        try:
            remote_sessions = self._session_manager.list_remote_sessions()
        except Exception:
            remote_sessions = []
        self.shared_session_combo.blockSignals(True)
        self.storage_session_combo.blockSignals(True)
        self.shared_session_combo.clear()
        self.storage_session_combo.clear()
        for session in remote_sessions:
            label = (
                f"{session.title} ({session.session_id})"
                if session.title
                else session.session_id
            )
            self.shared_session_combo.addItem(label, session.session_id)
            self.storage_session_combo.addItem(label, session.session_id)
        self.shared_session_combo.blockSignals(False)
        self.storage_session_combo.blockSignals(False)
        has_remote = bool(remote_sessions)
        self.shared_session_combo.setEnabled(has_remote)
        self.load_shared_button.setEnabled(has_remote)
        self.new_shared_button.setEnabled(True)
        self.storage_session_combo.setEnabled(has_remote)
        self.load_storage_button.setEnabled(has_remote)
        self.new_storage_button.setEnabled(True)

    def _swap_runtime(self, runtime: DemoRuntime) -> None:
        previous_runtime = self._runtime
        self._bridge.dispose()
        previous_runtime.close()
        self._runtime = runtime
        self.column_a.set_runtime(runtime)
        self.column_b.set_runtime(runtime)
        self._bridge = RuntimeBridge(runtime)
        self._bridge.grip_changed.connect(self._on_grip_changed)
        self._configure_handlers()
        self.render()
        LOGGER.info("session_loaded session_id=%s", self._runtime.session_id)
        LOGGER.info(
            "session_loaded_count session_id=%s drip_value=%r widget_text=%s",
            self._runtime.session_id,
            int(self._bridge.read(self._runtime.grips.COUNT) or 0),
            self.count_label.text(),
        )

    def _load_selected_session(self) -> None:
        if self._session_manager is None:
            return
        session_id = self.session_combo.currentData()
        if not isinstance(session_id, str) or not session_id:
            return
        LOGGER.info(
            "load_local_session requested_session_id=%s current_session_id=%s",
            session_id,
            self._runtime.session_id,
        )
        self._session_manager.select_local_session(session_id)
        self._swap_runtime(self._session_manager.build_runtime(session_id))

    def _create_new_session(self) -> None:
        if self._session_manager is None:
            return
        session = self._session_manager.create_and_select_new_local_session()
        self._swap_runtime(self._session_manager.build_runtime(session.glial_session_id))

    def _selected_storage_mode(self) -> str:
        mode = self.storage_mode_combo.currentText().strip()
        return mode if mode in {"local", "remote", "both"} else "local"

    def _load_selected_shared_session(self) -> None:
        if self._session_manager is None:
            return
        session_id = self.shared_session_combo.currentData()
        if not isinstance(session_id, str) or not session_id:
            return
        session = self._session_manager.select_remote_session(
            session_id,
            session_kind="glial-shared",
            storage_mode=self._selected_storage_mode(),
        )
        self._swap_runtime(
            self._session_manager.build_runtime(
                session.glial_session_id,
                session_kind="glial-shared",
            )
        )

    def _create_new_shared_session(self) -> None:
        if self._session_manager is None:
            return
        session = self._session_manager.create_and_select_new_remote_session(
            session_kind="glial-shared",
            storage_mode=self._selected_storage_mode(),
        )
        self._swap_runtime(
            self._session_manager.build_runtime(
                session.glial_session_id,
                session_kind="glial-shared",
            )
        )

    def _load_selected_storage_session(self) -> None:
        if self._session_manager is None:
            return
        session_id = self.storage_session_combo.currentData()
        if not isinstance(session_id, str) or not session_id:
            return
        session = self._session_manager.select_remote_session(
            session_id,
            session_kind="glial-storage",
            storage_mode=self._selected_storage_mode(),
        )
        self._swap_runtime(
            self._session_manager.build_runtime(
                session.glial_session_id,
                session_kind="glial-storage",
            )
        )

    def _create_new_storage_session(self) -> None:
        if self._session_manager is None:
            return
        session = self._session_manager.create_and_select_new_remote_session(
            session_kind="glial-storage",
            storage_mode=self._selected_storage_mode(),
        )
        self._swap_runtime(
            self._session_manager.build_runtime(
                session.glial_session_id,
                session_kind="glial-storage",
            )
        )

    def closeEvent(self, event):  # type: ignore[override]
        self._timer.stop()
        self._bridge.dispose()
        self._runtime.close()
        super().closeEvent(event)


def _fmt(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)
