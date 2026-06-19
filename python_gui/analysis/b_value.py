"""
B-value calculation for CAMAC AE/EME impulse catalogs.

This module contains only numerical logic.
Plotting stays in full_analysis_window.py.
"""

import numpy as np


def calculate_b_value_from_amplitudes(
    amplitudes: np.ndarray,
    min_magnitude: float | None = None,
    threshold_count: int = 30,
) -> tuple[float, float, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Рассчитывает b-value в стиле proba.m, но возвращает две группы точек:

    1. all_x / all_y:
       все точки кумулятивного распределения для отображения на графике.

    2. fit_x / fit_y:
       только участок, где рисуется линейная аппроксимация.

    Для каждого импульса:
        amplitude = max(abs(signal))
        M = log10(amplitude^2)

    Кумулятивный закон:
        log10(N(M >= M_threshold)) = a - bM

    Возвращает:
        b_value:
            коэффициент b
        a_value:
            свободный коэффициент линии
        all_x:
            все пороги M
        all_y:
            log10 cumulative counts для всех порогов
        fit_x:
            x-координаты выбранного линейного участка
        fit_y:
            y-координаты линии только на выбранном участке
    """
    amplitudes = np.asarray(amplitudes, dtype=float)
    amplitudes = amplitudes[np.isfinite(amplitudes)]
    amplitudes = amplitudes[amplitudes > 0]

    if len(amplitudes) < 5:
        raise ValueError("Недостаточно ненулевых амплитуд для расчета B-value.")

    magnitudes = np.log10(amplitudes ** 2)
    magnitudes = magnitudes[np.isfinite(magnitudes)]

    if min_magnitude is not None:
        magnitudes = magnitudes[magnitudes >= min_magnitude]

    if len(magnitudes) < 5:
        raise ValueError(
            "После применения минимальной M осталось слишком мало событий."
        )

    all_x, all_y = build_cumulative_threshold_points(
        magnitudes=magnitudes,
        threshold_count=threshold_count,
        min_magnitude=min_magnitude,
    )

    selected_x, selected_y = select_proba_linear_region(
        all_x,
        all_y,
    )

    slope, intercept, fit_x, fit_y = fit_best_proba_segment(
        selected_x,
        selected_y,
    )

    b_value = abs(float(slope))
    a_value = float(intercept)

    return b_value, a_value, all_x, all_y, fit_x, fit_y


def build_cumulative_threshold_points(
    magnitudes: np.ndarray,
    threshold_count: int,
    min_magnitude: float | None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Создает кумулятивные точки.

    Близко к proba.m:
        N = 30
        step_amps = max(nak_ampl) / N
        nakop_amps(i) = sum(nak_ampl >= step_amps * i)

    Если пользователь задал min_magnitude, пороги начинаются с него.
    """
    if threshold_count < 2:
        raise ValueError("threshold_count должен быть не меньше 2.")

    min_value = float(np.min(magnitudes))
    max_value = float(np.max(magnitudes))

    if min_magnitude is not None:
        start_value = float(min_magnitude)
    elif max_value > 0:
        start_value = 0.0
    else:
        start_value = min_value

    if start_value >= max_value:
        raise ValueError("Диапазон M слишком мал для расчета B-value.")

    thresholds = np.linspace(
        start_value,
        max_value,
        threshold_count + 1,
    )

    cumulative_counts = np.array(
        [
            np.sum(magnitudes >= threshold)
            for threshold in thresholds
        ],
        dtype=float,
    )

    valid_mask = cumulative_counts > 0

    thresholds = thresholds[valid_mask]
    cumulative_counts = cumulative_counts[valid_mask]

    if len(thresholds) < 5:
        raise ValueError("Недостаточно кумулятивных точек для расчета B-value.")

    log_counts = np.log10(cumulative_counts)

    return thresholds, log_counts


def select_proba_linear_region(
    x: np.ndarray,
    y: np.ndarray,
    plateau_drop: float = 0.02,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Выбирает область после начальной верхней полки.

    Это соответствует идее proba.m:
        pol_x = e_step(nakop_amps1 < max(nakop_amps1)-0.02)
        pol_y = nakop_amps1(nakop_amps1 < max(nakop_amps1)-0.02)

    Последнюю точку убираем, потому что хвост часто нестабилен.
    """
    max_y = float(np.max(y))

    mask = y < max_y - plateau_drop

    selected_x = x[mask]
    selected_y = y[mask]

    if len(selected_x) > 1:
        selected_x = selected_x[:-1]
        selected_y = selected_y[:-1]

    if len(selected_x) < 4:
        raise ValueError(
            "После удаления начальной полки осталось слишком мало точек "
            "для B-value. Попробуйте другой диапазон или min M."
        )

    return selected_x, selected_y


def fit_best_proba_segment(
    x: np.ndarray,
    y: np.ndarray,
) -> tuple[float, float, np.ndarray, np.ndarray]:
    """
    Выбирает лучший линейный сегмент и возвращает линию на выбранной области.

    Важно:
    slope/intercept подбираются по лучшему сегменту,
    но линия рисуется только на selected_x, а не на всех точках графика.
    """
    if len(x) != len(y):
        raise ValueError("x и y должны иметь одинаковую длину.")

    if len(x) < 4:
        raise ValueError("Недостаточно точек для линейной аппроксимации B-value.")

    k = round(len(x) / 2) - 1

    if k < 1:
        raise ValueError("Недостаточно точек для выбора линейного сегмента.")

    segment_length = k + 1

    best_error = None
    best_slope = None
    best_intercept = None

    for start_index in range(0, len(x) - segment_length + 1):
        end_index = start_index + segment_length

        segment_x = x[start_index:end_index]
        segment_y = y[start_index:end_index]

        if len(segment_x) < 2:
            continue

        slope, intercept = np.polyfit(segment_x, segment_y, 1)

        y_fit_over_selected_region = slope * x + intercept
        error = float(np.sum(np.abs(y - y_fit_over_selected_region)))

        if best_error is None or error < best_error:
            best_error = error
            best_slope = float(slope)
            best_intercept = float(intercept)

    if best_slope is None or best_intercept is None:
        raise ValueError("Не удалось выбрать линейный сегмент для B-value.")

    fit_x = x
    fit_y = best_slope * fit_x + best_intercept

    return best_slope, best_intercept, fit_x, fit_y
