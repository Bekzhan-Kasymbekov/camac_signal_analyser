# python_gui/analysis/b_value.py

"""
Расчет b-value для CAMAC Signal Analyser.

Модуль содержит только математическую часть.
Построение графиков, labels и QMessageBox остаются в GUI.
"""

import numpy as np


def calculate_b_value_from_amplitudes(
    amplitudes: np.ndarray,
    min_magnitude: float | None = None,
) -> tuple[float, float, np.ndarray, np.ndarray]:
    """
    Рассчитывает b-value по распределению амплитуд импульсов.

    Для каждого импульса берется амплитуда:
        max_abs = max(abs(signal))

    Условная магнитуда:
        M = log10(max_abs^2)

    Затем строится зависимость:
        log10(N >= M) = a - bM

    Возвращает:
        b_value:
            коэффициент b
        a_value:
            свободный коэффициент a
        x:
            значения M
        y:
            значения log10(N >= M)

    Важно:
    Это базовая оценка b-value для GUI. Если методика станции использует
    другую формулу магнитуды, менять нужно именно эту функцию.
    """
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
