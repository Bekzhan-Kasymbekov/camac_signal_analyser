# python_gui/analysis/wavelet_analysis.py

"""
Вейвлет-анализ CAMAC сигналов.

Модуль содержит только вычисления.
Отображение через PyQtGraph, progress dialog и сообщения пользователю
остаются в GUI.

Режимы вейвлет-анализа:

1. current:
   строится полная скалограмма одного выбранного импульса.
   Ось X = время внутри импульса, мс.
   Ось Y = частота, Hz.

2. all:
   для каждого импульса считается краткая частотная сводка.
   Полную скалограмму для 1988 импульсов строить слишком тяжело,
   поэтому каждый импульс превращается в один вертикальный столбец:
   средняя амплитуда вейвлета по времени для каждой частоты.
"""

import numpy as np


def compute_current_event_wavelet(
    signal: np.ndarray,
    wavelet_name: str,
    min_freq: float,
    max_freq: float,
    sample_period_seconds: float,
    frequency_count: int = 128,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Строит скалограмму одного импульса.

    Возвращает:
    - amplitude_matrix_log:
        log10(abs(CWT) + 1e-12), shape = frequencies x time
    - time_ms:
        время внутри импульса, мс
    - calculated_frequencies:
        частоты, рассчитанные PyWavelets
    """
    import pywt

    signal = np.asarray(signal, dtype=float)

    if len(signal) < 10:
        raise ValueError("Сигнал слишком короткий для вейвлет-анализа.")

    if min_freq <= 0 or max_freq <= 0 or min_freq >= max_freq:
        raise ValueError("Частоты должны быть > 0, и min_freq должен быть меньше max_freq.")

    if sample_period_seconds <= 0:
        raise ValueError("sample_period_seconds должен быть больше нуля.")

    signal = signal - np.mean(signal)

    frequencies = np.linspace(
        min_freq,
        max_freq,
        frequency_count,
    )

    central_frequency = pywt.central_frequency(wavelet_name)
    scales = central_frequency / (frequencies * sample_period_seconds)

    coefficients, calculated_frequencies = pywt.cwt(
        signal,
        scales,
        wavelet_name,
        sampling_period=sample_period_seconds,
    )

    amplitude_matrix_log = np.log10(np.abs(coefficients) + 1e-12)

    time_ms = np.arange(len(signal)) * sample_period_seconds * 1000.0

    return amplitude_matrix_log, time_ms, calculated_frequencies

def compute_all_events_wavelet_summary(
    signals: list[np.ndarray],
    wavelet_name: str,
    min_freq: float,
    max_freq: float,
    sample_period_seconds: float,
    frequency_count: int = 64,
    downsample_step: int = 4,
    progress_callback=None,
    cancel_callback=None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Строит вейвлет-сводку для всех импульсов текущего диапазона.

    Для одного импульса можно построить полную скалограмму.
    Но для всех импульсов это слишком тяжело, поэтому используется сводка:

    - для каждого импульса считается CWT;
    - амплитуда усредняется по времени;
    - каждый импульс становится одним вертикальным столбцом;
    - ось X = номер импульса;
    - ось Y = частота;
    - цвет = log10 средней wavelet amplitude.

    progress_callback:
        функция, которой передается номер обработанного импульса.

    cancel_callback:
        функция, которая возвращает True, если пользователь нажал Cancel.
    """
    import pywt

    if len(signals) == 0:
        raise ValueError("Нет сигналов для вейвлет-анализа.")

    if min_freq <= 0 or max_freq <= 0 or min_freq >= max_freq:
        raise ValueError("Частоты должны быть > 0, и min_freq должен быть меньше max_freq.")

    if sample_period_seconds <= 0:
        raise ValueError("sample_period_seconds должен быть больше нуля.")

    if frequency_count < 2:
        raise ValueError("frequency_count должен быть не меньше 2.")

    if downsample_step < 1:
        raise ValueError("downsample_step должен быть не меньше 1.")

    effective_sample_period = sample_period_seconds * downsample_step

    frequencies = np.linspace(
        min_freq,
        max_freq,
        frequency_count,
    )

    central_frequency = pywt.central_frequency(wavelet_name)
    scales = central_frequency / (frequencies * effective_sample_period)

    summary_columns = []

    for event_index, signal in enumerate(signals):
        if cancel_callback is not None and cancel_callback():
            raise RuntimeError("Вейвлет-анализ отменен пользователем.")

        signal = np.asarray(signal, dtype=float)

        if downsample_step > 1:
            signal = signal[::downsample_step]

        if len(signal) < 10:
            frequency_summary = np.zeros(frequency_count, dtype=float)
        else:
            signal = signal - np.mean(signal)

            coefficients, calculated_frequencies = pywt.cwt(
                signal,
                scales,
                wavelet_name,
                sampling_period=effective_sample_period,
            )

            amplitude = np.abs(coefficients)
            frequency_summary = np.mean(amplitude, axis=1)

        summary_columns.append(frequency_summary)

        if progress_callback is not None:
            progress_callback(event_index + 1)

    amplitude_matrix = np.stack(summary_columns, axis=1)
    amplitude_matrix_log = np.log10(amplitude_matrix + 1e-12)

    return amplitude_matrix_log, calculated_frequencies
