# python_gui/analysis/fft_analysis.py

"""
FFT-анализ CAMAC сигналов.

Здесь находятся вычисления АЧХ/FFT без Qt и GUI.
"""

import numpy as np


def compute_mean_fft_amplitude(
    signals: list[np.ndarray],
    sample_interval_seconds: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Рассчитывает сводную АЧХ для набора импульсов.

    Для каждого импульса считается FFT amplitude.
    Затем амплитуды усредняются по всем импульсам.

    Возвращает:
    - frequencies:
        частоты, Hz
    - mean_amplitude:
        средняя амплитуда FFT по всем импульсам
    """
    if len(signals) == 0:
        raise ValueError("Нет сигналов для FFT.")

    valid_signals = [
        np.asarray(signal, dtype=float)
        for signal in signals
        if len(signal) > 1
    ]

    if len(valid_signals) == 0:
        raise ValueError("Нет подходящих сигналов для FFT.")

    signal_length = min(len(signal) for signal in valid_signals)

    fft_amplitudes = []

    for signal in valid_signals:
        signal = signal[:signal_length]
        signal = signal - np.mean(signal)

        amplitude = np.abs(np.fft.rfft(signal))
        fft_amplitudes.append(amplitude)

    frequencies = np.fft.rfftfreq(
        signal_length,
        d=sample_interval_seconds,
    )

    mean_amplitude = np.mean(
        np.array(fft_amplitudes, dtype=float),
        axis=0,
    )

    return frequencies, mean_amplitude
