import os
from pathlib import Path

import numpy as np
import pyqtgraph as pg
import traceback
import pyqtgraph.exporters

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QProgressDialog,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class full_analysis_window(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("CAMAC Signal Analyser")
        self.resize(1280, 800)

        self.archive = None
        self.file_loaded = False
        self.current_file_name = "Файл не выбран"
        self.encoding_format = "unknown"

        self.num_pulses = 0
        self.original_num_pulses = 0
        self.current_index = 0
        self.last_b_value_results = {}

        self.raw_ae_data = []
        self.raw_eme_data = []
        self.ae_data = []
        self.eme_data = []

        self.original_event_indices = np.array([], dtype=int)
        self.relative_seconds = np.array([], dtype=float)
        self.ae_energy = np.array([], dtype=float)
        self.eme_energy = np.array([], dtype=float)

        self.combo_b_value_channel = None
        self.input_b_value_min_m = None
        self.lbl_b_value_result = None
        self.lbl_raw_header = None

        self.combo_wavelet_channel = None
        self.combo_wavelet_scope = None
        self.combo_wavelet_name = None
        self.input_wavelet_min_freq = None
        self.input_wavelet_max_freq = None
        self.pw_wavelet = None

        self.last_wavelet_amplitude = None
        self.last_wavelet_time_ms = None
        self.last_wavelet_frequencies = None
        self.last_wavelet_channel_title = ""

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.init_tab1()
        self.init_tab2()
        self.init_tab3()
        self.init_tab4()
        self.init_tab5()
        self.init_tab_b_value()

        self.toggle_ui_state(False)

    # ================= HELPERS =================

    def update_file_status_label(self) -> None:
        if not self.file_loaded:
            self.lbl_file_status.setText(
                f"<b>Статус:</b> {self.current_file_name}"
            )
            return

        duration_text = "—"
        if len(self.relative_seconds) > 0:
            duration_text = f"{self.relative_seconds[-1]:.3f} с"

        self.lbl_file_status.setText(
            f"<b>Загружен файл:</b><br>"
            f"<font color='green'>{self.current_file_name}</font><br>"
            f"Формат: {self.encoding_format}<br>"
            f"В архиве: {self.original_num_pulses}<br>"
            f"Текущий диапазон: {self.num_pulses}<br>"
            f"Длительность: {duration_text}"
        )

    def setup_graph_context_menu(self, plot_widget: pg.PlotWidget) -> None:
        plot_widget.setBackground("w")

        # Disable PyQtGraph's default cramped Export dialog.
        plot_widget.setMenuEnabled(False)

        # Use our own clean context menu.
        plot_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        plot_widget.customContextMenuRequested.connect(
            lambda position, current_plot=plot_widget: self.show_graph_context_menu(
                current_plot,
                position,
            )
        )

    def show_graph_context_menu(
        self,
        plot_widget: pg.PlotWidget,
        position,
    ) -> None:
        menu = QMenu(self)

        save_action = menu.addAction("Сохранить график как PNG/JPG...")
        save_action.triggered.connect(
            lambda: self.save_graph_as_image(plot_widget)
        )

        menu.exec(plot_widget.mapToGlobal(position))

    def save_graph_as_image(self, plot_widget: pg.PlotWidget) -> None:
        if not self.file_loaded:
            self.show_message(
                "Ошибка экспорта",
                "Сначала загрузите CAMAC архив.",
                QMessageBox.Warning,
            )
            return

        if len(plot_widget.plotItem.listDataItems()) == 0:
            self.show_message(
                "Ошибка экспорта",
                "На выбранном графике нет данных для экспорта.",
                QMessageBox.Warning,
            )
            return

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Сохранить график как изображение",
            str(Path.home() / "camac_graph.png"),
            (
                "PNG image (*.png);;"
                "JPEG image (*.jpg);;"
                "All files (*.*)"
            ),
        )

        if not file_path:
            return

        output_path = Path(file_path)

        if output_path.suffix == "":
            if "JPEG" in selected_filter:
                output_path = output_path.with_suffix(".jpg")
            else:
                output_path = output_path.with_suffix(".png")

        try:
            exporter = pyqtgraph.exporters.ImageExporter(plot_widget.plotItem)
            exporter.parameters()["width"] = 1600
            exporter.export(str(output_path))

        except Exception as error:
            self.show_message(
                "Ошибка экспорта",
                (
                    "Не удалось сохранить график.\n\n"
                    f"Ошибка: {repr(error)}"
                ),
                QMessageBox.Critical,
                details=traceback.format_exc(),
            )
            return

        if not output_path.exists():
            self.show_message(
                "Ошибка экспорта",
                (
                    "Экспорт завершился без ошибки, но файл не был найден.\n\n"
                    f"Ожидаемый путь:\n{output_path}"
                ),
                QMessageBox.Critical,
            )
            return

        self.show_message(
            "Успех",
            (
                "График успешно экспортирован.\n\n"
                f"Файл:\n{output_path}"
            ),
            QMessageBox.Information,
        )

    def toggle_ui_state(self, enabled: bool) -> None:
        self.btn_max.setEnabled(enabled)
        self.input_max.setEnabled(enabled)
        self.btn_min.setEnabled(enabled)
        self.input_min.setEnabled(enabled)
        self.btn_cut.setEnabled(enabled)
        self.btn_reset.setEnabled(enabled)
        self.combo_accumulation_x_axis.setEnabled(enabled)

        self.spin_pulse.setEnabled(enabled)
        self.btn_delete.setEnabled(enabled)

        self.btn_calc_stats.setEnabled(enabled)
        self.radio_single_signal.setEnabled(enabled)
        self.radio_jumping_window.setEnabled(enabled)
        self.input_window_size.setEnabled(
            enabled and self.radio_jumping_window.isChecked()
        )

    def get_event_numbers(self) -> np.ndarray:
        return np.arange(1, self.num_pulses + 1)

    def on_accumulation_x_axis_changed(self) -> None:
        if not self.file_loaded:
            return

        x_axis_mode = self.combo_accumulation_x_axis.currentData()

        self.line_min.blockSignals(True)
        self.line_max.blockSignals(True)

        if x_axis_mode == "relative_time":
            self.input_min.setPlaceholderText("Время MIN, с")
            self.input_max.setPlaceholderText("Время MAX, с")

            if len(self.relative_seconds) > 0:
                min_time = float(self.relative_seconds[0])
                max_time = float(self.relative_seconds[-1])

                self.line_min.setPos(min_time)
                self.line_max.setPos(max_time)

                self.input_min.setText(f"{min_time:.6f}")
                self.input_max.setText(f"{max_time:.6f}")

        else:
            self.input_min.setPlaceholderText("Номер импульса MIN")
            self.input_max.setPlaceholderText("Номер импульса MAX")

            self.line_min.setPos(1)
            self.line_max.setPos(self.num_pulses)

            self.input_min.setText("1")
            self.input_max.setText(str(self.num_pulses))

        self.line_min.blockSignals(False)
        self.line_max.blockSignals(False)

        self.update_accumulation_plot()

    def apply_cut_by_indices(
        self,
        start_index: int,
        end_index_exclusive: int,
    ) -> None:
        self.ae_data = self.ae_data[start_index:end_index_exclusive]
        self.eme_data = self.eme_data[start_index:end_index_exclusive]

        self.original_event_indices = self.original_event_indices[
            start_index:end_index_exclusive
        ]

        if len(self.relative_seconds) >= end_index_exclusive:
            self.relative_seconds = self.relative_seconds[
                start_index:end_index_exclusive
            ]

            if len(self.relative_seconds) > 0:
                self.relative_seconds = self.relative_seconds - self.relative_seconds[0]

        self.num_pulses = len(self.ae_data)

        self.update_file_status_label()

        self.spin_pulse.blockSignals(True)
        self.spin_pulse.setRange(1, self.num_pulses)
        self.spin_pulse.setValue(1)
        self.spin_pulse.blockSignals(False)

        self.lbl_total.setText(f"Всего импульсов: {self.num_pulses}")

        if self.combo_accumulation_x_axis.currentData() == "relative_time":
            self.line_min.setPos(float(self.relative_seconds[0]))
            self.line_max.setPos(float(self.relative_seconds[-1]))

            self.input_min.setText(f"{self.relative_seconds[0]:.6f}")
            self.input_max.setText(f"{self.relative_seconds[-1]:.6f}")
        else:
            self.line_min.setPos(1)
            self.line_max.setPos(self.num_pulses)

            self.input_min.setText("1")
            self.input_max.setText(str(self.num_pulses))

        self.update_accumulation_plot()
        self.load_pulse(1)
        self.draw_placeholder_stats_and_b_value()

        self.show_message(
            "CUT",
            (
                "Обрезка выполнена.\n\n"
                f"Исходный архив: {self.original_num_pulses}\n"
                f"Текущий диапазон: {self.num_pulses}"
            ),
            QMessageBox.Information,
        )

    def show_message(
        self,
        title: str,
        text: str,
        icon: QMessageBox.Icon = QMessageBox.Information,
        details: str | None = None,
    ) -> None:
        from PySide6.QtWidgets import QDialog, QTextEdit, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(620)

        if details is not None and details.strip() != "":
            dialog.setMinimumHeight(360)
        else:
            dialog.setMinimumHeight(180)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        text_label.setMinimumWidth(560)
        text_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(text_label)

        if details is not None and details.strip() != "":
            details_box = QTextEdit()
            details_box.setReadOnly(True)
            details_box.setPlainText(details)
            details_box.setMinimumHeight(140)
            layout.addWidget(details_box)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.exec()   

    def ask_confirmation(
        self,
        title: str,
        text: str,
        yes_text: str = "Да",
        no_text: str = "Нет",
    ) -> bool:
        from PySide6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QLabel,
            QDialogButtonBox,
            QPushButton,
        )

        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(520)
        dialog.setMinimumHeight(220)

        layout = QVBoxLayout(dialog)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(label)

        buttons = QDialogButtonBox()

        yes_button = QPushButton(yes_text)
        no_button = QPushButton(no_text)

        buttons.addButton(yes_button, QDialogButtonBox.AcceptRole)
        buttons.addButton(no_button, QDialogButtonBox.RejectRole)

        yes_button.clicked.connect(dialog.accept)
        no_button.clicked.connect(dialog.reject)

        layout.addWidget(buttons)

        return dialog.exec() == QDialog.Accepted

    def calculate_b_value_from_amplitudes(
        self,
        amplitudes: np.ndarray,
        min_magnitude: float | None = None,
    ) -> tuple[float, float, np.ndarray, np.ndarray]:
        amplitudes = np.asarray(amplitudes, dtype=float)
        amplitudes = amplitudes[np.isfinite(amplitudes)]
        amplitudes = amplitudes[amplitudes > 0]

        if len(amplitudes) < 5:
            raise ValueError("Недостаточно ненулевых амплитуд для расчета B-value.")

        magnitudes = np.log10(amplitudes ** 2)

        if min_magnitude is not None:
            magnitudes = magnitudes[magnitudes >= min_magnitude]

        if len(magnitudes) < 5:
            raise ValueError(
                "После применения минимальной M осталось слишком мало событий."
            )

        unique_magnitudes = np.sort(np.unique(magnitudes))

        cumulative_counts = np.array(
            [
                np.sum(magnitudes >= magnitude)
                for magnitude in unique_magnitudes
            ],
            dtype=float,
        )

        valid_mask = cumulative_counts > 0

        x = unique_magnitudes[valid_mask]
        y = np.log10(cumulative_counts[valid_mask])

        if len(x) < 2:
            raise ValueError("Недостаточно точек для линейной аппроксимации B-value.")

        slope, intercept = np.polyfit(x, y, 1)

        b_value = -float(slope)
        a_value = float(intercept)

        return b_value, a_value, x, y

    # ================= TAB 1: CROPPING / ACCUMULATION =================

    def init_tab1(self) -> None:
        tab = QWidget()
        main_layout = QHBoxLayout(tab)

        left_panel = QVBoxLayout()
        left_panel.setAlignment(Qt.AlignTop)
        left_panel.setSpacing(15)

        self.lbl_file_status = QLabel(f"<b>Статус:</b> {self.current_file_name}")
        self.lbl_file_status.setWordWrap(True)
        left_panel.addWidget(self.lbl_file_status)

        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.setMinimumHeight(40)
        self.btn_browse.setStyleSheet(
            "background-color: #d1e7dd; font-weight: bold;"
        )
        self.btn_browse.clicked.connect(self.open_file_dialog)
        left_panel.addWidget(self.btn_browse)

        left_panel.addSpacing(10)
        left_panel.addWidget(QLabel("<b>Ось X графика / режим обрезки:</b>"))

        self.combo_accumulation_x_axis = QComboBox()
        self.combo_accumulation_x_axis.addItem("По номеру импульса", "event_number")
        self.combo_accumulation_x_axis.addItem("По времени архива, с", "relative_time")
        self.combo_accumulation_x_axis.currentIndexChanged.connect(
            self.on_accumulation_x_axis_changed
        )

        left_panel.addWidget(self.combo_accumulation_x_axis)

        left_panel.addWidget(QLabel("<b>Левая граница обрезки:</b>"))
        self.btn_min = QPushButton("Min")
        self.btn_min.clicked.connect(lambda: self.activate_line_mode("min"))
        self.input_min = QLineEdit()
        self.input_min.setPlaceholderText("Номер импульса MIN")
        self.input_min.textChanged.connect(self.sync_line_from_input)
        left_panel.addWidget(self.btn_min)
        left_panel.addWidget(self.input_min)

        left_panel.addSpacing(5)

        left_panel.addWidget(QLabel("<b>Правая граница обрезки:</b>"))
        self.btn_max = QPushButton("Max")
        self.btn_max.clicked.connect(lambda: self.activate_line_mode("max"))
        self.input_max = QLineEdit()
        self.input_max.setPlaceholderText("Номер импульса MAX")
        self.input_max.textChanged.connect(self.sync_line_from_input)
        left_panel.addWidget(self.btn_max)
        left_panel.addWidget(self.input_max)
        left_panel.addSpacing(15)

        self.btn_cut = QPushButton("CUT")
        self.btn_cut.setMinimumHeight(45)
        self.btn_cut.setStyleSheet(
            "background-color: #ffe066; "
            "font-weight: bold; "
            "font-size: 14px; "
            "border: 1px solid gray;"
        )
        self.btn_cut.clicked.connect(self.cut_data)
        left_panel.addWidget(self.btn_cut)

        self.btn_reset = QPushButton("RESET")
        self.btn_reset.setMinimumHeight(40)
        self.btn_reset.setStyleSheet(
            "background-color: #dee2e6; font-weight: bold;"
        )
        self.btn_reset.clicked.connect(self.reset_data)
        left_panel.addWidget(self.btn_reset)

        main_layout.addLayout(left_panel, stretch=1)

        self.plot_widget1 = pg.PlotWidget(
            title="Окно 1: Накопление АЭ во времени"
        )
        self.setup_graph_context_menu(self.plot_widget1)
        self.plot_widget1.setLabel("left", "Накопленная энергия АЭ")
        self.plot_widget1.setLabel("bottom", "Номер импульса")
        self.plot_widget1.showGrid(x=True, y=True)

        self.line_min = pg.InfiniteLine(
            pos=1,
            angle=90,
            movable=True,
            pen=pg.mkPen("g", width=2.5, style=Qt.DashLine),
        )
        self.line_max = pg.InfiniteLine(
            pos=1,
            angle=90,
            movable=True,
            pen=pg.mkPen("r", width=2.5, style=Qt.DashLine),
        )

        self.line_min.sigPositionChanged.connect(
            lambda: self.sync_input_from_line("min")
        )
        self.line_max.sigPositionChanged.connect(
            lambda: self.sync_input_from_line("max")
        )

        self.plot_widget1.addItem(self.line_min)
        self.plot_widget1.addItem(self.line_max)

        main_layout.addWidget(self.plot_widget1, stretch=4)
        self.tabs.addTab(tab, "Окно 1: Обрезка")

    # ================= TAB 2: EVENT-BY-EVENT ANALYSIS =================

    def init_tab2(self) -> None:
        tab = QWidget()
        main_layout = QHBoxLayout(tab)

        grid_layout = QGridLayout()

        self.pw_ae_time = pg.PlotWidget(title="Форма сигнала АЭ")
        self.pw_eme_time = pg.PlotWidget(title="Форма сигнала ЭМЭ")
        self.pw_ae_fft = pg.PlotWidget(title="Амплитудный спектр АЭ")
        self.pw_eme_fft = pg.PlotWidget(title="Амплитудный спектр ЭМЭ")

        self.pw_ae_time.setLabel("bottom", "Время", units="us")
        self.pw_eme_time.setLabel("bottom", "Время", units="us")
        self.pw_ae_fft.setLabel("bottom", "Частота", units="Hz")
        self.pw_eme_fft.setLabel("bottom", "Частота", units="Hz")

        self.pw_ae_time.setLabel("left", "AE")
        self.pw_eme_time.setLabel("left", "EME")
        self.pw_ae_fft.setLabel("left", "Амплитуда")
        self.pw_eme_fft.setLabel("left", "Амплитуда")

        for i, plot_widget in enumerate(
            [
                self.pw_ae_time,
                self.pw_eme_time,
                self.pw_ae_fft,
                self.pw_eme_fft,
            ]
        ):
            self.setup_graph_context_menu(plot_widget)
            plot_widget.showGrid(x=True, y=True)
            grid_layout.addWidget(plot_widget, i // 2, i % 2)

        main_layout.addLayout(grid_layout, stretch=3)

        control_panel = QVBoxLayout()
        control_panel.setAlignment(Qt.AlignTop)

        self.lbl_total = QLabel("Всего импульсов: 0")
        control_panel.addWidget(self.lbl_total)

        control_panel.addWidget(QLabel("Выбрать импульс:"))
        self.spin_pulse = QSpinBox()
        self.spin_pulse.setMinimum(1)
        self.spin_pulse.valueChanged.connect(self.load_pulse)
        control_panel.addWidget(self.spin_pulse)

        control_panel.addSpacing(10)

        self.btn_delete = QPushButton("Удалить текущий импульс")
        self.btn_delete.setStyleSheet(
            "background-color: #f8d7da; color: #721c24;"
        )
        self.btn_delete.clicked.connect(self.delete_pulse)
        control_panel.addWidget(self.btn_delete)

        control_panel.addSpacing(25)

        control_panel.addWidget(QLabel("<b>Текущие параметры:</b>"))
        self.lbl_stats = QLabel(
            "<b>Текущий импульс:</b> —<br>"
            "<b>Исходный номер:</b> —<br>"
            "<b>Время архива:</b> —<br><br>"
            "<b>Энергия АЭ:</b> —<br>"
            "<b>Мощность АЭ:</b> —<br>"
            "<b>Max abs АЭ:</b> —<br><br>"
            "<b>Энергия ЭМЭ:</b> —<br>"
            "<b>Мощность ЭМЭ:</b> —<br>"
            "<b>Max abs ЭМЭ:</b> —"
        )
        control_panel.addWidget(self.lbl_stats)

        control_panel.addSpacing(15)

        control_panel.addWidget(QLabel("<b>RAW header preview:</b>"))

        self.lbl_raw_header = QLabel("RAW данные: —")
        self.lbl_raw_header.setWordWrap(True)
        control_panel.addWidget(self.lbl_raw_header)

        main_layout.addLayout(control_panel, stretch=1)
        self.tabs.addTab(tab, "Окно 2: Поимпульсный анализ")

    # ================= TAB 3: STATISTICS =================

    def init_tab3(self) -> None:
        tab = QWidget()
        main_layout = QHBoxLayout(tab)

        grid_layout = QGridLayout()

        self.pw_d_ae = pg.PlotWidget(title="d-value АЭ")
        self.pw_d_eme = pg.PlotWidget(title="d-value ЭМЭ")
        self.pw_s_ae = pg.PlotWidget(title="S-value АЭ")
        self.pw_s_eme = pg.PlotWidget(title="S-value ЭМЭ")
        self.pw_tsallis_ae = pg.PlotWidget(title="Параметр Тсаллиса q АЭ")
        self.pw_tsallis_eme = pg.PlotWidget(title="Параметр Тсаллиса q ЭМЭ")

        self.stat_plots = [
            self.pw_d_ae,
            self.pw_d_eme,
            self.pw_s_ae,
            self.pw_s_eme,
            self.pw_tsallis_ae,
            self.pw_tsallis_eme,
        ]

        for i, plot_widget in enumerate(self.stat_plots):
            self.setup_graph_context_menu(plot_widget)
            plot_widget.showGrid(x=True, y=True)
            grid_layout.addWidget(plot_widget, i // 2, i % 2)

        main_layout.addLayout(grid_layout, stretch=3)

        side_panel = QVBoxLayout()
        side_panel.setAlignment(Qt.AlignTop)

        group_box = QGroupBox("Параметры графиков")
        group_layout = QVBoxLayout(group_box)

        self.stat_mode_group = QButtonGroup(self)

        self.radio_single_signal = QRadioButton("1 сигнал за раз")
        self.radio_jumping_window = QRadioButton("Прыгающее скользящее окно")

        self.radio_single_signal.setChecked(True)

        self.stat_mode_group.addButton(self.radio_single_signal)
        self.stat_mode_group.addButton(self.radio_jumping_window)

        group_layout.addWidget(QLabel("<b>Вариант расчета:</b>"))
        group_layout.addWidget(self.radio_single_signal)
        group_layout.addWidget(self.radio_jumping_window)

        group_layout.addWidget(QLabel("Размер окна:"))
        self.input_window_size = QLineEdit("20")
        self.input_window_size.setEnabled(False)
        group_layout.addWidget(self.input_window_size)

        self.radio_single_signal.toggled.connect(self.update_stat_mode_ui)
        self.radio_jumping_window.toggled.connect(self.update_stat_mode_ui)

        self.btn_calc_stats = QPushButton("Рассчитать")
        self.btn_calc_stats.setStyleSheet(
            "background-color: #cfe2ff; font-weight: bold;"
        )
        self.btn_calc_stats.clicked.connect(self.calculate_stats_click)
        group_layout.addWidget(self.btn_calc_stats)

        side_panel.addWidget(group_box)
        main_layout.addLayout(side_panel, stretch=1)

        self.tabs.addTab(tab, "Окно 3: Статистика")

    def update_stat_mode_ui(self) -> None:
        use_jumping_window = self.radio_jumping_window.isChecked()
        self.input_window_size.setEnabled(
            self.file_loaded and use_jumping_window
    )

    def calculate_stats_click(self) -> None:
        if not self.file_loaded:
            self.show_message(
                "Ошибка",
                "Сначала загрузите CAMAC архив.",
                QMessageBox.Warning,
            )
            return

        if self.radio_single_signal.isChecked():
            self.draw_placeholder_stats_and_b_value()

            self.show_message(
                "Статистика",
                "Расчет выполнен для режима: 1 сигнал за раз.",
                QMessageBox.Information,
            )
            return

        try:
            window_size = int(self.input_window_size.text())
        except ValueError:
            self.show_message(
                "Ошибка",
                "Размер окна должен быть целым числом.",
                QMessageBox.Warning,
            )
            return

        if window_size < 2:
            self.show_message(
                "Ошибка",
                "Размер окна должен быть не меньше 2.",
                QMessageBox.Warning,
            )
            return

        if window_size > self.num_pulses:
            self.show_message(
                "Ошибка",
                "Размер окна не может быть больше количества импульсов.",
                QMessageBox.Warning,
            )
            return

        self.draw_jumping_window_stats(window_size)

        self.show_message(
            "Статистика",
            (
                "Расчет выполнен для прыгающего скользящего окна.\n\n"
                f"Размер окна: {window_size}"
            ),
            QMessageBox.Information,
        )

        # ================= TAB 4: WAVELETS =================

    def init_tab4(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("<b>Окно 4: Вейвлет-анализ текущего импульса</b>"))

        controls_layout = QHBoxLayout()

        controls_layout.addWidget(QLabel("Режим:"))

        self.combo_wavelet_scope = QComboBox()
        self.combo_wavelet_scope.addItem("Текущий импульс", "current")
        self.combo_wavelet_scope.addItem("Все импульсы", "all")
        controls_layout.addWidget(self.combo_wavelet_scope)

        controls_layout.addWidget(QLabel("Канал:"))

        self.combo_wavelet_channel = QComboBox()
        self.combo_wavelet_channel.addItem("АЭ", "ae")
        self.combo_wavelet_channel.addItem("ЭМЭ", "eme")
        controls_layout.addWidget(self.combo_wavelet_channel)

        controls_layout.addWidget(QLabel("Вейвлет:"))

        self.combo_wavelet_name = QComboBox()
        self.combo_wavelet_name.addItem("cmor1.5-1.0", "cmor1.5-1.0")
        self.combo_wavelet_name.addItem("morl", "morl")
        controls_layout.addWidget(self.combo_wavelet_name)

        controls_layout.addWidget(QLabel("Мин. частота, Hz:"))

        self.input_wavelet_min_freq = QLineEdit()
        self.input_wavelet_min_freq.setText("1000")
        self.input_wavelet_min_freq.setFixedWidth(100)
        controls_layout.addWidget(self.input_wavelet_min_freq)

        controls_layout.addWidget(QLabel("Макс. частота, Hz:"))

        self.input_wavelet_max_freq = QLineEdit()
        self.input_wavelet_max_freq.setText("1000000")
        self.input_wavelet_max_freq.setFixedWidth(100)
        controls_layout.addWidget(self.input_wavelet_max_freq)

        self.btn_draw_wavelet = QPushButton("Построить вейвлет")
        self.btn_draw_wavelet.clicked.connect(self.draw_wavelet_plot)
        controls_layout.addWidget(self.btn_draw_wavelet)

        self.btn_export_wavelet = QPushButton("Экспорт вейвлета CSV...")
        self.btn_export_wavelet.clicked.connect(self.export_wavelet_csv)
        controls_layout.addWidget(self.btn_export_wavelet)

        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        self.pw_wavelet = pg.PlotWidget(title="Вейвлет-спектр текущего импульса")
        self.setup_graph_context_menu(self.pw_wavelet)
        self.pw_wavelet.showGrid(x=True, y=True)
        self.pw_wavelet.setLabel("bottom", "Время", units="ms")
        self.pw_wavelet.setLabel("left", "Частота", units="Hz")

        layout.addWidget(self.pw_wavelet)

        layout.addWidget(
            QLabel(
                "<i>Вейвлет строится для текущего выбранного импульса из Окна 2.</i>"
            )
        )

        self.tabs.addTab(tab, "Окно 4: Вейвлеты")    

        # ================= TAB 5: EXPORT =================

    def init_tab5(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(20)

        layout.addWidget(QLabel("<h2>Экспорт результатов</h2>"))

        box_data = QGroupBox("Сохранение табличных каталогов")
        layout_data = QVBoxLayout(box_data)
        layout_data.addWidget(
            QLabel(
                "Сохранение отфильтрованного каталога импульсов "
                "после CUT / удаления."
            )
        )

        btn_save_catalog = QPushButton("Экспортировать каталог в CSV...")
        btn_save_catalog.setMinimumHeight(40)
        btn_save_catalog.clicked.connect(self.export_current_catalog)
        layout_data.addWidget(btn_save_catalog)

        btn_save_current_event = QPushButton("Экспортировать текущий импульс в CSV...")
        btn_save_current_event.setMinimumHeight(40)
        btn_save_current_event.clicked.connect(self.export_current_event)
        layout_data.addWidget(btn_save_current_event)
       
        btn_save_current_event_raw = QPushButton("Экспортировать текущий импульс RAW в CSV...")
        btn_save_current_event_raw.setMinimumHeight(40)
        btn_save_current_event_raw.clicked.connect(self.export_current_event_raw)
        layout_data.addWidget(btn_save_current_event_raw)

        btn_export_range_folder = QPushButton("Экспортировать текущий диапазон в папку...")
        btn_export_range_folder.setMinimumHeight(40)
        btn_export_range_folder.clicked.connect(self.export_current_range_folder)
        layout_data.addWidget(btn_export_range_folder)

        layout.addWidget(box_data)

        box_plots = QGroupBox("Экспорт графиков")
        layout_plots = QVBoxLayout(box_plots)
        layout_plots.addWidget(
            QLabel("Графики можно сохранять через контекстное меню графика.")
        )

        layout.addWidget(box_plots)

        self.tabs.addTab(tab, "Окно 5: Экспорт")

    def export_current_catalog(self) -> None:
        if not self.file_loaded:
            self.show_message(
                "Ошибка",
                "Нечего экспортировать. Сначала загрузите CAMAC архив.",
                QMessageBox.Warning,
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить каталог",
            str(Path.home() / "camac_catalog.csv"),
            "CSV files (*.csv);;Text files (*.txt);;All files (*.*)",
        )

        if not file_path:
            return

        output_path = Path(file_path)

        if output_path.suffix == "":
            output_path = output_path.with_suffix(".csv")

        try:
            with open(output_path, "w", encoding="utf-8") as file:
                file.write(
                    "event_number,"
                    "original_event_number,"
                    "relative_seconds,"
                    "ae_max_abs,"
                    "eme_max_abs,"
                    "ae_max_abs_squared,"
                    "eme_max_abs_squared,"
                    "ae_energy,"
                    "eme_energy\n"
                )

                for i in range(self.num_pulses):
                    event_number = i + 1

                    if i < len(self.original_event_indices):
                        original_event_number = int(self.original_event_indices[i]) + 1
                    else:
                        original_event_number = event_number

                    relative_seconds = (
                        float(self.relative_seconds[i])
                        if i < len(self.relative_seconds)
                        else 0.0
                    )

                    ae_signal = self.ae_data[i]
                    eme_signal = self.eme_data[i]

                    ae_max_abs = float(np.max(np.abs(ae_signal)))
                    eme_max_abs = float(np.max(np.abs(eme_signal)))

                    ae_energy = float(np.sum(ae_signal ** 2))
                    eme_energy = float(np.sum(eme_signal ** 2))

                    file.write(
                        f"{event_number},"
                        f"{original_event_number},"
                        f"{relative_seconds:.6f},"
                        f"{ae_max_abs:.6f},"
                        f"{eme_max_abs:.6f},"
                        f"{ae_max_abs * ae_max_abs:.6f},"
                        f"{eme_max_abs * eme_max_abs:.6f},"
                        f"{ae_energy:.6f},"
                        f"{eme_energy:.6f}\n"
                    )

        except Exception as error:
            self.show_message(
                "Ошибка экспорта",
                (
                    "Не удалось сохранить каталог.\n\n"
                    f"Ошибка: {repr(error)}"
                ),
                QMessageBox.Critical,
                details=traceback.format_exc(),
            )
            return

        self.show_message(
            "Экспорт",
            (
                "Каталог успешно сохранен.\n\n"
                f"Файл:\n{output_path}\n"
                f"Строк данных: {self.num_pulses}"
            ),
            QMessageBox.Information,
        )


    def export_current_event(self) -> None:
        if not self.file_loaded:
            self.show_message(
                "Ошибка",
                "Сначала загрузите CAMAC архив.",
                QMessageBox.Warning,
            )
            return

        if not self.ae_data or not self.eme_data:
            self.show_message(
                "Ошибка",
                "Нет данных импульса для экспорта.",
                QMessageBox.Warning,
            )
            return

        event_index = self.current_index

        if event_index < 0 or event_index >= self.num_pulses:
            self.show_message(
                "Ошибка",
                "Текущий номер импульса вне диапазона.",
                QMessageBox.Warning,
            )
            return

        event_number = event_index + 1

        if event_index < len(self.original_event_indices):
            original_event_number = int(self.original_event_indices[event_index]) + 1
        else:
            original_event_number = event_number

        default_name = f"event_{event_number}_original_{original_event_number}.csv"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить текущий импульс",
            str(Path.home() / default_name),
            "CSV files (*.csv);;Text files (*.txt);;All files (*.*)",
        )

        if not file_path:
            return

        output_path = Path(file_path)

        if output_path.suffix == "":
            output_path = output_path.with_suffix(".csv")

        ae_signal = self.ae_data[event_index]
        eme_signal = self.eme_data[event_index]

        max_length = max(len(ae_signal), len(eme_signal))

        try:
            with open(output_path, "w", encoding="utf-8") as file:
                file.write(
                    "sample_index,"
                    "time_microseconds,"
                    "ae_signal,"
                    "eme_signal\n"
                )

                for sample_index in range(max_length):
                    time_microseconds = sample_index * 0.5

                    ae_value = (
                        f"{float(ae_signal[sample_index]):.6f}"
                        if sample_index < len(ae_signal)
                        else ""
                    )

                    eme_value = (
                        f"{float(eme_signal[sample_index]):.6f}"
                        if sample_index < len(eme_signal)
                        else ""
                    )

                    file.write(
                        f"{sample_index},"
                        f"{time_microseconds:.6f},"
                        f"{ae_value},"
                        f"{eme_value}\n"
                    )

        except Exception as error:
            self.show_message(
                "Ошибка экспорта",
                (
                    "Не удалось сохранить текущий импульс.\n\n"
                    f"Ошибка: {repr(error)}"
                ),
                QMessageBox.Critical,
                details=traceback.format_exc(),
            )
            return

        self.show_message(
            "Экспорт",
            (
                "Текущий импульс успешно сохранен.\n\n"
                f"Файл:\n{output_path}\n"
                f"Импульс: {event_number}\n"
                f"Исходный номер: {original_event_number}"
            ),
            QMessageBox.Information,
        )

    def export_current_event_raw(self) -> None:
        if not self.file_loaded:
            self.show_message(
                "Ошибка",
                "Сначала загрузите CAMAC архив.",
                QMessageBox.Warning,
            )
            return

        if self.archive is None:
            self.show_message(
                "Ошибка",
                "Архив не загружен.",
                QMessageBox.Warning,
            )
            return

        event_index = self.current_index

        if event_index < 0 or event_index >= self.num_pulses:
            self.show_message(
                "Ошибка",
                "Текущий номер импульса вне диапазона.",
                QMessageBox.Warning,
            )
            return

        event_number = event_index + 1

        if event_index < len(self.original_event_indices):
            original_event_number = int(self.original_event_indices[event_index]) + 1
        else:
            original_event_number = event_number

        original_event_index = original_event_number - 1

        default_name = (
            f"event_{event_number}_original_{original_event_number}_raw.csv"
        )

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить RAW данные текущего импульса",
            str(Path.home() / default_name),
            "CSV files (*.csv);;Text files (*.txt);;All files (*.*)",
        )

        if not file_path:
            return

        output_path = Path(file_path)

        if output_path.suffix == "":
            output_path = output_path.with_suffix(".csv")

        try:
            ae_raw = np.array(
                self.archive.ae_raw(original_event_index),
                dtype=np.uint16,
            )
            eme_raw = np.array(
                self.archive.eme_raw(original_event_index),
                dtype=np.uint16,
            )

            max_length = max(len(ae_raw), len(eme_raw))

            with open(output_path, "w", encoding="utf-8") as file:
                file.write(
                    "sample_index,"
                    "time_microseconds,"
                    "ae_raw,"
                    "eme_raw\n"
                )

                for sample_index in range(max_length):
                    time_microseconds = sample_index * 0.5

                    ae_value = (
                        str(int(ae_raw[sample_index]))
                        if sample_index < len(ae_raw)
                        else ""
                    )

                    eme_value = (
                        str(int(eme_raw[sample_index]))
                        if sample_index < len(eme_raw)
                        else ""
                    )

                    file.write(
                        f"{sample_index},"
                        f"{time_microseconds:.6f},"
                        f"{ae_value},"
                        f"{eme_value}\n"
                    )

        except Exception as error:
            self.show_message(
                "Ошибка экспорта",
                (
                    "Не удалось сохранить RAW данные текущего импульса.\n\n"
                    f"Ошибка: {repr(error)}"
                ),
                QMessageBox.Critical,
                details=traceback.format_exc(),
            )
            return

        self.show_message(
            "Экспорт",
            (
                "RAW данные текущего импульса успешно сохранены.\n\n"
                f"Файл:\n{output_path}\n"
                f"Импульс в текущем диапазоне: {event_number}\n"
                f"Исходный номер импульса: {original_event_number}"
            ),
            QMessageBox.Information,
        )

    def export_current_range_folder(self) -> None:
        if not self.file_loaded:
            self.show_message(
                "Ошибка",
                "Сначала загрузите CAMAC архив.",
                QMessageBox.Warning,
            )
            return

        if self.num_pulses == 0:
            self.show_message(
                "Ошибка",
                "Нет импульсов для экспорта.",
                QMessageBox.Warning,
            )
            return

        estimated_files = self.num_pulses * 2 + 1

        if self.num_pulses > 100:
            reply = QMessageBox.question(
                self,
                "Большой экспорт",
                (
                    "Вы собираетесь экспортировать большой диапазон.\n\n"
                    f"Импульсов: {self.num_pulses}\n"
                    f"Будет создано файлов: {estimated_files}\n\n"
                    "Продолжить?"
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply != QMessageBox.Yes:
                return

        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для экспорта текущего диапазона",
            str(Path.home()),
        )

        if not folder_path:
            return

        output_folder = Path(folder_path)

        export_folder = output_folder / f"camac_export_{self.current_file_name}"
        export_folder.mkdir(parents=True, exist_ok=True)

        try:
            catalog_path = export_folder / "archive_catalog.csv"

            with open(catalog_path, "w", encoding="utf-8") as file:
                file.write(
                    "event_number,"
                    "original_event_number,"
                    "relative_seconds,"
                    "ae_max_abs,"
                    "eme_max_abs,"
                    "ae_max_abs_squared,"
                    "eme_max_abs_squared,"
                    "ae_energy,"
                    "eme_energy\n"
                )

                for i in range(self.num_pulses):
                    event_number = i + 1

                    if i < len(self.original_event_indices):
                        original_event_number = int(self.original_event_indices[i]) + 1
                    else:
                        original_event_number = event_number

                    relative_seconds = (
                        float(self.relative_seconds[i])
                        if i < len(self.relative_seconds)
                        else 0.0
                    )

                    ae_signal = self.ae_data[i]
                    eme_signal = self.eme_data[i]

                    ae_max_abs = float(np.max(np.abs(ae_signal)))
                    eme_max_abs = float(np.max(np.abs(eme_signal)))

                    ae_energy = float(np.sum(ae_signal ** 2))
                    eme_energy = float(np.sum(eme_signal ** 2))

                    file.write(
                        f"{event_number},"
                        f"{original_event_number},"
                        f"{relative_seconds:.6f},"
                        f"{ae_max_abs:.6f},"
                        f"{eme_max_abs:.6f},"
                        f"{ae_max_abs * ae_max_abs:.6f},"
                        f"{eme_max_abs * eme_max_abs:.6f},"
                        f"{ae_energy:.6f},"
                        f"{eme_energy:.6f}\n"
                    )

            for i in range(self.num_pulses):
                event_number = i + 1

                if i < len(self.original_event_indices):
                    original_event_number = int(self.original_event_indices[i]) + 1
                else:
                    original_event_number = event_number

                processed_path = (
                    export_folder
                    / f"event_{event_number}_original_{original_event_number}_signal.csv"
                )
                raw_path = (
                    export_folder
                    / f"event_{event_number}_original_{original_event_number}_raw.csv"
                )

                self.write_processed_event_csv(processed_path, i)
                self.write_raw_event_csv(raw_path, i)

        except Exception as error:
            self.show_message(
                "Ошибка экспорта",
                (
                    "Не удалось экспортировать текущий диапазон.\n\n"
                    f"Ошибка: {repr(error)}"
                ),
                QMessageBox.Critical,
                details=traceback.format_exc(),
            )
            return

        self.show_message(
            "Экспорт",
            (
                "Текущий диапазон успешно экспортирован.\n\n"
                f"Папка:\n{export_folder}\n\n"
                f"Импульсов экспортировано: {self.num_pulses}"
            ),
            QMessageBox.Information,
        )

    def export_b_value_csv(self) -> None:
        if not self.file_loaded:
            self.show_message(
                "Ошибка",
                "Сначала загрузите CAMAC архив.",
                QMessageBox.Warning,
            )
            return

        if not self.last_b_value_results:
            self.draw_b_value_plot()

        if not self.last_b_value_results:
            self.show_message(
                "Ошибка",
                "Нет рассчитанных данных b-value для экспорта.",
                QMessageBox.Warning,
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить b-value CSV",
            str(Path.home() / "b_value_results.csv"),
            "CSV files (*.csv);;Text files (*.txt);;All files (*.*)",
        )

        if not file_path:
            return

        output_path = Path(file_path)

        if output_path.suffix == "":
            output_path = output_path.with_suffix(".csv")

        try:
            with open(output_path, "w", encoding="utf-8") as file:
                file.write(
                    "channel,"
                    "b_value,"
                    "a_value,"
                    "min_magnitude,"
                    "event_count_total,"
                    "point_index,"
                    "M,"
                    "log10_cumulative_N,"
                    "fit_y\n"
                )

                for channel_name, result in self.last_b_value_results.items():
                    b_value = float(result["b_value"])
                    a_value = float(result["a_value"])
                    min_magnitude = result["min_magnitude"]

                    min_magnitude_text = (
                        ""
                        if min_magnitude is None
                        else f"{float(min_magnitude):.6f}"
                    )

                    x_values = result["x"]
                    y_values = result["y"]
                    fit_values = result["fit_y"]

                    for point_index in range(len(x_values)):
                        file.write(
                            f"{channel_name},"
                            f"{b_value:.6f},"
                            f"{a_value:.6f},"
                            f"{min_magnitude_text},"
                            f"{self.num_pulses},"
                            f"{point_index + 1},"
                            f"{float(x_values[point_index]):.6f},"
                            f"{float(y_values[point_index]):.6f},"
                            f"{float(fit_values[point_index]):.6f}\n"
                        )

        except Exception as error:
            self.show_message(
                "Ошибка экспорта",
                (
                    "Не удалось сохранить b-value CSV.\n\n"
                    f"Ошибка: {repr(error)}"
                ),
                QMessageBox.Critical,
                details=traceback.format_exc(),
            )
            return

        self.show_message(
            "Экспорт",
            (
                "B-value CSV успешно сохранен.\n\n"
                f"Файл:\n{output_path}"
            ),
            QMessageBox.Information,
        )

    def export_wavelet_csv(self) -> None:
        if self.last_wavelet_amplitude is None:
            self.show_message(
                "Ошибка",
                "Сначала постройте вейвлет.",
                QMessageBox.Warning,
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить вейвлет CSV",
            str(Path.home() / "wavelet_scalogram.csv"),
            "CSV files (*.csv);;Text files (*.txt);;All files (*.*)",
        )

        if not file_path:
            return

        output_path = Path(file_path)

        if output_path.suffix == "":
            output_path = output_path.with_suffix(".csv")

        try:
            amplitude = self.last_wavelet_amplitude
            frequencies = self.last_wavelet_frequencies

            with open(output_path, "w", encoding="utf-8") as file:
                if self.last_wavelet_time_ms is not None:
                    time_ms = self.last_wavelet_time_ms

                    file.write(
                        "frequency_hz,"
                        "time_ms,"
                        "log10_wavelet_amplitude\n"
                    )

                    for freq_index in range(amplitude.shape[0]):
                        frequency = float(frequencies[freq_index])

                        for time_index in range(amplitude.shape[1]):
                            file.write(
                                f"{frequency:.6f},"
                                f"{float(time_ms[time_index]):.9f},"
                                f"{float(amplitude[freq_index, time_index]):.9f}\n"
                            )

                else:
                    file.write(
                        "frequency_hz,"
                        "event_number,"
                        "original_event_number,"
                        "log10_wavelet_amplitude\n"
                    )

                    for freq_index in range(amplitude.shape[0]):
                        frequency = float(frequencies[freq_index])

                        for event_index in range(amplitude.shape[1]):
                            event_number = event_index + 1

                            if event_index < len(self.original_event_indices):
                                original_event_number = (
                                    int(self.original_event_indices[event_index]) + 1
                                )
                            else:
                                original_event_number = event_number

                            file.write(
                                f"{frequency:.6f},"
                                f"{event_number},"
                                f"{original_event_number},"
                                f"{float(amplitude[freq_index, event_index]):.9f}\n"
                            )

        except Exception as error:
            self.show_message(
                "Ошибка экспорта",
                (
                    "Не удалось сохранить вейвлет CSV.\n\n"
                    f"Ошибка: {repr(error)}"
                ),
                QMessageBox.Critical,
                details=traceback.format_exc(),
            )
            return

        self.show_message(
            "Экспорт",
            (
                "Вейвлет CSV успешно сохранен.\n\n"
                f"Файл:\n{output_path}\n"
                f"Режим: {self.last_wavelet_channel_title}"
            ),
            QMessageBox.Information,
        )    

    def write_processed_event_csv(
        self,
        output_path: Path,
        event_index: int,
    ) -> None:
        ae_signal = self.ae_data[event_index]
        eme_signal = self.eme_data[event_index]

        max_length = max(len(ae_signal), len(eme_signal))

        with open(output_path, "w", encoding="utf-8") as file:
            file.write(
                "sample_index,"
                "time_microseconds,"
                "ae_signal,"
                "eme_signal\n"
            )

            for sample_index in range(max_length):
                time_microseconds = sample_index * 0.5

                ae_value = (
                    f"{float(ae_signal[sample_index]):.6f}"
                    if sample_index < len(ae_signal)
                    else ""
                )

                eme_value = (
                    f"{float(eme_signal[sample_index]):.6f}"
                    if sample_index < len(eme_signal)
                    else ""
                )

                file.write(
                    f"{sample_index},"
                    f"{time_microseconds:.6f},"
                    f"{ae_value},"
                    f"{eme_value}\n"
                )

    def write_raw_event_csv(
        self,
        output_path: Path,
        event_index: int,
    ) -> None:
        if event_index < len(self.original_event_indices):
            original_event_index = int(self.original_event_indices[event_index])
        else:
            original_event_index = event_index

        ae_raw = np.array(
            self.archive.ae_raw(original_event_index),
            dtype=np.uint16,
        )
        eme_raw = np.array(
            self.archive.eme_raw(original_event_index),
            dtype=np.uint16,
        )

        max_length = max(len(ae_raw), len(eme_raw))

        with open(output_path, "w", encoding="utf-8") as file:
            file.write(
                "sample_index,"
                "time_microseconds,"
                "ae_raw,"
                "eme_raw\n"
            )

            for sample_index in range(max_length):
                time_microseconds = sample_index * 0.5

                ae_value = (
                    str(int(ae_raw[sample_index]))
                    if sample_index < len(ae_raw)
                    else ""
                )

                eme_value = (
                    str(int(eme_raw[sample_index]))
                    if sample_index < len(eme_raw)
                    else ""
                )

                file.write(
                    f"{sample_index},"
                    f"{time_microseconds:.6f},"
                    f"{ae_value},"
                    f"{eme_value}\n"
                )
    # ================= B-VALUE TAB =================

    def init_tab_b_value(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(
            QLabel(
                "<b>Приложение: Нахождение b-value "
                "(log10(N ≥ M) = a - bM)</b>"
            )
        )

        controls_layout = QHBoxLayout()

        controls_layout.addWidget(QLabel("Канал:"))

        self.combo_b_value_channel = QComboBox()
        self.combo_b_value_channel.addItem("АЭ и ЭМЭ", "both")
        self.combo_b_value_channel.addItem("Только АЭ", "ae")
        self.combo_b_value_channel.addItem("Только ЭМЭ", "eme")
        controls_layout.addWidget(self.combo_b_value_channel)

        controls_layout.addWidget(QLabel("Минимальная M:"))

        self.input_b_value_min_m = QLineEdit()
        self.input_b_value_min_m.setPlaceholderText("auto")
        self.input_b_value_min_m.setFixedWidth(100)
        controls_layout.addWidget(self.input_b_value_min_m)

        self.btn_recalculate_b_value = QPushButton("Пересчитать b-value")
        self.btn_recalculate_b_value.clicked.connect(self.draw_b_value_plot)
        controls_layout.addWidget(self.btn_recalculate_b_value)

        self.btn_export_b_value = QPushButton("Экспорт b-value CSV...")
        self.btn_export_b_value.clicked.connect(self.export_b_value_csv)
        controls_layout.addWidget(self.btn_export_b_value)

        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        self.lbl_b_value_result = QLabel("B-value: —")
        self.lbl_b_value_result.setWordWrap(True)
        layout.addWidget(self.lbl_b_value_result)

        self.pw_b_value = pg.PlotWidget(
            title="B-value для АЭ и ЭМЭ"
        )
        self.setup_graph_context_menu(self.pw_b_value)

        self.pw_b_value.addLegend()
        self.pw_b_value.showGrid(x=True, y=True)

        self.pw_b_value.setLabel("left", "log10(N ≥ M)")
        self.pw_b_value.setLabel(
            "bottom",
            "M = log10(max_abs²)",
        )

        layout.addWidget(self.pw_b_value)

        layout.addWidget(
            QLabel(
                "<i>B-value рассчитывается по текущему диапазону импульсов. "
                "После CUT/delete график пересчитывается только для оставшихся импульсов. "
                "Минимальная M позволяет отбросить слабые события/шум.</i>"
            )
        )

        self.tabs.addTab(tab, "Приложение: b-value")

    # ================= MAIN LOGIC =================

    def open_file_dialog(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть бинарный архив CAMAC",
            str(Path.home()),
            "CAMAC archives (*.001 *.002 *.003 *.004 *.005 *.bin);;All files (*.*)",
        )

        if not file_name:
            return

        try:
            import camac_core

            self.archive = camac_core.parse_camac_file(file_name)

            self.num_pulses = self.archive.event_count()
            self.original_num_pulses = self.num_pulses
            self.original_event_indices = np.arange(self.num_pulses, dtype=int)

            self.ae_data = [
                np.array(self.archive.ae_signal(i), dtype=float)
                for i in range(self.num_pulses)
            ]

            self.eme_data = [
                np.array(self.archive.eme_signal(i), dtype=float)
                for i in range(self.num_pulses)
            ]

            self.raw_ae_data = list(self.ae_data)
            self.raw_eme_data = list(self.eme_data)

            self.relative_seconds = np.array(
                self.archive.relative_seconds(),
                dtype=float,
            )

            self.ae_energy = np.array(
                self.archive.ae_energy_values(),
                dtype=float,
            )

            self.eme_energy = np.array(
                self.archive.eme_energy_values(),
                dtype=float,
            )

        except Exception as error:
            self.show_message(
                "Ошибка чтения CAMAC архива",
                str(error),
                QMessageBox.Critical,
            )
            return

        if self.num_pulses <= 0:
            self.show_message(
                "Ошибка",
                "В архиве не найдено событий.",
                QMessageBox.Warning,
            )
            return

        self.file_loaded = True
        self.current_file_name = os.path.basename(file_name)

        self.encoding_format = self.archive.encoding_format()

        self.update_file_status_label()

        self.toggle_ui_state(True)

        self.spin_pulse.blockSignals(True)
        self.spin_pulse.setRange(1, self.num_pulses)
        self.spin_pulse.setValue(1)
        self.spin_pulse.blockSignals(False)

        self.lbl_total.setText(f"Всего импульсов: {self.num_pulses}")

        self.on_accumulation_x_axis_changed()

        self.load_pulse(1)
        self.draw_placeholder_stats_and_b_value()

        duration_text = "—"
        if len(self.relative_seconds) > 0:
            duration_text = f"{self.relative_seconds[-1]:.3f} с"

        self.show_message(
            "Файл прочитан",
            (
                "CAMAC архив успешно загружен.\n\n"
                f"Файл: {self.current_file_name}\n"
                f"Формат: {self.encoding_format}\n"
                f"Обнаружено импульсов: {self.num_pulses}\n"
                f"Длительность: {duration_text}"
            ),
            QMessageBox.Information,
        )

    def load_pulse(self, event_number: int) -> None:
        if not self.file_loaded or not self.ae_data:
            return

        if event_number < 1 or event_number > self.num_pulses:
            return

        event_index = event_number - 1
        self.current_index = event_index

        self.pw_ae_time.clear()
        self.pw_eme_time.clear()
        self.pw_ae_fft.clear()
        self.pw_eme_fft.clear()

        ae_signal = self.ae_data[event_index]
        eme_signal = self.eme_data[event_index]

        ae_time_us = np.arange(len(ae_signal)) * 0.5
        eme_time_us = np.arange(len(eme_signal)) * 0.5

        self.pw_ae_time.plot(
            ae_time_us,
            ae_signal,
            pen=pg.mkPen("b", width=1.5),
        )
        self.pw_eme_time.plot(
            eme_time_us,
            eme_signal,
            pen=pg.mkPen("r", width=1.5),
        )

        sample_interval_seconds = 500e-9

        ae_freqs = np.fft.rfftfreq(
            len(ae_signal),
            d=sample_interval_seconds,
        )
        eme_freqs = np.fft.rfftfreq(
            len(eme_signal),
            d=sample_interval_seconds,
        )

        fft_ae = np.abs(np.fft.rfft(ae_signal))
        fft_eme = np.abs(np.fft.rfft(eme_signal))

        self.pw_ae_fft.plot(
            ae_freqs,
            fft_ae,
            pen=pg.mkPen("darkBlue", width=1.5),
        )
        self.pw_eme_fft.plot(
            eme_freqs,
            fft_eme,
            pen=pg.mkPen("darkRed", width=1.5),
        )

        energy_ae = float(np.sum(ae_signal ** 2))
        energy_eme = float(np.sum(eme_signal ** 2))

        ae_duration_seconds = len(ae_signal) * 500e-9
        eme_duration_seconds = len(eme_signal) * 500e-9

        power_ae = energy_ae / ae_duration_seconds if ae_duration_seconds > 0 else 0.0
        power_eme = energy_eme / eme_duration_seconds if eme_duration_seconds > 0 else 0.0

        max_abs_ae = float(np.max(np.abs(ae_signal))) if len(ae_signal) > 0 else 0.0
        max_abs_eme = float(np.max(np.abs(eme_signal))) if len(eme_signal) > 0 else 0.0

        relative_time = (
            float(self.relative_seconds[event_index])
            if event_index < len(self.relative_seconds)
            else 0.0
        )

        original_event_number = event_number

        if event_index < len(self.original_event_indices):
            original_event_number = int(self.original_event_indices[event_index]) + 1

        self.lbl_stats.setText(
            f"<b>Текущий импульс:</b> {event_number}<br>"
            f"<b>Исходный номер:</b> {original_event_number}<br>"
            f"<b>Время архива:</b> {relative_time:.6f} с<br><br>"
            f"<b>Энергия АЭ:</b> {energy_ae:.2f} у.е.<br>"
            f"<b>Мощность АЭ:</b> {power_ae:.2f} у.е./с<br>"
            f"<b>Max abs АЭ:</b> {max_abs_ae:.2f}<br><br>"
            f"<b>Энергия ЭМЭ:</b> {energy_eme:.2f} у.е.<br>"
            f"<b>Мощность ЭМЭ:</b> {power_eme:.2f} у.е./с<br>"
            f"<b>Max abs ЭМЭ:</b> {max_abs_eme:.2f}"
        )

        if self.lbl_raw_header is not None and self.archive is not None:
            try:
                original_event_index = event_index

                if event_index < len(self.original_event_indices):
                    original_event_index = int(self.original_event_indices[event_index])

                ae_raw = np.array(
                    self.archive.ae_raw(original_event_index),
                    dtype=np.uint16,
                )
                eme_raw = np.array(
                    self.archive.eme_raw(original_event_index),
                    dtype=np.uint16,
                )

                ae_preview = ", ".join(str(int(value)) for value in ae_raw[:12])
                eme_preview = ", ".join(str(int(value)) for value in eme_raw[:12])

                self.lbl_raw_header.setText(
                    f"<b>AE raw[0..11]:</b><br>{ae_preview}<br><br>"
                    f"<b>EME raw[0..11]:</b><br>{eme_preview}"
                )

            except Exception as error:
                self.lbl_raw_header.setText(
                    f"RAW preview unavailable: {repr(error)}"
                )

    def delete_pulse(self) -> None:
        if not self.file_loaded or not self.ae_data:
            return

        event_index = self.current_index

        self.ae_data.pop(event_index)
        self.eme_data.pop(event_index)

        if event_index < len(self.relative_seconds):
            self.relative_seconds = np.delete(self.relative_seconds, event_index)
 
        if event_index < len(self.original_event_indices):
            self.original_event_indices = np.delete(
                self.original_event_indices,
                event_index,
            )

        self.num_pulses = len(self.ae_data)
        self.update_file_status_label()

        if self.num_pulses == 0:
            self.show_message(
                "Ошибка",
                "Все импульсы удалены.",
                QMessageBox.Warning,
                )            
            return

        self.spin_pulse.blockSignals(True)
        self.spin_pulse.setRange(1, self.num_pulses)

        next_event_number = min(event_index + 1, self.num_pulses)

        self.spin_pulse.setValue(next_event_number)
        self.spin_pulse.blockSignals(False)

        self.lbl_total.setText(f"Всего импульсов: {self.num_pulses}")

        self.on_accumulation_x_axis_changed()

        self.load_pulse(next_event_number)
        self.draw_placeholder_stats_and_b_value()

    def update_accumulation_plot(self) -> None:
        self.plot_widget1.clear()

        if not self.file_loaded or not self.ae_data:
            self.plot_widget1.addItem(self.line_min)
            self.plot_widget1.addItem(self.line_max)
            return

        event_numbers = self.get_event_numbers()

        ae_energy = np.array(
            [np.sum(signal ** 2) for signal in self.ae_data],
            dtype=float,
        )

        cumulative_ae_energy = np.cumsum(ae_energy)

        x_axis_mode = self.combo_accumulation_x_axis.currentData()

        if x_axis_mode == "relative_time" and len(self.relative_seconds) == self.num_pulses:
            x_values = self.relative_seconds
            self.plot_widget1.setLabel("bottom", "Время архива", units="s")
        else:
            x_values = event_numbers
            self.plot_widget1.setLabel("bottom", "Номер импульса")

        self.plot_widget1.plot(
            x_values,
            cumulative_ae_energy,
            pen=pg.mkPen("b", width=2.5),
        )

        self.plot_widget1.addItem(self.line_min)
        self.plot_widget1.addItem(self.line_max)

    def activate_line_mode(self, mode: str) -> None:
        if mode == "min":
            self.line_min.setPen(pg.mkPen("g", width=4, style=Qt.SolidLine))
            self.line_max.setPen(pg.mkPen("r", width=2, style=Qt.DashLine))
        else:
            self.line_max.setPen(pg.mkPen("r", width=4, style=Qt.SolidLine))
            self.line_min.setPen(pg.mkPen("g", width=2, style=Qt.DashLine))

    def sync_input_from_line(self, mode: str) -> None:
        if not self.file_loaded:
            return

        x_axis_mode = self.combo_accumulation_x_axis.currentData()

        if x_axis_mode == "relative_time":
            min_value_allowed = float(self.relative_seconds[0])
            max_value_allowed = float(self.relative_seconds[-1])

            if mode == "min":
                value = max(
                    min_value_allowed,
                    min(
                        float(self.line_min.getXPos()),
                        max_value_allowed,
                    ),
                )

                self.input_min.blockSignals(True)
                self.input_min.setText(f"{value:.6f}")
                self.input_min.blockSignals(False)

            elif mode == "max":
                value = max(
                    min_value_allowed,
                    min(
                        float(self.line_max.getXPos()),
                        max_value_allowed,
                    ),
                )

                self.input_max.blockSignals(True)
                self.input_max.setText(f"{value:.6f}")
                self.input_max.blockSignals(False)

            return

        if mode == "min":
            value = max(
                1,
                min(
                    int(round(self.line_min.getXPos())),
                    self.num_pulses,
                ),
            )

            self.input_min.blockSignals(True)
            self.input_min.setText(str(value))
            self.input_min.blockSignals(False)

        elif mode == "max":
            value = max(
                1,
                min(
                    int(round(self.line_max.getXPos())),
                    self.num_pulses,
                ),
            )

            self.input_max.blockSignals(True)
            self.input_max.setText(str(value))
            self.input_max.blockSignals(False)

    def sync_line_from_input(self) -> None:
        if not self.file_loaded:
            return

        x_axis_mode = self.combo_accumulation_x_axis.currentData()

        if x_axis_mode == "relative_time":
            if len(self.relative_seconds) == 0:
                return

            min_allowed = float(self.relative_seconds[0])
            max_allowed = float(self.relative_seconds[-1])

            try:
                min_value = float(self.input_min.text())

                if min_allowed <= min_value <= max_allowed:
                    self.line_min.setPos(min_value)

            except ValueError:
                pass

            try:
                max_value = float(self.input_max.text())

                if min_allowed <= max_value <= max_allowed:
                    self.line_max.setPos(max_value)

            except ValueError:
                pass

            return

        try:
            min_value = int(self.input_min.text())

            if 1 <= min_value <= self.num_pulses:
                self.line_min.setPos(min_value)

        except ValueError:
            pass

        try:
            max_value = int(self.input_max.text())

            if 1 <= max_value <= self.num_pulses:
                self.line_max.setPos(max_value)

        except ValueError:
            pass

    def cut_data(self) -> None:
        if not self.file_loaded:
            return

        x_axis_mode = self.combo_accumulation_x_axis.currentData()

        if x_axis_mode == "relative_time":
            self.cut_data_by_time()
        else:
            self.cut_data_by_event_number()

    def cut_data_by_event_number(self) -> None:
        try:
            min_event_number = int(self.input_min.text())
            max_event_number = int(self.input_max.text())
        except ValueError:
            self.show_message(
                "Ошибка",
                "Укажите целые номера границ.",
                QMessageBox.Warning,
            )
            return

        if min_event_number < 1 or max_event_number > self.num_pulses:
            self.show_message(
                "Ошибка",
                "Границы должны быть внутри диапазона импульсов.",
                QMessageBox.Warning,
            )
            return

        if min_event_number >= max_event_number:
            self.show_message(
                "Ошибка",
                "Min должен быть меньше Max.",
                QMessageBox.Warning,
            )
            return

        start_index = min_event_number - 1
        end_index_exclusive = max_event_number

        self.apply_cut_by_indices(start_index, end_index_exclusive)

    def cut_data_by_time(self) -> None:
        if len(self.relative_seconds) != self.num_pulses:
            self.show_message(
                "Ошибка",
                "Невозможно выполнить обрезку по времени: массив времени не совпадает с количеством импульсов.",
                QMessageBox.Warning,
            )
            return

        try:
            min_time = float(self.input_min.text())
            max_time = float(self.input_max.text())
        except ValueError:
            self.show_message(
                "Ошибка",
                "Укажите границы времени в секундах.",
                QMessageBox.Warning,
            )
            return

        if min_time >= max_time:
            self.show_message(
                "Ошибка",
                "Время MIN должно быть меньше времени MAX.",
                QMessageBox.Warning,
            )
            return

        mask = (self.relative_seconds >= min_time) & (self.relative_seconds <= max_time)
        matching_indices = np.where(mask)[0]

        if len(matching_indices) == 0:
            self.show_message(
                "Ошибка",
                "В выбранном временном диапазоне нет импульсов.",
                QMessageBox.Warning,
            )
            return

        start_index = int(matching_indices[0])
        end_index_exclusive = int(matching_indices[-1]) + 1

        self.apply_cut_by_indices(start_index, end_index_exclusive)

    def reset_data(self) -> None:
        if not self.file_loaded:
            return

        self.ae_data = list(self.raw_ae_data)
        self.eme_data = list(self.raw_eme_data)

        self.relative_seconds = np.array(
            self.archive.relative_seconds(),
            dtype=float,
        )

        self.num_pulses = len(self.ae_data)
        self.original_event_indices = np.arange(self.num_pulses, dtype=int)
        self.update_file_status_label()

        self.spin_pulse.blockSignals(True)
        self.spin_pulse.setRange(1, self.num_pulses)
        self.spin_pulse.setValue(1)
        self.spin_pulse.blockSignals(False)

        self.line_min.setPos(1)
        self.line_max.setPos(self.num_pulses)

        if self.combo_accumulation_x_axis.currentData() == "relative_time":
            self.line_min.setPos(float(self.relative_seconds[0]))
            self.line_max.setPos(float(self.relative_seconds[-1]))

            self.input_min.setText(f"{self.relative_seconds[0]:.6f}")
            self.input_max.setText(f"{self.relative_seconds[-1]:.6f}")
        else:
            self.line_min.setPos(1)
            self.line_max.setPos(self.num_pulses)

            self.input_min.setText("1")
            self.input_max.setText(str(self.num_pulses))

        self.lbl_total.setText(f"Всего импульсов: {self.num_pulses}")

        self.update_accumulation_plot()
        self.load_pulse(1)
        self.draw_placeholder_stats_and_b_value()

        self.show_message(
            "RESET",
            f"Данные восстановлены. Импульсов: {self.num_pulses}",
            QMessageBox.Information,
        )



    def draw_placeholder_stats_and_b_value(self) -> None:
        if not self.file_loaded or self.num_pulses == 0:
            return

        x = self.get_event_numbers()

        ae_energy = np.array(
            [np.sum(signal ** 2) for signal in self.ae_data],
            dtype=float,
        )
        eme_energy = np.array(
            [np.sum(signal ** 2) for signal in self.eme_data],
            dtype=float,
        )

        ae_max = np.array(
            [np.max(np.abs(signal)) for signal in self.ae_data],
            dtype=float,
        )
        eme_max = np.array(
            [np.max(np.abs(signal)) for signal in self.eme_data],
            dtype=float,
        )

        self.pw_d_ae.clear()
        self.pw_d_eme.clear()
        self.pw_s_ae.clear()
        self.pw_s_eme.clear()
        self.pw_tsallis_ae.clear()
        self.pw_tsallis_eme.clear()

        self.pw_d_ae.plot(x, ae_max, pen=pg.mkPen("b", width=1.5))
        self.pw_d_eme.plot(x, eme_max, pen=pg.mkPen("r", width=1.5))

        self.pw_s_ae.plot(x, ae_energy, pen=pg.mkPen("b", width=1.5))
        self.pw_s_eme.plot(x, eme_energy, pen=pg.mkPen("r", width=1.5))

        cumulative_ae = np.cumsum(ae_energy)
        cumulative_eme = np.cumsum(eme_energy)

        self.pw_tsallis_ae.plot(
            x,
            cumulative_ae,
            pen=pg.mkPen("b", width=1.5),
        )
        self.pw_tsallis_eme.plot(
            x,
            cumulative_eme,
            pen=pg.mkPen("r", width=1.5),
        )

        self.draw_b_value_plot()
    
    def draw_jumping_window_stats(self, window_size: int) -> None:
        if not self.file_loaded or self.num_pulses == 0:
            return

        ae_energy = np.array(
            [np.sum(signal ** 2) for signal in self.ae_data],
            dtype=float,
        )
        eme_energy = np.array(
            [np.sum(signal ** 2) for signal in self.eme_data],
            dtype=float,
        )

        ae_max = np.array(
            [np.max(np.abs(signal)) for signal in self.ae_data],
            dtype=float,
        )
        eme_max = np.array(
            [np.max(np.abs(signal)) for signal in self.eme_data],
            dtype=float,
        )

        x = []
        ae_energy_windowed = []
        eme_energy_windowed = []
        ae_max_windowed = []
        eme_max_windowed = []

        for start in range(0, self.num_pulses - window_size + 1, window_size):
            end = start + window_size

            x.append(start + 1)

            ae_energy_windowed.append(np.sum(ae_energy[start:end]))
            eme_energy_windowed.append(np.sum(eme_energy[start:end]))

            ae_max_windowed.append(np.max(ae_max[start:end]))
            eme_max_windowed.append(np.max(eme_max[start:end]))

        x = np.array(x, dtype=int)

        ae_energy_windowed = np.array(ae_energy_windowed, dtype=float)
        eme_energy_windowed = np.array(eme_energy_windowed, dtype=float)

        ae_max_windowed = np.array(ae_max_windowed, dtype=float)
        eme_max_windowed = np.array(eme_max_windowed, dtype=float)

        self.pw_d_ae.clear()
        self.pw_d_eme.clear()
        self.pw_s_ae.clear()
        self.pw_s_eme.clear()
        self.pw_tsallis_ae.clear()
        self.pw_tsallis_eme.clear()

        self.pw_d_ae.plot(x, ae_max_windowed, pen=pg.mkPen("b", width=1.5))
        self.pw_d_eme.plot(x, eme_max_windowed, pen=pg.mkPen("r", width=1.5))

        self.pw_s_ae.plot(x, ae_energy_windowed, pen=pg.mkPen("b", width=1.5))
        self.pw_s_eme.plot(x, eme_energy_windowed, pen=pg.mkPen("r", width=1.5))

        self.pw_tsallis_ae.plot(
            x,
            np.cumsum(ae_energy_windowed),
            pen=pg.mkPen("b", width=1.5),
        )
        self.pw_tsallis_eme.plot(
            x,
            np.cumsum(eme_energy_windowed),
            pen=pg.mkPen("r", width=1.5),
        )

        self.draw_b_value_placeholder(ae_energy_windowed, eme_energy_windowed)

    def draw_b_value_plot(self) -> None:
        if not self.file_loaded or not self.ae_data:
            return

        if self.combo_b_value_channel is None:
            return

        channel_mode = self.combo_b_value_channel.currentData()

        min_magnitude = None
        min_magnitude_text = self.input_b_value_min_m.text().strip()

        if min_magnitude_text:
            try:
                min_magnitude = float(min_magnitude_text)
            except ValueError:
                self.lbl_b_value_result.setText(
                    "<b>Ошибка:</b> минимальная M должна быть числом, например 5.2"
                )
                return

        ae_max_abs_values = np.array(
            [
                float(np.max(np.abs(signal)))
                for signal in self.ae_data
                if len(signal) > 0
            ],
            dtype=float,
        )

        eme_max_abs_values = np.array(
            [
                float(np.max(np.abs(signal)))
                for signal in self.eme_data
                if len(signal) > 0
            ],
            dtype=float,
        )

        self.pw_b_value.clear()
        self.last_b_value_results = {}

        result_lines = []
        error_lines = []

        if channel_mode in ("both", "ae"):
            try:
                ae_b, ae_a, ae_x, ae_y = self.calculate_b_value_from_amplitudes(
                    ae_max_abs_values,
                    min_magnitude,
                )

                self.pw_b_value.plot(
                    ae_x,
                    ae_y,
                    pen=None,
                    symbol="o",
                    symbolSize=5,
                    name="AE points",
                )

                ae_fit_y = ae_a - ae_b * ae_x

                self.pw_b_value.plot(
                    ae_x,
                    ae_fit_y,
                    pen=pg.mkPen("b", width=2),
                    name=f"AE fit, b={ae_b:.3f}",
                )

                result_lines.append(f"<b>AE b-value:</b> {ae_b:.4f}")

                self.last_b_value_results["AE"] = {
                    "b_value": ae_b,
                    "a_value": ae_a,
                    "x": ae_x,
                    "y": ae_y,
                    "fit_y": ae_fit_y,
                    "min_magnitude": min_magnitude,
                }

            except Exception as error:
                error_lines.append(f"<b>AE:</b> {str(error)}")

        if channel_mode in ("both", "eme"):
            try:
                eme_b, eme_a, eme_x, eme_y = self.calculate_b_value_from_amplitudes(
                    eme_max_abs_values,
                    min_magnitude,
                )

                self.pw_b_value.plot(
                    eme_x,
                    eme_y,
                    pen=None,
                    symbol="x",
                    symbolSize=6,
                    name="EME points",
                )

                eme_fit_y = eme_a - eme_b * eme_x

                self.pw_b_value.plot(
                    eme_x,
                    eme_fit_y,
                    pen=pg.mkPen("r", width=2),
                    name=f"EME fit, b={eme_b:.3f}",
                )

                result_lines.append(f"<b>EME b-value:</b> {eme_b:.4f}")

                self.last_b_value_results["EME"] = {
                    "b_value": eme_b,
                    "a_value": eme_a,
                    "x": eme_x,
                    "y": eme_y,
                    "fit_y": eme_fit_y,
                    "min_magnitude": min_magnitude,
                }

            except Exception as error:
                error_lines.append(f"<b>EME:</b> {str(error)}")

        threshold_text = "auto / нет" if min_magnitude is None else f"{min_magnitude:g}"

        if not result_lines:
            result_lines.append(
                "<b>B-value:</b> не рассчитан. "
                "Попробуйте уменьшить минимальную M или выбрать другой канал."
            )

        self.lbl_b_value_result.setText(
            "<br>".join(result_lines)
            + f"<br><b>Минимальная M:</b> {threshold_text}"
            + f"<br><b>Импульсов в текущем диапазоне:</b> {self.num_pulses}"
            + (
                "<br><br><b>Предупреждения:</b><br>" + "<br>".join(error_lines)
                if error_lines
                else ""
            )
        )

        self.pw_b_value.setTitle("B-value по текущему диапазону")
        self.pw_b_value.setLabel("bottom", "M = log10(max_abs²)")
        self.pw_b_value.setLabel("left", "log10(N ≥ M)")    

    def draw_b_value_placeholder(
        self,
        ae_energy: np.ndarray,
        eme_energy: np.ndarray,
    ) -> None:
        self.pw_b_value.clear()
        self.pw_b_value.addLegend()

        def prepare_b_value_points(energy_values: np.ndarray):
            energy_values = energy_values[energy_values > 0]

            if len(energy_values) < 5:
                return np.array([]), np.array([])

            magnitudes = np.log10(energy_values)
            thresholds = np.linspace(
                np.min(magnitudes),
                np.max(magnitudes),
                30,
            )

            counts = np.array(
                [np.sum(magnitudes >= threshold) for threshold in thresholds],
                dtype=float,
            )

            valid = counts > 0

            return thresholds[valid], np.log10(counts[valid])

        ae_magnitude, ae_log_count = prepare_b_value_points(ae_energy)
        eme_magnitude, eme_log_count = prepare_b_value_points(eme_energy)

        if len(ae_magnitude) > 0:
            self.pw_b_value.plot(
                ae_magnitude,
                ae_log_count,
                pen=pg.mkPen("b", width=2),
                name="АЭ",
            )

        if len(eme_magnitude) > 0:
            self.pw_b_value.plot(
                eme_magnitude,
                eme_log_count,
                pen=pg.mkPen("r", width=2),
                name="ЭМЭ",
            )

    def draw_wavelet_plot(self) -> None:
        if not self.file_loaded or not self.ae_data:
            self.show_message(
                "Ошибка",
                "Сначала загрузите CAMAC архив.",
                QMessageBox.Warning,
            )
            return

        if self.combo_wavelet_scope is None:
            return

        scope = self.combo_wavelet_scope.currentData()

        if scope == "all":
            self.draw_wavelet_all_events()
        else:
            self.draw_wavelet_current_event()

    def draw_wavelet_current_event(self) -> None:
        if not self.file_loaded or not self.ae_data:
            self.show_message(
                "Ошибка",
                "Сначала загрузите CAMAC архив.",
                QMessageBox.Warning,
            )
            return

        try:
            import pywt
        except ImportError:
            self.show_message(
                "Ошибка",
                (
                    "PyWavelets не установлен.\n\n"
                    "Установите его командой:\n"
                    "pip install PyWavelets"
                ),
                QMessageBox.Warning,
            )
            return

        if self.pw_wavelet is None:
            return

        event_index = self.current_index

        if event_index < 0 or event_index >= self.num_pulses:
            return

        channel = self.combo_wavelet_channel.currentData()
        wavelet_name = self.combo_wavelet_name.currentData()

        try:
            min_freq = float(self.input_wavelet_min_freq.text().strip())
            max_freq = float(self.input_wavelet_max_freq.text().strip())
        except ValueError:
            self.show_message(
                "Ошибка",
                "Минимальная и максимальная частота должны быть числами.",
                QMessageBox.Warning,
            )
            return

        if min_freq <= 0 or max_freq <= 0 or min_freq >= max_freq:
            self.show_message(
                "Ошибка",
                "Проверьте диапазон частот: min должен быть > 0 и меньше max.",
                QMessageBox.Warning,
            )
            return

        if channel == "ae":
            signal = np.asarray(self.ae_data[event_index], dtype=float)
            channel_title = "АЭ"
        else:
            signal = np.asarray(self.eme_data[event_index], dtype=float)
            channel_title = "ЭМЭ"

        if len(signal) < 10:
            self.show_message(
                "Ошибка",
                "Сигнал слишком короткий для вейвлет-анализа.",
                QMessageBox.Warning,
            )
            return

        sample_period_seconds = 500e-9

        signal = signal - np.mean(signal)

        frequencies = np.linspace(min_freq, max_freq, 128)

        try:
            central_frequency = pywt.central_frequency(wavelet_name)
            scales = central_frequency / (frequencies * sample_period_seconds)

            coefficients, calculated_frequencies = pywt.cwt(
                signal,
                scales,
                wavelet_name,
                sampling_period=sample_period_seconds,
            )

        except Exception as error:
            self.show_message(
                "Ошибка вейвлет-анализа",
                f"Не удалось построить вейвлет.\n\nОшибка: {repr(error)}",
                QMessageBox.Warning,
            )
            return

        amplitude = np.abs(coefficients)
        amplitude = np.log10(amplitude + 1e-12)

        time_ms = np.arange(len(signal)) * 0.5 / 1000.0

        self.last_wavelet_amplitude = amplitude
        self.last_wavelet_time_ms = time_ms
        self.last_wavelet_frequencies = calculated_frequencies
        self.last_wavelet_channel_title = channel_title

        self.pw_wavelet.clear()

        image_item = pg.ImageItem()

        low_level = float(np.percentile(amplitude, 5))
        high_level = float(np.percentile(amplitude, 99))

        image_item.setImage(
            amplitude.T,
            levels=(low_level, high_level),
        )

        color_map = pg.colormap.get("viridis")
        image_item.setLookupTable(color_map.getLookupTable())

        time_min = float(time_ms[0])
        time_max = float(time_ms[-1])

        freq_min = float(np.min(calculated_frequencies))
        freq_max = float(np.max(calculated_frequencies))

        image_item.setRect(
            time_min,
            freq_min,
            time_max - time_min,
            freq_max - freq_min,
        )

        self.pw_wavelet.addItem(image_item)

        self.pw_wavelet.setTitle(
            f"Вейвлет-спектр {channel_title}, импульс {event_index + 1}"
        )
        self.pw_wavelet.setLabel("bottom", "Время", units="ms")
        self.pw_wavelet.setLabel("left", "Частота", units="Hz")

    def draw_wavelet_all_events(self) -> None:
        try:
            import pywt
        except ImportError:
            self.show_message(
                "Ошибка",
                (
                    "PyWavelets не установлен.\n\n"
                    "Установите его командой:\n"
                    "pip install PyWavelets"
                ),
                QMessageBox.Warning,
            )
            return

        channel = self.combo_wavelet_channel.currentData()
        wavelet_name = self.combo_wavelet_name.currentData()

        try:
            min_freq = float(self.input_wavelet_min_freq.text().strip())
            max_freq = float(self.input_wavelet_max_freq.text().strip())
        except ValueError:
            self.show_message(
                "Ошибка",
                "Минимальная и максимальная частота должны быть числами.",
                QMessageBox.Warning,
            )
            return

        if min_freq <= 0 or max_freq <= 0 or min_freq >= max_freq:
            self.show_message(
                "Ошибка",
                "Проверьте диапазон частот: min должен быть > 0 и меньше max.",
                QMessageBox.Warning,
            )
            return

        if channel == "ae":
            signals = self.ae_data
            channel_title = "АЭ"
        else:
            signals = self.eme_data
            channel_title = "ЭМЭ"

        if self.num_pulses > 300:
            confirmed = self.ask_confirmation(
                "Большой расчет",
                (
                    "Вейвлет для всех импульсов может занять время.\n\n"
                    f"Импульсов: {self.num_pulses}\n\n"
                    "Совет: сначала сделайте CUT на нужный диапазон.\n\n"
                    "Продолжить?"
                ),
                yes_text="Продолжить",
                no_text="Отмена",
            )

            if not confirmed:
                return
        sample_period_seconds = 500e-9

        # For all-events overview, use fewer frequency rows than for one signal.
        # This makes the calculation much faster.
        frequency_count = 64
        frequencies = np.linspace(min_freq, max_freq, frequency_count)

        try:
            central_frequency = pywt.central_frequency(wavelet_name)
            scales = central_frequency / (frequencies * sample_period_seconds)
            calculated_frequencies = (
                pywt.scale2frequency(wavelet_name, scales) / sample_period_seconds
            )
        except Exception as error:
            self.show_message(
                "Ошибка вейвлета",
                f"Не удалось подготовить scales.\n\nОшибка: {repr(error)}",
                QMessageBox.Warning,
            )
            return

        progress = QProgressDialog(
            (
                "Расчет вейвлета для всех импульсов...\n\n"
                f"Импульсов: {self.num_pulses}\n"
                "Это может занять некоторое время."
            ),
            "Отмена",
            0,
            self.num_pulses,
            self,
        )

        progress.setWindowTitle("Вейвлет")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumWidth(520)
        progress.setMinimumHeight(180)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)

        progress.show()
        QApplication.processEvents()

        columns = []

        try:
            for i, signal in enumerate(signals):
                if progress.wasCanceled():
                    progress.close()
                    return

                signal = np.asarray(signal, dtype=float)

                if len(signal) < 10:
                    column = np.zeros(len(frequencies), dtype=float)
                    columns.append(column)
                    progress.setValue(i + 1)
                    QApplication.processEvents()
                    continue

                signal = signal - np.mean(signal)

                # Downsample for all-events overview.
                # Original: ~3072 samples.
                # After step 4: ~768 samples.
                # This is enough for overview heatmap and much faster.
                downsample_step = 4
                signal = signal[::downsample_step]
                effective_sample_period = sample_period_seconds * downsample_step

                effective_scales = central_frequency / (
                    frequencies * effective_sample_period
                )

                coefficients, _ = pywt.cwt(
                    signal,
                    effective_scales,
                    wavelet_name,
                    sampling_period=effective_sample_period,
                )

                amplitude = np.abs(coefficients)

                # One value per frequency for this event.
                # Mean over time = frequency summary for one impulse.
                column = np.mean(amplitude, axis=1)
                columns.append(column)

                if i % 5 == 0:
                    progress.setValue(i + 1)
                    QApplication.processEvents()

            progress.setValue(self.num_pulses)
            QApplication.processEvents()
            progress.close()

        except Exception as error:
            progress.close()

            self.show_message(
                "Ошибка вейвлет-анализа",
                (
                    "Не удалось построить вейвлет для всех импульсов.\n\n"
                    f"Ошибка: {repr(error)}"
                ),
                QMessageBox.Warning,
            )
            return

        if not columns:
            self.show_message(
                "Ошибка",
                "Нет данных для построения вейвлета.",
                QMessageBox.Warning,
            )
            return

        amplitude_matrix = np.array(columns, dtype=float).T
        amplitude_matrix = np.log10(amplitude_matrix + 1e-12)

        self.last_wavelet_amplitude = amplitude_matrix
        self.last_wavelet_time_ms = None
        self.last_wavelet_frequencies = calculated_frequencies
        self.last_wavelet_channel_title = f"{channel_title}, все импульсы"

        self.pw_wavelet.clear()

        image_item = pg.ImageItem()

        low_level = float(np.percentile(amplitude_matrix, 5))
        high_level = float(np.percentile(amplitude_matrix, 99))

        image_item.setImage(
            amplitude_matrix.T,
            levels=(low_level, high_level),
        )

        color_map = pg.colormap.get("viridis")
        image_item.setLookupTable(color_map.getLookupTable())

        x_min = 1.0
        x_max = float(self.num_pulses)

        freq_min = float(np.min(calculated_frequencies))
        freq_max = float(np.max(calculated_frequencies))

        image_item.setRect(
            x_min,
            freq_min,
            x_max - x_min,
            freq_max - freq_min,
        )

        self.pw_wavelet.addItem(image_item)

        self.pw_wavelet.setTitle(
            f"Вейвлет-сводка {channel_title} для всех импульсов"
        )
        self.pw_wavelet.setLabel("bottom", "Номер импульса")
        self.pw_wavelet.setLabel("left", "Частота", units="Hz")
