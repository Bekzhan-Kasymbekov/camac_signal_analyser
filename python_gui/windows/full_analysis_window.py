"""
Главное окно CAMAC Signal Analyser.

Этот файл отвечает за:
- создание вкладок GUI;
- хранение текущего состояния загруженного архива;
- связь между кнопками/полями ввода и функциями анализа;
- отображение графиков и сообщений пользователю.

Важно:
- Пользовательские номера импульсов начинаются с 1.
- Индексы Python начинаются с 0.
- После CUT/delete текущие номера импульсов перенумеровываются,
  но original_event_indices хранит исходные индексы из полного архива.
"""

import os
from pathlib import Path

import numpy as np
import pyqtgraph as pg
import traceback
import pyqtgraph.exporters

from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
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
    QVBoxLayout,
    QWidget,
)

from constants import (
    DEFAULT_WAVELET_FREQUENCY_COUNT_ALL,
    DEFAULT_WAVELET_FREQUENCY_COUNT_SINGLE,
    DEFAULT_WAVELET_MAX_FREQ,
    DEFAULT_WAVELET_MIN_FREQ,
    SAMPLE_INTERVAL_MICROSECONDS,
    SAMPLE_INTERVAL_MILLISECONDS,
    SAMPLE_INTERVAL_SECONDS,
)

from ui.dialogs import ask_confirmation_dialog, show_message_dialog

from analysis.fft_analysis import compute_mean_fft_amplitude
from analysis.b_value import calculate_b_value_from_amplitudes
from analysis.wavelet_analysis import (
        compute_all_events_wavelet_summary,
        compute_current_event_wavelet,        
)
from analysis.signal_metrics import (
    calculate_energy,
    calculate_max_abs,
    calculate_power,
)
from analysis.statistical_values import (
    amplitudes_from_signals,
    calculate_d_values_by_windows,
    calculate_d_values_from_signals,
    calculate_gamma_value_from_amplitudes,
    calculate_gamma_values_by_windows,
    calculate_s_value_from_amplitudes,
    calculate_s_values_by_windows,
    calculate_tsallis_parameters_from_amplitudes,
    calculate_tsallis_q_values_by_windows,
)

from file_io.csv_exporters import (
    write_b_value_csv,
    write_catalog_csv,
    write_processed_event_csv,
    write_processed_signal_matrix_csv,
    write_raw_event_csv,
    write_wavelet_results_csv,
)

from workers.statistics_worker import StatisticsWorker

class FullAnalysisWindow(QMainWindow):
    """
    Главное окно приложения.

    Класс хранит текущее рабочее состояние архива:
    - ae_data / eme_data:
        текущий диапазон после CUT/delete;
    - original_ae_data / original_eme_data:
        копия обработанных сигналов сразу после загрузки, нужна для RESET;
    - original_event_indices:
        связь текущих импульсов с исходными индексами полного архива;
    - relative_seconds:
        относительное время импульсов в текущем диапазоне.

    GUI показывает номера импульсов с 1, но внутри Python используются индексы с 0.
    """
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

        # original_ae_data / original_eme_data:
        # копия обработанных сигналов сразу после загрузки файла.
        # Нужны для RESET.
        #
        # ae_data / eme_data:
        # текущий рабочий диапазон после CUT/delete.
        #
        # Настоящие RAW uint16 данные берутся из:
        # self.archive.ae_raw(index)
        # self.archive.eme_raw(index)
        self.original_ae_data = []
        self.original_eme_data = []
        self.ae_data = []
        self.eme_data = []

        # Хранит исходные индексы импульсов из полного архива.
        # Пример: после CUT 100–200 текущий импульс 1 соответствует исходному импульсу 100.
        # Внутри храним индексы Python с 0, поэтому при показе пользователю добавляем +1.
        self.original_event_indices = np.array([], dtype=int)
        self.relative_seconds = np.array([], dtype=float)
        self.original_archive_seconds = np.array([], dtype=float)
        self.ae_energy = np.array([], dtype=float)
        self.eme_energy = np.array([], dtype=float)

        self.combo_b_value_channel = None
        self.input_b_value_min_m = None
        self.lbl_b_value_result = None
        self.lbl_raw_header = None

        self.combo_wavelet_scope = None
        self.combo_wavelet_name = None
        self.input_wavelet_min_freq = None
        self.input_wavelet_max_freq = None

        self.pw_wavelet_ae = None
        self.pw_wavelet_eme = None

        self.last_wavelet_results = {}

        self.statistics_thread = None
        self.statistics_worker = None
        self.statistics_progress = None

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
    def get_default_export_dir(self) -> Path:
        """
        Возвращает папку exports в корне проекта.

        Если папка exports недоступна, используется домашняя папка пользователя.
        """
        try:
            project_root = Path(__file__).resolve().parents[2]
            export_dir = project_root / "exports"
            export_dir.mkdir(parents=True, exist_ok=True)
            return export_dir

        except Exception as error:
            fallback_dir = Path.home() / "camac_signal_analyser_exports"
            fallback_dir.mkdir(parents=True, exist_ok=True)

            print(
                "Warning: could not use project exports folder. "
                f"Using fallback export folder: {fallback_dir}. "
                f"Original error: {repr(error)}"
            )

            return fallback_dir

    def get_current_event_filename_numbers(self) -> tuple[int, int]:
        """
        Returns:
            event_number: current number in edited/current catalog, 1-based
            original_event_number: original number in archive, 1-based
        """
        if self.num_pulses <= 0:
            return 0, 0

        event_number = int(self.current_index + 1)
        original_event_number = int(self.get_original_event_number(self.current_index))

        return event_number, original_event_number

    def make_image_export_name(
        self,
        plot_type: str,
        suffix: str = ".png",
        scope: str = "range",
    ) -> str:
        """
        Creates clean English image export filenames.

        scope:
            "single_event" -> archive_plot_type_event_N_original_M.png
            "range"        -> archive_plot_type_range_A-B.png
        """
        archive_stem = self.get_archive_stem_for_filename()
        plot_type = self.sanitize_filename_part(plot_type).lower()

        if scope == "single_event":
            event_number, original_event_number = self.get_current_event_filename_numbers()

            return (
                f"{archive_stem}_"
                f"{plot_type}_"
                f"event_{event_number}_"
                f"original_{original_event_number}"
                f"{suffix}"
            )

        range_label = self.get_current_range_label_for_filename()

        return (
            f"{archive_stem}_"
            f"{plot_type}_"
            f"{range_label}"
            f"{suffix}"
        )

    def get_english_plot_export_info(self, plot_widget) -> tuple[str, str]:
        """
        Returns:
            plot_type: clean English plot name
            scope: "single_event" or "range"
        """

        if hasattr(self, "plot_widget1") and plot_widget is self.plot_widget1:
            plot_type = self.combo_accumulation_plot_type.currentData()

            if plot_type == "count_time":
                return "signal_count_accumulation_time", "range"

            if plot_type == "energy_time":
                return "energy_accumulation_time", "range"

            return "energy_accumulation_event_numbers", "range"

        if hasattr(self, "pw_ae_time") and plot_widget is self.pw_ae_time:
            return "ae_waveform", "single_event"

        if hasattr(self, "pw_eme_time") and plot_widget is self.pw_eme_time:
            return "eme_waveform", "single_event"

        if hasattr(self, "pw_ae_fft") and plot_widget is self.pw_ae_fft:
            return "ae_fft", "single_event"

        if hasattr(self, "pw_eme_fft") and plot_widget is self.pw_eme_fft:
            return "eme_fft", "single_event"

        if hasattr(self, "pw_fft_summary") and plot_widget is self.pw_fft_summary:
            return "fft_summary", "range"

        if hasattr(self, "pw_d_value") and plot_widget is self.pw_d_value:
            return "d_value", "range"

        if hasattr(self, "pw_s_value") and plot_widget is self.pw_s_value:
            return "s_value", "range"

        if hasattr(self, "pw_gamma_value") and plot_widget is self.pw_gamma_value:
            return "gamma_value", "range"

        if hasattr(self, "pw_tsallis_q") and plot_widget is self.pw_tsallis_q:
            return "tsallis_q", "range"

        if hasattr(self, "pw_b_value") and plot_widget is self.pw_b_value:
            return "b_value", "range"

        if hasattr(self, "pw_wavelet_ae") and plot_widget is self.pw_wavelet_ae:
            if getattr(self, "last_wavelet_results", {}).get("mode") == "current":
                return "ae_wavelet", "single_event"
            return "ae_wavelet", "range"

        if hasattr(self, "pw_wavelet_eme") and plot_widget is self.pw_wavelet_eme:
            if getattr(self, "last_wavelet_results", {}).get("mode") == "current":
                return "eme_wavelet", "single_event"
            return "eme_wavelet", "range"

        return "plot", "range"

    def sanitize_filename_part(self, text: str) -> str:
        """
        Делает безопасную часть имени файла.

        Убирает символы, которые неудобны в Windows/Linux/macOS:
        / \ : * ? " < > | и лишние пробелы.
        """
        text = str(text).strip()

        replacements = {
            "/": "_",
            "\\": "_",
            ":": "_",
            "*": "_",
            "?": "_",
            '"': "",
            "<": "_",
            ">": "_",
            "|": "_",
            "\n": "_",
            "\r": "_",
            "\t": "_",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        text = "_".join(text.split())

        while "__" in text:
            text = text.replace("__", "_")

        return text.strip("_") or "unnamed"

    def get_archive_stem_for_filename(self) -> str:
        """
        Возвращает безопасное имя архива без расширения.
        """
        if not self.current_file_name or self.current_file_name == "Файл не выбран":
            return "camac_archive"

        return self.sanitize_filename_part(Path(self.current_file_name).stem)

    def get_current_range_label_for_filename(self) -> str:
        """
        Возвращает подпись текущего диапазона по исходным номерам импульсов.

        Пример:
            range_1-1988
            range_50-120
        """
        if self.num_pulses <= 0:
            return "range_empty"

        first_original = self.get_original_event_number(0)
        last_original = self.get_original_event_number(self.num_pulses - 1)

        return f"range_{first_original}-{last_original}"

    def make_default_export_name(
        self,
        export_type: str,
        suffix: str,
        extra: str | None = None,
    ) -> str:
        """
        Формирует стандартное имя файла экспорта.

        Пример:
            archive_range_50-120_processed_signal_matrix_AE.csv
        """
        archive_stem = self.get_archive_stem_for_filename()
        range_label = self.get_current_range_label_for_filename()
        export_type = self.sanitize_filename_part(export_type)

        parts = [
            archive_stem,
            range_label,
            export_type,
        ]

        if extra:
            parts.append(self.sanitize_filename_part(extra))

        return "_".join(parts) + suffix
 
    def make_default_single_event_export_name(
        self,
        export_type: str,
        suffix: str,
        event_number: int,
        original_event_number: int,
    ) -> str:
        """
        Формирует имя файла для экспорта одного импульса.

        В отличие от экспорта диапазона, здесь не нужен range_...
        Достаточно:
        - имя исходного архива;
        - тип экспорта;
        - текущий номер импульса;
        - исходный номер импульса.

        Пример:
            190723_processed_event_7_original_56.csv
            190723_raw_event_7_original_56.csv
        """
        archive_stem = self.get_archive_stem_for_filename()
        export_type = self.sanitize_filename_part(export_type)

        return (
            f"{archive_stem}_"
            f"{export_type}_"
            f"event_{event_number}_"
            f"original_{original_event_number}"
            f"{suffix}"
        )

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

        if not self.plot_has_exportable_data(plot_widget):
            self.show_message(
                "Ошибка экспорта",
                "На выбранном графике нет данных для экспорта.",
                QMessageBox.Warning,
            )
            return

        plot_type, scope = self.get_english_plot_export_info(plot_widget)

        default_name = self.make_image_export_name(
            plot_type=plot_type,
            suffix=".png",
            scope=scope,
        )

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Сохранить график как изображение",
            str(self.get_default_export_dir() / default_name),
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

    def plot_has_exportable_data(self, plot_widget: pg.PlotWidget) -> bool:
        """
        Проверяет, есть ли на графике данные для экспорта.

        Обычные графики PyQtGraph хранят линии как DataItem.
        Вейвлет-графики используют ImageItem, поэтому listDataItems()
        для них может быть пустым, хотя изображение на графике есть.
        """
        if len(plot_widget.plotItem.listDataItems()) > 0:
            return True

        for item in plot_widget.plotItem.items:
            if isinstance(item, pg.ImageItem):
                return True

        return False

    def toggle_ui_state(self, enabled: bool) -> None:
        self.btn_max.setEnabled(enabled)
        self.input_max.setEnabled(enabled)
        self.btn_min.setEnabled(enabled)
        self.input_min.setEnabled(enabled)
        self.btn_cut.setEnabled(enabled)
        self.btn_reset.setEnabled(enabled)
        self.combo_accumulation_plot_type.setEnabled(enabled)

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

    def get_original_event_number(self, event_index: int) -> int:
        """
        Возвращает исходный номер импульса для текущего индекса.

        event_index:
            индекс текущего рабочего диапазона, начиная с 0.

        Возвращаемое значение:
            пользовательский номер исходного импульса, начиная с 1.

        Пример:
            после CUT 100–200 текущий импульс 1 имеет event_index = 0,
            но исходный номер импульса должен быть 100.
        """
        if event_index < len(self.original_event_indices):
            return int(self.original_event_indices[event_index]) + 1

        return event_index + 1


    def get_original_event_index(self, event_index: int) -> int:
        """
        Возвращает исходный индекс импульса в полном архиве.

        Используется для доступа к настоящим RAW данным:
            self.archive.ae_raw(original_event_index)
            self.archive.eme_raw(original_event_index)

        Важно:
            это Python-индекс, поэтому он начинается с 0.
        """
        if event_index < len(self.original_event_indices):
            return int(self.original_event_indices[event_index])

        return event_index


    def get_relative_time(self, event_index: int) -> float:
        """
        Возвращает относительное время импульса в текущем рабочем диапазоне.

        Если время недоступно или индекс вне массива времени, возвращает 0.0.
        """
        if event_index < len(self.relative_seconds):
            return float(self.relative_seconds[event_index])

        return 0.0

    def get_original_archive_time_seconds(self, event_index: int) -> float:
        """
        Возвращает время импульса в эксперименте для текущего event_index.

        Используется для матричного экспорта обработанных сигналов:
        первая строка CSV = время каждого импульса.

        После CUT/delete event_index относится к текущему диапазону,
        поэтому сначала переводим его в исходный индекс архива.
        """
        original_event_index = self.get_original_event_index(event_index)

        if (
            original_event_index >= 0
            and original_event_index < len(self.original_archive_seconds)
        ):
            return float(self.original_archive_seconds[original_event_index])

        return self.get_relative_time(event_index)

    def get_current_archive_time_values(self) -> np.ndarray:
        """
        Возвращает времена всех импульсов текущего рабочего диапазона.

        Длина массива равна self.num_pulses.
        """
        return np.array(
            [
                self.get_original_archive_time_seconds(event_index)
                for event_index in range(self.num_pulses)
            ],
            dtype=float,
        )

    def calculate_total_energies(self) -> tuple[float, float]:
        """
        Возвращает сумму энергий всех импульсов текущего рабочего диапазона.

        После CUT/delete считаются только оставшиеся импульсы.
        RESET восстанавливает полный диапазон.
        """
        total_ae_energy = sum(
            calculate_energy(signal)
            for signal in self.ae_data
        )

        total_eme_energy = sum(
            calculate_energy(signal)
            for signal in self.eme_data
        )

        return float(total_ae_energy), float(total_eme_energy)
 
    def get_accumulation_x_axis_mode(self) -> str:
        """
        Возвращает режим оси X для окна 1.

        count_time   -> время
        energy_time  -> время
        energy_number -> номер импульса
        """
        plot_type = self.combo_accumulation_plot_type.currentData()

        if plot_type in ["count_time", "energy_time"]:
            return "relative_time"

        return "event_number"

    def on_accumulation_plot_type_changed(self) -> None:
        if not self.file_loaded:
            return

        x_axis_mode = self.get_accumulation_x_axis_mode()

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
        """
        Обрезает текущий рабочий диапазон по индексам Python.

        Диапазон задается как:
            [start_index, end_index_exclusive)

        Пользователь вводит номера импульсов с 1, но сюда передаются индексы с 0.

        После обрезки:
        - ae_data / eme_data становятся короче;
        - original_event_indices тоже обрезается, чтобы сохранить связь с исходным архивом;
        - relative_seconds пересчитывается от нуля для нового диапазона.
        """
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

        if self.get_accumulation_x_axis_mode() == "relative_time":
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
        self.clear_statistics_plots()
        self.update_fft_summary_plot()

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
        show_message_dialog(
            self,
            title,
            text,
            icon,
            details,
        )

    def ask_confirmation(
        self,
        title: str,
        text: str,
        yes_text: str = "Да",
        no_text: str = "Нет",
    ) -> bool:
        return ask_confirmation_dialog(
            self,
            title,
            text,
            yes_text,
            no_text,
        )
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
        left_panel.addWidget(QLabel("<b>Тип графика / режим обрезки:</b>"))

        self.combo_accumulation_plot_type = QComboBox()

        self.combo_accumulation_plot_type.addItem(
            "Накопление количества импульсов во времени",
            "count_time",
        )

        self.combo_accumulation_plot_type.addItem(
            "Накопление энергии АЭ/ЭМЭ во времени",
            "energy_time",
        )

        self.combo_accumulation_plot_type.addItem(
            "Накопление энергии АЭ/ЭМЭ по номерам импульсов",
            "energy_number",
        )

        self.combo_accumulation_plot_type.currentIndexChanged.connect(
            self.on_accumulation_plot_type_changed
        )

        left_panel.addWidget(self.combo_accumulation_plot_type)

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
            title="Окно 1: Накопление энергии АЭ и ЭМЕ"
        )
        self.setup_graph_context_menu(self.plot_widget1)
        self.plot_widget1.setLabel("left", "Накопленная энергия")
        self.plot_widget1.addLegend()
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
        self.pw_fft_summary = pg.PlotWidget(
            title="Сводная АЧХ / FFT для всех импульсов"
        )

        self.pw_ae_time.setLabel("bottom", "Время", units="us")
        self.pw_eme_time.setLabel("bottom", "Время", units="us")
        self.pw_ae_fft.setLabel("bottom", "Частота", units="Hz")
        self.pw_eme_fft.setLabel("bottom", "Частота", units="Hz")

        self.pw_ae_time.setLabel("left", "Амплитуда")
        self.pw_eme_time.setLabel("left", "Амплитуда")
        self.pw_ae_fft.setLabel("left", "Амплитуда")
        self.pw_eme_fft.setLabel("left", "Амплитуда")

        self.pw_fft_summary.setLabel("bottom", "Частота", units="Hz")
        self.pw_fft_summary.setLabel("left", "Средняя амплитуда FFT")
        self.pw_fft_summary.addLegend()

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

        self.setup_graph_context_menu(self.pw_fft_summary)
        self.pw_fft_summary.showGrid(x=True, y=True)
        grid_layout.addWidget(self.pw_fft_summary, 2, 0, 1, 2)

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
            "<b>Max abs ЭМЭ:</b> —<br><br>"
            "<b>Сумма энергий АЭ:</b> —<br>"
            "<b>Сумма энергий ЭМЭ:</b> —"
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

        self.pw_d_value = pg.PlotWidget(title="d-value")
        self.pw_s_value = pg.PlotWidget(title="S-value")
        self.pw_gamma_value = pg.PlotWidget(title="γ-value")
        self.pw_tsallis_q = pg.PlotWidget(title="Параметр Тсаллиса q")

        self.stat_plots = [
            self.pw_d_value,
            self.pw_s_value,
            self.pw_gamma_value,
            self.pw_tsallis_q,
        ]
        
        for i, plot_widget in enumerate(self.stat_plots):
            self.setup_graph_context_menu(plot_widget)
            plot_widget.showGrid(x=True, y=True)
            plot_widget.addLegend()
            plot_widget.setLabel("bottom", "Номер импульса")
            grid_layout.addWidget(plot_widget, i // 2, i % 2)

        self.pw_d_value.setLabel("left", "d-value")
        self.pw_s_value.setLabel("left", "S-value")
        self.pw_gamma_value.setLabel("left", "γ")
        self.pw_tsallis_q.setLabel("left", "q")

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

        if self.statistics_thread is not None:
            self.show_message(
                "Статистика",
                "Расчет статистики уже выполняется. Дождитесь завершения.",
                QMessageBox.Warning,
            )
            return

        if self.radio_single_signal.isChecked():
            self.start_statistics_worker(
                mode="single",
                window_size=None,
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

        self.start_statistics_worker(
            mode="window",
            window_size=window_size,
        )

    def start_statistics_worker(
        self,
        mode: str,
        window_size: int | None,
    ) -> None:
        """
        Запускает расчет окна 3 в отдельном QThread.

        Это нужно, чтобы тяжелые расчеты d-value и Tsallis q не блокировали
        основной GUI поток и не вызывали системное сообщение
        'python3 is not responding'.
        """
        progress_text = "Расчет статистических коэффициентов..."

        if mode == "window":
            progress_text = (
                "Расчет статистических коэффициентов по окнам...\n\n"
                f"Размер окна: {window_size}"
            )

        self.statistics_progress = QProgressDialog(
            progress_text,
            "",
            0,
            0,
            self,
        )
        self.statistics_progress.setWindowTitle("Окно 3: Статистика")
        self.statistics_progress.setWindowModality(Qt.WindowModal)
        self.statistics_progress.setMinimumWidth(520)
        self.statistics_progress.setMinimumDuration(0)
        self.statistics_progress.setCancelButton(None)
        self.statistics_progress.show()

        self.btn_calc_stats.setEnabled(False)

        self.statistics_thread = QThread(self)
        self.statistics_worker = StatisticsWorker(
            self.ae_data,
            self.eme_data,
            mode,
            window_size,
        )

        self.statistics_worker.moveToThread(self.statistics_thread)

        self.statistics_thread.started.connect(self.statistics_worker.run)
        self.statistics_worker.finished.connect(self.on_statistics_finished)
        self.statistics_worker.failed.connect(self.on_statistics_failed)

        self.statistics_worker.finished.connect(self.statistics_thread.quit)
        self.statistics_worker.failed.connect(self.statistics_thread.quit)

        self.statistics_thread.finished.connect(self.statistics_worker.deleteLater)
        self.statistics_thread.finished.connect(self.statistics_thread.deleteLater)
        self.statistics_thread.finished.connect(self.cleanup_statistics_worker)

        self.statistics_thread.start()

    def cleanup_statistics_worker(self) -> None:
        """
        Очищает ссылки после завершения фонового расчета.
        """
        self.statistics_thread = None
        self.statistics_worker = None

        if self.statistics_progress is not None:
            self.statistics_progress.close()
            self.statistics_progress = None

        self.btn_calc_stats.setEnabled(True)

    def on_statistics_failed(self, error_text: str) -> None:
        self.show_message(
            "Ошибка статистики",
            "Не удалось рассчитать статистические коэффициенты.",
            QMessageBox.Critical,
            details=error_text,
        )

    def on_statistics_finished(self, result: dict) -> None:
        if result["mode"] == "single":
            self.draw_statistics_single_result(result)
        else:
            self.draw_statistics_window_result(result)

        self.show_message(
            "Статистика",
            "Расчет статистических коэффициентов выполнен.",
            QMessageBox.Information,
        )
        # ================= TAB 4: WAVELETS =================

    def init_tab4(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(
            QLabel("<b>Окно 4: Вейвлет-скалограммы АЭ и ЭМЭ</b>")
        )

        controls_layout = QHBoxLayout()

        controls_layout.addWidget(QLabel("Режим:"))

        self.combo_wavelet_scope = QComboBox()
        self.combo_wavelet_scope.addItem("Текущий импульс", "current")
        self.combo_wavelet_scope.addItem("Все импульсы", "all")
        controls_layout.addWidget(self.combo_wavelet_scope)

        controls_layout.addWidget(QLabel("Вейвлет:"))

        self.combo_wavelet_name = QComboBox()
        self.combo_wavelet_name.addItem("cmor1.5-1.0", "cmor1.5-1.0")
        self.combo_wavelet_name.addItem("morl", "morl")
        controls_layout.addWidget(self.combo_wavelet_name)

        controls_layout.addWidget(QLabel("Мин. частота, Hz:"))

        self.input_wavelet_min_freq = QLineEdit()
        self.input_wavelet_min_freq.setText(str(DEFAULT_WAVELET_MIN_FREQ))
        self.input_wavelet_min_freq.setFixedWidth(100)
        controls_layout.addWidget(self.input_wavelet_min_freq)

        controls_layout.addWidget(QLabel("Макс. частота, Hz:"))

        self.input_wavelet_max_freq = QLineEdit()
        self.input_wavelet_max_freq.setText(str(DEFAULT_WAVELET_MAX_FREQ))
        self.input_wavelet_max_freq.setFixedWidth(100)
        controls_layout.addWidget(self.input_wavelet_max_freq)

        self.btn_draw_wavelet = QPushButton("Построить вейвлеты")
        self.btn_draw_wavelet.clicked.connect(self.draw_wavelet_plot)
        controls_layout.addWidget(self.btn_draw_wavelet)

        self.btn_export_wavelet = QPushButton("Экспорт вейвлетов CSV...")
        self.btn_export_wavelet.clicked.connect(self.export_wavelet_csv)
        controls_layout.addWidget(self.btn_export_wavelet)

        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        wavelet_grid = QGridLayout()

        self.pw_wavelet_ae = pg.PlotWidget(title="Вейвлет-скалограмма АЭ")
        self.pw_wavelet_eme = pg.PlotWidget(title="Вейвлет-скалограмма ЭМЭ")

        for row_index, plot_widget in enumerate(
            [self.pw_wavelet_ae, self.pw_wavelet_eme]
        ):
            self.setup_graph_context_menu(plot_widget)
            plot_widget.showGrid(x=True, y=True)
            plot_widget.setLabel("bottom", "Время", units="ms")
            plot_widget.setLabel("left", "Частота", units="Hz")
            wavelet_grid.addWidget(plot_widget, row_index, 0)

        layout.addLayout(wavelet_grid)

        layout.addWidget(
            QLabel(
                "<i>В режиме текущего импульса строятся две полные скалограммы: "
                "АЭ и ЭМЭ. В режиме всех импульсов строятся две сводные "
                "вейвлет-карты по текущему рабочему диапазону.</i>"
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

        btn_save_catalog = QPushButton("Экспортировать каталог текущего диапазона в CSV...")
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

        btn_export_range_folder = QPushButton("Экспортировать текущий диапазон отдельными файлами в папку...")
        btn_export_range_folder.setMinimumHeight(40)
        btn_export_range_folder.clicked.connect(self.export_current_range_folder)
        layout_data.addWidget(btn_export_range_folder)

        btn_export_signal_matrices = QPushButton(
            "Экспортировать матрицу обработанных сигналов АЭ/ЭМЭ в CSV..."
        )
        btn_export_signal_matrices.setMinimumHeight(40)
        btn_export_signal_matrices.clicked.connect(
            self.export_processed_signal_matrices
        )
        layout_data.addWidget(btn_export_signal_matrices)

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
            str(
                self.get_default_export_dir() 
                / self.make_default_export_name("catalog_summary", ".csv")
            )
        )

        if not file_path:
            return

        output_path = Path(file_path)

        if output_path.suffix == "":
            output_path = output_path.with_suffix(".csv")

        try:
            original_event_numbers = [
                self.get_original_event_number(i)
                for i in range(self.num_pulses)
            ]

            relative_seconds_values = [
                self.get_relative_time(i)
                for i in range(self.num_pulses)
            ]

            write_catalog_csv(
                output_path,
                self.ae_data,
                self.eme_data,
                original_event_numbers,
                relative_seconds_values,
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
        original_event_number = self.get_original_event_number(event_index)

        default_name = self.make_default_single_event_export_name(
            "processed",
            ".csv",
            event_number,
            original_event_number,
        )

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить текущий импульс",
            str(self.get_default_export_dir() / default_name),
            "CSV files (*.csv);;Text files (*.txt);;All files (*.*)",
        )

        if not file_path:
            return

        output_path = Path(file_path)

        if output_path.suffix == "":
            output_path = output_path.with_suffix(".csv")

        try:
            write_processed_event_csv(
                output_path,
                self.ae_data[event_index],
                self.eme_data[event_index],
                SAMPLE_INTERVAL_MICROSECONDS,
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

        event_number = event_index + 1
        original_event_number = self.get_original_event_number(event_index)
        original_event_index = self.get_original_event_index(event_index)

        default_name = self.make_default_single_event_export_name(
            "raw",
            ".csv",
            event_number,
            original_event_number,
        )

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить RAW данные текущего импульса",
            str(self.get_default_export_dir() / default_name),
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

            write_raw_event_csv(
                output_path,
                ae_raw,
                eme_raw,
                SAMPLE_INTERVAL_MICROSECONDS,
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
            confirmed = self.ask_confirmation(
                "Большой экспорт",
                (
                    "Вы собираетесь экспортировать большой диапазон.\n\n"
                    f"Импульсов: {self.num_pulses}\n"
                    f"Будет создано файлов: {estimated_files}\n\n"
                    "Продолжить?"
                ),
                yes_text="Продолжить",
                no_text="Отмена",
            )

            if not confirmed:
                return

        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для экспорта текущего диапазона",
            str(self.get_default_export_dir()),
        )

        if not folder_path:
            return

        output_folder = Path(folder_path)

        export_folder_name = self.make_default_export_name(
            "full_range_export",
            "",
        )

        export_folder = output_folder / export_folder_name
        export_folder.mkdir(parents=True, exist_ok=True)

        try:
            catalog_path = export_folder / self.make_default_export_name(
                "catalog_summary",
                ".csv",
            )

            original_event_numbers = [
                self.get_original_event_number(i)
                for i in range(self.num_pulses)
            ]

            relative_seconds_values = [
                self.get_relative_time(i)
                for i in range(self.num_pulses)
            ]

            write_catalog_csv(
                catalog_path,
                self.ae_data,
                self.eme_data,
                original_event_numbers,
                relative_seconds_values,
            )

            for i in range(self.num_pulses):
                event_number = i + 1
                original_event_number = self.get_original_event_number(i)

                processed_path = (
                    export_folder
                    / self.make_default_export_name(
                        "processed_event_signal",
                        ".csv",
                        f"event_{event_number}_original_{original_event_number}",
                    )
                )
                raw_path = (
                    export_folder
                    / self.make_default_export_name(
                        "raw_event_signal",
                        ".csv",
                        f"event_{event_number}_original_{original_event_number}",
                    )
                )

                write_processed_event_csv(
                    processed_path,
                    self.ae_data[i],
                    self.eme_data[i],
                    SAMPLE_INTERVAL_MICROSECONDS,
                )

                original_event_index = self.get_original_event_index(i)

                ae_raw = np.array(
                    self.archive.ae_raw(original_event_index),
                    dtype=np.uint16,
                )
                eme_raw = np.array(
                    self.archive.eme_raw(original_event_index),
                    dtype=np.uint16,
                )

                write_raw_event_csv(
                    raw_path,
                    ae_raw,
                    eme_raw,
                    SAMPLE_INTERVAL_MICROSECONDS,
                )

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

    def export_processed_signal_matrices(self) -> None:
        """
        Экспортирует текущий обработанный каталог сигналов в два CSV файла:

        1. <archive>_<range>_processed_signal_matrix_AE.csv
        2. <archive>_<range>_processed_signal_matrix_EME.csv

        Формат каждого файла:
            - столбцы = импульсы текущего диапазона;
            - первая строка = время импульса в эксперименте;
            - следующие строки = значения обработанного сигнала;
            - без metadata и без заголовков.

        После CUT/delete экспортируется только текущий рабочий диапазон.
        """
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
                "Нет обработанных сигналов для экспорта.",
                QMessageBox.Warning,
            )
            return

        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для экспорта обработанных сигналов",
            str(self.get_default_export_dir()),
        )

        if not folder_path:
            return

        output_folder = Path(folder_path)

        ae_output_path = output_folder / self.make_default_export_name(
            "processed_signal_matrix",
            ".csv",
            "AE",
        )

        eme_output_path = output_folder / self.make_default_export_name(
            "processed_signal_matrix",
            ".csv",
            "EME",
        )

        event_times_seconds = self.get_current_archive_time_values()

        event_numbers = np.arange(1, self.num_pulses + 1, dtype=int)

        original_event_numbers = np.array(
            [
                self.get_original_event_number(event_index)
                for event_index in range(self.num_pulses)
            ],
            dtype=int,
        )

        ae_max_len = max(len(signal) for signal in self.ae_data)
        eme_max_len = max(len(signal) for signal in self.eme_data)

        total_progress_rows = ae_max_len + 2 + eme_max_len + 2

        progress = QProgressDialog(
            (
                "Экспорт обработанных сигналов в CSV...\n\n"
                f"Импульсов: {self.num_pulses}\n"
                "Будут созданы два файла: AE и EME."
            ),
            "Отмена",
            0,
            total_progress_rows,
            self,
        )

        progress.setWindowTitle("Экспорт сигналов")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumWidth(560)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.show()
        QApplication.processEvents()

        exported_ae_rows = 0

        def ae_progress_callback(done_rows: int, total_rows: int) -> None:
            nonlocal exported_ae_rows

            exported_ae_rows = done_rows

            progress.setLabelText(
                (
                    "Экспорт обработанных сигналов АЭ...\n\n"
                    f"Строка {done_rows} / {total_rows}"
                )
            )
            progress.setValue(done_rows)
            QApplication.processEvents()

            if progress.wasCanceled():
                raise RuntimeError("Экспорт отменен пользователем.")

        def eme_progress_callback(done_rows: int, total_rows: int) -> None:
            progress.setLabelText(
                (
                    "Экспорт обработанных сигналов ЭМЭ...\n\n"
                    f"Строка {done_rows} / {total_rows}"
                )
            )
            progress.setValue(exported_ae_rows + done_rows)
            QApplication.processEvents()

            if progress.wasCanceled():
                raise RuntimeError("Экспорт отменен пользователем.")

        try:
            write_processed_signal_matrix_csv(
                ae_output_path,
                self.ae_data,
                event_times_seconds,
                event_numbers=event_numbers,
                original_event_numbers=original_event_numbers,
                progress_callback=ae_progress_callback,
            )

            write_processed_signal_matrix_csv(
                eme_output_path,
                self.eme_data,
                event_times_seconds,
                event_numbers=event_numbers,
                original_event_numbers=original_event_numbers,
                progress_callback=eme_progress_callback,
            )

        except Exception as error:
            progress.close()

            self.show_message(
                "Ошибка экспорта",
                (
                    "Не удалось экспортировать обработанные сигналы.\n\n"
                    f"Ошибка: {repr(error)}"
                ),
                QMessageBox.Critical,
                details=traceback.format_exc(),
            )
            return

        progress.setValue(total_progress_rows)
        QApplication.processEvents()
        progress.close()

        self.show_message(
            "Экспорт",
            (
                "Обработанные сигналы успешно экспортированы.\n\n"
                f"AE файл:\n{ae_output_path}\n\n"
                f"EME файл:\n{eme_output_path}\n\n"
                f"Импульсов: {self.num_pulses}\n"
                f"Строк AE: {ae_max_len + 2}\n"
                f"Строк EME: {eme_max_len + 2}"
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
            str(
                self.get_default_export_dir()
                / self.make_default_export_name("b_value_AE_EME", ".csv")
            ),
            "CSV files (*.csv);;Text files (*.txt);;All files (*.*)",
        )

        if not file_path:
            return

        output_path = Path(file_path)

        if output_path.suffix == "":
            output_path = output_path.with_suffix(".csv")

        try:
            write_b_value_csv(
                output_path,
                self.last_b_value_results,
                self.num_pulses,
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
        """
        Экспортирует последние построенные вейвлет-результаты.

        После обновления окна 4 экспорт сохраняет оба канала:
        - AE;
        - EME.

        Для текущего импульса:
            строки содержат channel, frequency_hz, time_ms, amplitude.

        Для всех импульсов:
            строки содержат channel, event_number, original_event_number,
            frequency_hz, amplitude.
        """
        if not self.last_wavelet_results:
            self.show_message(
                "Ошибка",
                "Сначала постройте вейвлеты.",
                QMessageBox.Warning,
            )
            return

        mode = self.last_wavelet_results.get("mode", "unknown")

        if mode == "current":
            event_number = self.last_wavelet_results.get("event_number", "")
            original_event_number = self.last_wavelet_results.get(
                "original_event_number",
                "",
            )
            extra = f"current_event_{event_number}_original_{original_event_number}"
        elif mode == "all_events":
            extra = "all_events_AE_EME"
        else:
            extra = "AE_EME"

        default_name = self.make_default_export_name(
            "wavelet_AE_EME",
            ".csv",
            extra,
        )

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить вейвлеты CSV",
            str(self.get_default_export_dir() / default_name),
            "CSV files (*.csv);;Text files (*.txt);;All files (*.*)",
        )

        if not file_path:
            return

        output_path = Path(file_path)

        if output_path.suffix == "":
            output_path = output_path.with_suffix(".csv")

        try:
            write_wavelet_results_csv(
                output_path,
                self.last_wavelet_results,
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

        mode = self.last_wavelet_results.get("mode", "unknown")
        channels = ", ".join(
            self.last_wavelet_results.get("channels", {}).keys()
        )

        self.show_message(
            "Экспорт",
            (
                "Вейвлет CSV успешно сохранен.\n\n"
                f"Файл:\n{output_path}\n"
                f"Режим: {mode}\n"
                f"Каналы: {channels}"
            ),
            QMessageBox.Information,
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
        """
        Открывает бинарный CAMAC архив через QFileDialog и загружает его через camac_core.

        camac_core сам определяет формат архива:
        - old_ae_header
        - new_channel_timestamps

        После загрузки:
        - сохраняется исходное количество импульсов;
        - создается рабочий диапазон ae_data / eme_data;
        - original_event_indices инициализируется как 0..N-1;
        - обновляются графики и элементы интерфейса.
        """

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

            self.original_ae_data = list(self.ae_data)
            self.original_eme_data = list(self.eme_data)

            self.relative_seconds = np.array(
                self.archive.relative_seconds(),
                dtype=float,
            )

            # Время эксперимента от начала архива.
            # Для экспорта обработанных сигналов удобнее использовать именно это время,
            # а не absolute_seconds(), потому что new format может содержать Unix-like timestamp.
            self.original_archive_seconds = np.array(
                self.archive.relative_seconds(),
                dtype=float,
            )

            if len(self.original_archive_seconds) != self.num_pulses:
                self.original_archive_seconds = np.arange(
                    self.num_pulses,
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

        self.on_accumulation_plot_type_changed()

        self.load_pulse(1)
        self.clear_statistics_plots()
        self.update_fft_summary_plot()

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
        """
        Загружает выбранный импульс в окно поимпульсного анализа.

        event_number:
            пользовательский номер импульса, начинается с 1.

        Функция:
        - переводит event_number в Python index;
        - рисует AE/EME сигналы;
        - строит FFT;
        - считает энергию, мощность и max abs;
        - показывает исходный номер импульса после CUT/delete;
        - показывает RAW header preview для проверки парсера.
        """
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

        ae_time_us = np.arange(len(ae_signal)) * SAMPLE_INTERVAL_MICROSECONDS
        eme_time_us = np.arange(len(eme_signal)) * SAMPLE_INTERVAL_MICROSECONDS

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

        sample_interval_seconds = SAMPLE_INTERVAL_SECONDS

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

        energy_ae = calculate_energy(ae_signal)
        energy_eme = calculate_energy(eme_signal)

        power_ae = calculate_power(ae_signal, SAMPLE_INTERVAL_SECONDS)
        power_eme = calculate_power(eme_signal, SAMPLE_INTERVAL_SECONDS)

        max_abs_ae = calculate_max_abs(ae_signal)
        max_abs_eme = calculate_max_abs(eme_signal)

        total_ae_energy, total_eme_energy = self.calculate_total_energies()

        relative_time = self.get_relative_time(event_index)
        original_event_number = self.get_original_event_number(event_index)

        self.lbl_stats.setText(
            f"<b>Текущий импульс:</b> {event_number}<br>"
            f"<b>Исходный номер:</b> {original_event_number}<br>"
            f"<b>Время архива:</b> {relative_time:.6f} с<br><br>"
            f"<b>Энергия АЭ:</b> {energy_ae:.2f} у.е.<br>"
            f"<b>Мощность АЭ:</b> {power_ae:.2f} у.е./с<br>"
            f"<b>Max abs АЭ:</b> {max_abs_ae:.2f}<br><br>"
            f"<b>Энергия ЭМЭ:</b> {energy_eme:.2f} у.е.<br>"
            f"<b>Мощность ЭМЭ:</b> {power_eme:.2f} у.е./с<br>"
            f"<b>Max abs ЭМЭ:</b> {max_abs_eme:.2f}<br><br>"
            f"<b>Сумма энергий АЭ:</b> {total_ae_energy:.2f} у.е.<br>"
            f"<b>Сумма энергий ЭМЭ:</b> {total_eme_energy:.2f} у.е."
        )

        if self.lbl_raw_header is not None and self.archive is not None:
            try:
                original_event_index = self.get_original_event_index(event_index)

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

        self.on_accumulation_plot_type_changed()

        self.load_pulse(next_event_number)
        self.clear_statistics_plots()
        self.update_fft_summary_plot()

    def update_fft_summary_plot(self) -> None:
        """
        Обновляет сводную АЧХ для всех импульсов текущего рабочего диапазона.

        После CUT/delete используются только оставшиеся импульсы.
        На одном графике отображаются средние FFT amplitude для АЭ и ЭМЭ.
        """
        self.pw_fft_summary.clear()

        if not self.file_loaded or not self.ae_data or not self.eme_data:
            return

        try:
            ae_freqs, ae_mean_fft = compute_mean_fft_amplitude(
                self.ae_data,
                SAMPLE_INTERVAL_SECONDS,
            )

            eme_freqs, eme_mean_fft = compute_mean_fft_amplitude(
                self.eme_data,
                SAMPLE_INTERVAL_SECONDS,
            )

        except Exception:
            return

        self.pw_fft_summary.plot(
            ae_freqs,
            ae_mean_fft,
            pen=pg.mkPen("b", width=2),
            name="АЭ",
        )

        self.pw_fft_summary.plot(
            eme_freqs,
            eme_mean_fft,
            pen=pg.mkPen("r", width=2),
            name="ЭМЭ",
        )

    def update_accumulation_plot(self) -> None:
        """
        Обновляет график накопления в окне 1.

        Режимы:
        1. Накопление количества импульсов во времени.
        2. Накопление энергии АЭ/ЭМЭ во времени.
        3. Накопление энергии АЭ/ЭМЭ по номерам импульсов.
        """
        self.plot_widget1.clear()

        if not self.file_loaded or not self.ae_data or not self.eme_data:
            self.plot_widget1.addItem(self.line_min)
            self.plot_widget1.addItem(self.line_max)
            return

        event_numbers = self.get_event_numbers()
        plot_type = self.combo_accumulation_plot_type.currentData()
        x_axis_mode = self.get_accumulation_x_axis_mode()

        if (
            x_axis_mode == "relative_time"
            and len(self.relative_seconds) == self.num_pulses
        ):
            x_values = self.relative_seconds
            self.plot_widget1.setLabel("bottom", "Время архива", units="s")
        else:
            x_values = event_numbers
            self.plot_widget1.setLabel("bottom", "Номер импульса")

        if plot_type == "count_time":
            cumulative_count = np.arange(1, self.num_pulses + 1, dtype=int)

            self.plot_widget1.setTitle(
                "Окно 1: Накопление количества импульсов во времени"
            )
            self.plot_widget1.setLabel("left", "Количество импульсов")

            self.plot_widget1.plot(
                x_values,
                cumulative_count,
                pen=pg.mkPen("k", width=2.5),
                name="Количество импульсов",
            )

        else:
            ae_energy = np.array(
                [calculate_energy(signal) for signal in self.ae_data],
                dtype=float,
            )

            eme_energy = np.array(
                [calculate_energy(signal) for signal in self.eme_data],
                dtype=float,
            )

            cumulative_ae_energy = np.cumsum(ae_energy)
            cumulative_eme_energy = np.cumsum(eme_energy)

            if plot_type == "energy_time":
                self.plot_widget1.setTitle(
                    "Окно 1: Накопление энергии АЭ и ЭМЭ во времени"
                )
            else:
                self.plot_widget1.setTitle(
                    "Окно 1: Накопление энергии АЭ и ЭМЭ по номерам импульсов"
                )

            self.plot_widget1.setLabel("left", "Накопленная энергия")

            self.plot_widget1.plot(
                x_values,
                cumulative_ae_energy,
                pen=pg.mkPen("b", width=2.5),
                name="АЭ",
            )

            self.plot_widget1.plot(
                x_values,
                cumulative_eme_energy,
                pen=pg.mkPen("r", width=2.5),
                name="ЭМЭ",
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

        x_axis_mode = self.get_accumulation_x_axis_mode()

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

        x_axis_mode = self.get_accumulation_x_axis_mode()

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

        x_axis_mode = self.get_accumulation_x_axis_mode()

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

        self.ae_data = list(self.original_ae_data)
        self.eme_data = list(self.original_eme_data)

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

        if self.get_accumulation_x_axis_mode() == "relative_time":
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
        self.clear_statistics_plots()
        self.update_fft_summary_plot()

        self.show_message(
            "RESET",
            f"Данные восстановлены. Импульсов: {self.num_pulses}",
            QMessageBox.Information,
        )

    def clear_statistics_plots(self) -> None:
        """
        Очищает графики окна 3 после загрузки, CUT/delete или RESET.

        Статистические коэффициенты могут считаться долго, особенно d-value
        и Tsallis q. Поэтому они пересчитываются только по кнопке
        "Рассчитать", а не автоматически при каждом изменении данных.
        """
        if not hasattr(self, "stat_plots"):
            return

        for plot_widget in self.stat_plots:
            plot_widget.clear()
            plot_widget.addLegend()
            plot_widget.setLabel("bottom", "Номер импульса")

        self.pw_d_value.setTitle("d-value")
        self.pw_s_value.setTitle("S-value")
        self.pw_gamma_value.setTitle("γ-value")
        self.pw_tsallis_q.setTitle("Параметр Тсаллиса q")

        self.pw_d_value.setLabel("left", "d")
        self.pw_s_value.setLabel("left", "S")
        self.pw_gamma_value.setLabel("left", "γ")
        self.pw_tsallis_q.setLabel("left", "q")

    def reset_statistics_plot_titles(self) -> None:
        self.pw_d_value.setTitle("d-value")
        self.pw_s_value.setTitle("S-value")
        self.pw_gamma_value.setTitle("γ-value")
        self.pw_tsallis_q.setTitle("Параметр Тсаллиса q")

        self.pw_d_value.setLabel("left", "d")
        self.pw_s_value.setLabel("left", "S")
        self.pw_gamma_value.setLabel("left", "γ")
        self.pw_tsallis_q.setLabel("left", "q")

        for plot_widget in self.stat_plots:
            plot_widget.setLabel("bottom", "Номер импульса")

    def clear_statistics_plot_items(self) -> None:
        self.pw_d_value.clear()
        self.pw_s_value.clear()
        self.pw_gamma_value.clear()
        self.pw_tsallis_q.clear()

        self.pw_d_value.addLegend()
        self.pw_s_value.addLegend()
        self.pw_gamma_value.addLegend()
        self.pw_tsallis_q.addLegend()

        self.reset_statistics_plot_titles()

    def draw_statistics_single_result(self, result: dict) -> None:
        x = result["x"]

        self.clear_statistics_plot_items()

        self.pw_d_value.plot(
            x,
            result["ae_d_values"],
            pen=pg.mkPen("b", width=1.5),
            name="АЭ",
        )
        self.pw_d_value.plot(
            x,
            result["eme_d_values"],
            pen=pg.mkPen("r", width=1.5),
            name="ЭМЭ",
        )

        self.pw_s_value.plot(
            x,
            np.full_like(x, result["ae_s_value"], dtype=float),
            pen=pg.mkPen("b", width=1.5),
            name=f"АЭ S={result['ae_s_value']:.4f}",
        )
        self.pw_s_value.plot(
            x,
            np.full_like(x, result["eme_s_value"], dtype=float),
            pen=pg.mkPen("r", width=1.5),
            name=f"ЭМЭ S={result['eme_s_value']:.4f}",
        )

        self.pw_gamma_value.plot(
            x,
            np.full_like(x, result["ae_gamma"], dtype=float),
            pen=pg.mkPen("b", width=1.5),
            name=f"АЭ γ={result['ae_gamma']:.4f}",
        )
        self.pw_gamma_value.plot(
            x,
            np.full_like(x, result["eme_gamma"], dtype=float),
            pen=pg.mkPen("r", width=1.5),
            name=f"ЭМЭ γ={result['eme_gamma']:.4f}",
        )

        if result["ae_q"] is not None:
            self.pw_tsallis_q.plot(
                x,
                np.full_like(x, result["ae_q"], dtype=float),
                pen=pg.mkPen("b", width=1.5),
                name=f"АЭ q={result['ae_q']:.4f}, a={result['ae_a']:.3e}",
            )

        if result["eme_q"] is not None:
            self.pw_tsallis_q.plot(
                x,
                np.full_like(x, result["eme_q"], dtype=float),
                pen=pg.mkPen("r", width=1.5),
                name=f"ЭМЭ q={result['eme_q']:.4f}, a={result['eme_a']:.3e}",
            )

        self.auto_range_stat_plots()

    def draw_statistics_window_result(self, result: dict) -> None:
        self.clear_statistics_plot_items()

        self.pw_d_value.plot(
            result["d_x_ae"],
            result["ae_d_windowed"],
            pen=pg.mkPen("b", width=1.5),
            name="АЭ",
        )
        self.pw_d_value.plot(
            result["d_x_eme"],
            result["eme_d_windowed"],
            pen=pg.mkPen("r", width=1.5),
            name="ЭМЭ",
        )

        self.pw_s_value.plot(
            result["s_x_ae"],
            result["ae_s_windowed"],
            pen=pg.mkPen("b", width=1.5),
            name="АЭ",
        )
        self.pw_s_value.plot(
            result["s_x_eme"],
            result["eme_s_windowed"],
            pen=pg.mkPen("r", width=1.5),
            name="ЭМЭ",
        )

        self.pw_gamma_value.plot(
            result["gamma_x_ae"],
            result["ae_gamma_windowed"],
            pen=pg.mkPen("b", width=1.5),
            name="АЭ",
        )
        self.pw_gamma_value.plot(
            result["gamma_x_eme"],
            result["eme_gamma_windowed"],
            pen=pg.mkPen("r", width=1.5),
            name="ЭМЭ",
        )

        self.pw_tsallis_q.plot(
            result["tsallis_x_ae"],
            result["ae_q_windowed"],
            pen=pg.mkPen("b", width=1.5),
            name="АЭ",
        )
        self.pw_tsallis_q.plot(
            result["tsallis_x_eme"],
            result["eme_q_windowed"],
            pen=pg.mkPen("r", width=1.5),
            name="ЭМЭ",
        )

        self.auto_range_stat_plots()

    def auto_range_stat_plots(self) -> None:
        for plot_widget in self.stat_plots:
            plot_widget.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)
            plot_widget.autoRange()

    def draw_b_value_plot(self) -> None:
        """
        Строит B-value по текущему рабочему диапазону.

        Для каждого импульса берется:
            max_abs = max(abs(signal))

        Затем считается условная магнитуда:
            M = log10(max_abs^2)

        И строится:
            log10(N >= M) = a - bM

        Если EME слишком слабый или после min M осталось мало событий,
        ошибка должна отображаться в label, а не ломать расчет AE.
        """
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
                ae_b, ae_a, ae_x, ae_y, ae_fit_x, ae_fit_y = calculate_b_value_from_amplitudes(
                ae_max_abs_values,
                min_magnitude,
)

                self.pw_b_value.plot(
                    ae_x,
                    ae_y,
                    pen=None,
                    symbol="o",
                    symbolSize=5,
                    name="AE selected points",
                )

                self.pw_b_value.plot(
                    ae_fit_x,
                    ae_fit_y,
                    pen=pg.mkPen("b", width=2),
                    name=f"AE linear fit, b={ae_b:.3f}",
                )

                result_lines.append(f"<b>AE b-value:</b> {ae_b:.4f}")

                ae_fit_y_for_all_points = np.full_like(ae_y, np.nan, dtype=float)

                for fit_index, fit_x_value in enumerate(ae_fit_x):
                    matching_indices = np.where(np.isclose(ae_x, fit_x_value))[0]

                    if len(matching_indices) > 0:
                        ae_fit_y_for_all_points[matching_indices[0]] = ae_fit_y[fit_index]

                self.last_b_value_results["AE"] = {
                    "b_value": ae_b,
                    "a_value": ae_a,
                    "x": ae_x,
                    "y": ae_y,
                    "fit_y": ae_fit_y_for_all_points,
                    "fit_x": ae_fit_x,
                    "fit_y_segment": ae_fit_y,
                    "min_magnitude": min_magnitude,
                }

            except Exception as error:
                error_lines.append(f"<b>AE:</b> {str(error)}")

        if channel_mode in ("both", "eme"):
            try:
                eme_b, eme_a, eme_x, eme_y, eme_fit_x, eme_fit_y = calculate_b_value_from_amplitudes(
                    eme_max_abs_values,
                    min_magnitude,
                )

                self.pw_b_value.plot(
                    eme_x,
                    eme_y,
                    pen=None,
                    symbol="x",
                    symbolSize=6,
                    name="EME selected points",
                )

                self.pw_b_value.plot(
                    eme_fit_x,
                    eme_fit_y,
                    pen=pg.mkPen("r", width=2),
                    name=f"EME linear fit, b={eme_b:.3f}",
                )

                result_lines.append(f"<b>EME b-value:</b> {eme_b:.4f}")

                eme_fit_y_for_all_points = np.full_like(eme_y, np.nan, dtype=float)

                for fit_index, fit_x_value in enumerate(eme_fit_x):
                    matching_indices = np.where(np.isclose(eme_x, fit_x_value))[0]

                    if len(matching_indices) > 0:
                        eme_fit_y_for_all_points[matching_indices[0]] = eme_fit_y[fit_index]

                self.last_b_value_results["EME"] = {
                    "b_value": eme_b,
                    "a_value": eme_a,
                    "x": eme_x,
                    "y": eme_y,
                    "fit_y": eme_fit_y_for_all_points,
                    "fit_x": eme_fit_x,
                    "fit_y_segment": eme_fit_y,
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

    def get_wavelet_settings(self) -> tuple[str, float, float] | None:
        """
        Читает настройки вейвлет-анализа из GUI.

        Возвращает:
            (wavelet_name, min_freq, max_freq)

        Если пользователь ввел некорректный диапазон частот,
        показывает сообщение и возвращает None.
        """
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
            return None

        if min_freq <= 0 or max_freq <= 0 or min_freq >= max_freq:
            self.show_message(
                "Ошибка",
                "Проверьте диапазон частот: min должен быть > 0 и меньше max.",
                QMessageBox.Warning,
            )
            return None

        return wavelet_name, min_freq, max_freq

    def draw_wavelet_image(
        self,
        plot_widget: pg.PlotWidget,
        amplitude_matrix: np.ndarray,
        x_values: np.ndarray,
        frequencies: np.ndarray,
        title: str,
        x_label: str,
        x_units: str | None = None,
    ) -> None:
        """
        Рисует одну вейвлет-карту в PlotWidget.

        amplitude_matrix:
            матрица log10 amplitude.
            Ось 0 = частота, ось 1 = время или номер импульса.

        x_values:
            либо время внутри импульса, либо номера импульсов.
        """
        plot_widget.clear()

        if amplitude_matrix.size == 0:
            return

        finite_values = amplitude_matrix[np.isfinite(amplitude_matrix)]

        if len(finite_values) == 0:
            return

        image_item = pg.ImageItem()

        low_level = float(np.percentile(finite_values, 5))
        high_level = float(np.percentile(finite_values, 99))

        if low_level == high_level:
            high_level = low_level + 1e-12

        image_item.setImage(
            amplitude_matrix.T,
            levels=(low_level, high_level),
        )

        color_map = pg.colormap.get("viridis")
        image_item.setLookupTable(color_map.getLookupTable())

        x_min = float(np.min(x_values))
        x_max = float(np.max(x_values))

        freq_min = float(np.min(frequencies))
        freq_max = float(np.max(frequencies))

        x_width = max(x_max - x_min, 1e-12)
        freq_width = max(freq_max - freq_min, 1e-12)

        image_item.setRect(
            x_min,
            freq_min,
            x_width,
            freq_width,
        )

        plot_widget.addItem(image_item)
        plot_widget.setTitle(title)
        plot_widget.setLabel("bottom", x_label, units=x_units)
        plot_widget.setLabel("left", "Частота", units="Hz")
        plot_widget.autoRange()

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
        """
        Строит две полные вейвлет-скалограммы текущего импульса:
        - АЭ;
        - ЭМЭ.

        Это соответствует требованию окна 4: два графических окна
        с вейвлет-скалограммами для АЭ и ЭМЭ.
        """
        if not self.file_loaded or not self.ae_data:
            self.show_message(
                "Ошибка",
                "Сначала загрузите CAMAC архив.",
                QMessageBox.Warning,
            )
            return

        if self.pw_wavelet_ae is None or self.pw_wavelet_eme is None:
            return

        event_index = self.current_index

        if event_index < 0 or event_index >= self.num_pulses:
            return

        settings = self.get_wavelet_settings()

        if settings is None:
            return

        wavelet_name, min_freq, max_freq = settings

        ae_signal = np.asarray(self.ae_data[event_index], dtype=float)
        eme_signal = np.asarray(self.eme_data[event_index], dtype=float)

        if len(ae_signal) < 10 or len(eme_signal) < 10:
            self.show_message(
                "Ошибка",
                "Сигнал слишком короткий для вейвлет-анализа.",
                QMessageBox.Warning,
            )
            return

        try:
            ae_amplitude, ae_time_ms, ae_frequencies = compute_current_event_wavelet(
                ae_signal,
                wavelet_name,
                min_freq,
                max_freq,
                SAMPLE_INTERVAL_SECONDS,
                DEFAULT_WAVELET_FREQUENCY_COUNT_SINGLE,
            )

            eme_amplitude, eme_time_ms, eme_frequencies = compute_current_event_wavelet(
                eme_signal,
                wavelet_name,
                min_freq,
                max_freq,
                SAMPLE_INTERVAL_SECONDS,
                DEFAULT_WAVELET_FREQUENCY_COUNT_SINGLE,
            )

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

        except Exception as error:
            self.show_message(
                "Ошибка вейвлет-анализа",
                f"Не удалось построить вейвлет.\n\nОшибка: {repr(error)}",
                QMessageBox.Warning,
            )
            return

        event_number = event_index + 1
        original_event_number = self.get_original_event_number(event_index)

        self.draw_wavelet_image(
            self.pw_wavelet_ae,
            ae_amplitude,
            ae_time_ms,
            ae_frequencies,
            (
                f"Вейвлет-скалограмма АЭ, импульс {event_number} "
                f"(исх. {original_event_number})"
            ),
            "Время",
            "ms",
        )

        self.draw_wavelet_image(
            self.pw_wavelet_eme,
            eme_amplitude,
            eme_time_ms,
            eme_frequencies,
            (
                f"Вейвлет-скалограмма ЭМЭ, импульс {event_number} "
                f"(исх. {original_event_number})"
            ),
            "Время",
            "ms",
        )

        self.last_wavelet_results = {
            "mode": "current",
            "event_number": event_number,
            "original_event_number": original_event_number,
            "channels": {
                "AE": {
                    "amplitude": ae_amplitude,
                    "time_ms": ae_time_ms,
                    "frequencies": ae_frequencies,
                },
                "EME": {
                    "amplitude": eme_amplitude,
                    "time_ms": eme_time_ms,
                    "frequencies": eme_frequencies,
                },
            },
        }

    def draw_wavelet_all_events(self) -> None:
        """
        Строит две вейвлет-сводки для всех импульсов текущего диапазона:
        - АЭ;
        - ЭМЭ.

        Для всех импульсов строится не полная скалограмма каждого события,
        а сводная карта:
        - каждый импульс становится одним вертикальным столбцом;
        - ось X = номер импульса;
        - ось Y = частота;
        - цвет = log10 средней wavelet amplitude по времени.
        """
        if not self.file_loaded or not self.ae_data or not self.eme_data:
            self.show_message(
                "Ошибка",
                "Сначала загрузите CAMAC архив.",
                QMessageBox.Warning,
            )
            return

        if self.pw_wavelet_ae is None or self.pw_wavelet_eme is None:
            return

        settings = self.get_wavelet_settings()

        if settings is None:
            return

        wavelet_name, min_freq, max_freq = settings

        if self.num_pulses > 300:
            confirmed = self.ask_confirmation(
                "Большой расчет",
                (
                    "Вейвлет для всех импульсов теперь считается для двух каналов: "
                    "АЭ и ЭМЭ.\n\n"
                    f"Импульсов: {self.num_pulses}\n"
                    f"Операций примерно: {self.num_pulses * 2}\n\n"
                    "Совет: сначала сделайте CUT на нужный диапазон.\n\n"
                    "Продолжить?"
                ),
                yes_text="Продолжить",
                no_text="Отмена",
            )

            if not confirmed:
                return

        progress = QProgressDialog(
            (
                "Расчет вейвлет-сводок для АЭ и ЭМЭ...\n\n"
                f"Импульсов: {self.num_pulses}\n"
                "Это может занять некоторое время."
            ),
            "Отмена",
            0,
            self.num_pulses * 2,
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

        def cancel_callback() -> bool:
            return progress.wasCanceled()

        def ae_progress_callback(done: int, total: int | None = None) -> None:
            if total is None:
                total = self.num_pulses

            progress.setLabelText(
                (
                    "Расчет вейвлет-сводки АЭ...\n\n"
                    f"{done} / {total}"
                )
            )
            progress.setValue(min(done, self.num_pulses))
            QApplication.processEvents()

        def eme_progress_callback(done: int, total: int | None = None) -> None:
            if total is None:
                total = self.num_pulses

            progress.setLabelText(
                (
                    "Расчет вейвлет-сводки ЭМЭ...\n\n"
                    f"{done} / {total}"
                )
            )
            progress.setValue(min(self.num_pulses + done, self.num_pulses * 2))
            QApplication.processEvents()

        try:
            ae_amplitude_matrix, ae_frequencies = compute_all_events_wavelet_summary(
                self.ae_data,
                wavelet_name,
                min_freq,
                max_freq,
                SAMPLE_INTERVAL_SECONDS,
                DEFAULT_WAVELET_FREQUENCY_COUNT_ALL,
                downsample_step=4,
                progress_callback=ae_progress_callback,
                cancel_callback=cancel_callback,
            )

            if progress.wasCanceled():
                progress.close()
                return

            eme_amplitude_matrix, eme_frequencies = compute_all_events_wavelet_summary(
                self.eme_data,
                wavelet_name,
                min_freq,
                max_freq,
                SAMPLE_INTERVAL_SECONDS,
                DEFAULT_WAVELET_FREQUENCY_COUNT_ALL,
                downsample_step=4,
                progress_callback=eme_progress_callback,
                cancel_callback=cancel_callback,
            )

        except ImportError:
            progress.close()
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

        except RuntimeError as error:
            progress.close()
            self.show_message(
                "Вейвлет-анализ",
                str(error),
                QMessageBox.Warning,
            )
            return

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

        progress.setValue(self.num_pulses * 2)
        QApplication.processEvents()
        progress.close()

        event_numbers = self.get_event_numbers()

        self.draw_wavelet_image(
            self.pw_wavelet_ae,
            ae_amplitude_matrix,
            event_numbers,
            ae_frequencies,
            "Вейвлет-сводка АЭ для всех импульсов",
            "Номер импульса",
            None,
        )

        self.draw_wavelet_image(
            self.pw_wavelet_eme,
            eme_amplitude_matrix,
            event_numbers,
            eme_frequencies,
            "Вейвлет-сводка ЭМЭ для всех импульсов",
            "Номер импульса",
            None,
        )

        original_event_numbers = np.array(
            [
                self.get_original_event_number(i)
                for i in range(self.num_pulses)
            ],
            dtype=int,
        )

        self.last_wavelet_results = {
            "mode": "all_events",
            "event_numbers": event_numbers,
            "original_event_numbers": original_event_numbers,
            "channels": {
                "AE": {
                    "amplitude": ae_amplitude_matrix,
                    "time_ms": None,
                    "frequencies": ae_frequencies,
                },
                "EME": {
                    "amplitude": eme_amplitude_matrix,
                    "time_ms": None,
                    "frequencies": eme_frequencies,
                },
            },
        }
