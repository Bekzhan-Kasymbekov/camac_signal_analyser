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

def write_wavelet_results_csv(
    output_path,
    wavelet_results: dict,
) -> None:
    """
    Экспортирует результаты вейвлет-анализа для двух каналов: AE и EME.

    Поддерживает два режима:

    mode == "current":
        Полные скалограммы текущего импульса.
        Столбцы матрицы = время внутри импульса.

    mode == "all_events":
        Сводные вейвлет-карты по всем импульсам.
        Столбцы матрицы = номера импульсов.
    """
    import csv
    from pathlib import Path

    output_path = Path(output_path)

    mode = wavelet_results.get("mode", "")
    channels = wavelet_results.get("channels", {})

    if not channels:
        raise ValueError("Нет данных вейвлет-анализа для экспорта.")

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)

        writer.writerow(
            [
                "mode",
                "channel",
                "event_number",
                "original_event_number",
                "frequency_hz",
                "time_ms",
                "log10_wavelet_amplitude",
            ]
        )

        if mode == "current":
            event_number = wavelet_results.get("event_number", "")
            original_event_number = wavelet_results.get(
                "original_event_number",
                "",
            )

            for channel_name, channel_result in channels.items():
                amplitude = np.asarray(
                    channel_result["amplitude"],
                    dtype=float,
                )
                frequencies = np.asarray(
                    channel_result["frequencies"],
                    dtype=float,
                )
                time_ms = np.asarray(
                    channel_result["time_ms"],
                    dtype=float,
                )

                if amplitude.ndim != 2:
                    raise ValueError(
                        f"Wavelet amplitude for {channel_name} must be 2D."
                    )

                if amplitude.shape[0] != len(frequencies):
                    raise ValueError(
                        f"Frequency count mismatch for {channel_name}."
                    )

                if amplitude.shape[1] != len(time_ms):
                    raise ValueError(
                        f"Time count mismatch for {channel_name}."
                    )

                for frequency_index, frequency_hz in enumerate(frequencies):
                    for time_index, time_value in enumerate(time_ms):
                        writer.writerow(
                            [
                                mode,
                                channel_name,
                                event_number,
                                original_event_number,
                                float(frequency_hz),
                                float(time_value),
                                float(amplitude[frequency_index, time_index]),
                            ]
                        )

            return

        if mode == "all_events":
            event_numbers = np.asarray(
                wavelet_results.get("event_numbers", []),
                dtype=int,
            )
            original_event_numbers = np.asarray(
                wavelet_results.get("original_event_numbers", []),
                dtype=int,
            )

            if len(event_numbers) == 0:
                raise ValueError("Нет номеров импульсов для экспорта.")

            if len(original_event_numbers) != len(event_numbers):
                raise ValueError(
                    "Количество исходных номеров импульсов не совпадает "
                    "с количеством текущих номеров."
                )

            for channel_name, channel_result in channels.items():
                amplitude = np.asarray(
                    channel_result["amplitude"],
                    dtype=float,
                )
                frequencies = np.asarray(
                    channel_result["frequencies"],
                    dtype=float,
                )

                if amplitude.ndim != 2:
                    raise ValueError(
                        f"Wavelet amplitude for {channel_name} must be 2D."
                    )

                if amplitude.shape[0] != len(frequencies):
                    raise ValueError(
                        f"Frequency count mismatch for {channel_name}."
                    )

                if amplitude.shape[1] != len(event_numbers):
                    raise ValueError(
                        f"Event count mismatch for {channel_name}."
                    )

                for frequency_index, frequency_hz in enumerate(frequencies):
                    for event_index, event_number in enumerate(event_numbers):
                        writer.writerow(
                            [
                                mode,
                                channel_name,
                                int(event_number),
                                int(original_event_numbers[event_index]),
                                float(frequency_hz),
                                "",
                                float(amplitude[frequency_index, event_index]),
                            ]
                        )

            return

        raise ValueError(f"Unknown wavelet export mode: {mode}")

def write_processed_signal_matrix_csv(
    output_path,
    signals,
    event_times_seconds,
    event_numbers=None,
    original_event_numbers=None,
    progress_callback=None,
) -> None:
    """
    Экспортирует обработанные сигналы текущего каталога в матричный CSV.

    Формат CSV:
        row_label,event_1_original_50,event_2_original_51,...
        experiment_time_seconds,1.89487,1.92412,...
        sample_0,-12.4,3.1,...
        sample_1,-10.2,2.7,...

    То есть:
        - столбцы = импульсы / сигналы;
        - первая строка = подписи столбцов;
        - первый столбец = подписи строк;
        - первая строка данных = время импульса в эксперименте;
        - следующие строки = значения обработанного сигнала;
        - без CAMAC metadata/header.
    """
    import csv
    from pathlib import Path

    import numpy as np

    output_path = Path(output_path)

    signals = [
        np.asarray(signal, dtype=float)
        for signal in signals
    ]

    event_times_seconds = np.asarray(event_times_seconds, dtype=float)

    if len(signals) == 0:
        raise ValueError("Нет сигналов для экспорта.")

    event_count = len(signals)

    if len(event_times_seconds) != event_count:
        raise ValueError(
            "Количество времен событий не совпадает с количеством сигналов."
        )

    if event_numbers is None:
        event_numbers = np.arange(1, event_count + 1, dtype=int)
    else:
        event_numbers = np.asarray(event_numbers, dtype=int)

    if original_event_numbers is None:
        original_event_numbers = event_numbers
    else:
        original_event_numbers = np.asarray(original_event_numbers, dtype=int)

    if len(event_numbers) != event_count:
        raise ValueError(
            "Количество текущих номеров импульсов не совпадает с количеством сигналов."
        )

    if len(original_event_numbers) != event_count:
        raise ValueError(
            "Количество исходных номеров импульсов не совпадает с количеством сигналов."
        )

    max_signal_length = max(len(signal) for signal in signals)

    if max_signal_length == 0:
        raise ValueError("Сигналы пустые.")

    def format_number(value: float) -> str:
        if not np.isfinite(value):
            return ""
        return f"{float(value):.15g}"

    column_labels = [
        f"event_{int(event_number)}_original_{int(original_event_number)}"
        for event_number, original_event_number in zip(
            event_numbers,
            original_event_numbers,
        )
    ]

    total_rows = max_signal_length + 2

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)

        writer.writerow(
            ["row_label"]
            + column_labels
        )

        writer.writerow(
            ["experiment_time_seconds"]
            + [
                format_number(time_value)
                for time_value in event_times_seconds
            ]
        )

        if progress_callback is not None:
            progress_callback(2, total_rows)

        for sample_index in range(max_signal_length):
            row = [f"sample_{sample_index}"]

            for signal in signals:
                if sample_index < len(signal):
                    row.append(format_number(signal[sample_index]))
                else:
                    row.append("")

            writer.writerow(row)

            if (
                progress_callback is not None
                and (
                    sample_index % 25 == 0
                    or sample_index == max_signal_length - 1
                )
            ):
                progress_callback(sample_index + 3, total_rows)
