# python_gui/file_io/csv_exporters.py

"""
CSV экспорт для CAMAC Signal Analyser.

Этот модуль не должен открывать QFileDialog и не должен показывать QMessageBox.
GUI выбирает путь, проверяет состояние приложения и показывает сообщения.
Здесь находятся только функции записи CSV файлов.
"""

from pathlib import Path

from analysis.signal_metrics import calculate_energy, calculate_max_abs

import numpy as np


def write_processed_event_csv(
    output_path: Path,
    ae_signal: np.ndarray,
    eme_signal: np.ndarray,
    sample_interval_microseconds: float,
) -> None:
    """
    Сохраняет обработанные сигналы одного импульса в CSV.

    Обработанный сигнал означает сигнал после удаления среднего уровня.
    Это не настоящие RAW uint16 данные из бинарного файла.
    """
    max_length = max(len(ae_signal), len(eme_signal))

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(
            "sample_index,"
            "time_microseconds,"
            "ae_signal,"
            "eme_signal\n"
        )

        for sample_index in range(max_length):
            time_microseconds = sample_index * sample_interval_microseconds

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
    output_path: Path,
    ae_raw: np.ndarray,
    eme_raw: np.ndarray,
    sample_interval_microseconds: float,
) -> None:
    """
    Сохраняет настоящие RAW uint16 данные одного импульса в CSV.

    RAW данные берутся напрямую из архива:
        archive.ae_raw(original_event_index)
        archive.eme_raw(original_event_index)
    """
    max_length = max(len(ae_raw), len(eme_raw))

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(
            "sample_index,"
            "time_microseconds,"
            "ae_raw,"
            "eme_raw\n"
        )

        for sample_index in range(max_length):
            time_microseconds = sample_index * sample_interval_microseconds

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

def write_catalog_csv(
    output_path: Path,
    ae_data: list[np.ndarray],
    eme_data: list[np.ndarray],
    original_event_numbers: list[int],
    relative_seconds_values: list[float],
) -> None:
    """
    Сохраняет каталог текущего рабочего диапазона в CSV.

    GUI передает сюда уже подготовленные:
    - ae_data / eme_data текущего диапазона;
    - original_event_numbers для связи с исходным архивом;
    - relative_seconds_values для времени импульсов.

    Эта функция не знает ничего про QFileDialog, QMessageBox и состояние окна.
    """
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

        for i, (ae_signal, eme_signal) in enumerate(zip(ae_data, eme_data)):
            event_number = i + 1

            original_event_number = (
                original_event_numbers[i]
                if i < len(original_event_numbers)
                else event_number
            )

            relative_seconds = (
                relative_seconds_values[i]
                if i < len(relative_seconds_values)
                else 0.0
            )

            ae_max_abs = calculate_max_abs(ae_signal)
            eme_max_abs = calculate_max_abs(eme_signal)

            ae_energy = calculate_energy(ae_signal)
            eme_energy = calculate_energy(eme_signal)

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

def write_b_value_csv(
    output_path: Path,
    b_value_results: dict,
    event_count_total: int,
) -> None:
    """
    Сохраняет результаты b-value в CSV.

    GUI отвечает за расчет b-value и выбор файла.
    Эта функция только записывает готовые данные.
    """
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

        for channel_name, result in b_value_results.items():
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
                    f"{event_count_total},"
                    f"{point_index + 1},"
                    f"{float(x_values[point_index]):.6f},"
                    f"{float(y_values[point_index]):.6f},"
                    f"{float(fit_values[point_index]):.6f}\n"
                )

def write_wavelet_csv(
    output_path: Path,
    amplitude: np.ndarray,
    frequencies: np.ndarray,
    time_ms: np.ndarray | None,
    original_event_numbers: list[int] | None = None,
) -> None:
    """
    Сохраняет результат вейвлет-анализа в CSV.

    Если time_ms не None, экспортируется скалограмма одного импульса:
        frequency_hz, time_ms, log10_wavelet_amplitude

    Если time_ms is None, экспортируется сводка по всем импульсам:
        frequency_hz, event_number, original_event_number, log10_wavelet_amplitude
    """
    with open(output_path, "w", encoding="utf-8") as file:
        if time_ms is not None:
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

            return

        file.write(
            "frequency_hz,"
            "event_number,"
            "original_event_number,"
            "log10_wavelet_amplitude\n"
        )

        if original_event_numbers is None:
            original_event_numbers = []

        for freq_index in range(amplitude.shape[0]):
            frequency = float(frequencies[freq_index])

            for event_index in range(amplitude.shape[1]):
                event_number = event_index + 1

                original_event_number = (
                    original_event_numbers[event_index]
                    if event_index < len(original_event_numbers)
                    else event_number
                )

                file.write(
                    f"{frequency:.6f},"
                    f"{event_number},"
                    f"{original_event_number},"
                    f"{float(amplitude[freq_index, event_index]):.9f}\n"
                )
