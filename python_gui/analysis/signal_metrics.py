# python_gui/analysis/signal_metrics.py

"""
Расчет простых метрик сигналов CAMAC.

Этот модуль не зависит от Qt и GUI.
Его можно безопасно использовать из графического интерфейса,
экспорта CSV и будущих тестов.
"""

import numpy as np


def calculate_energy(signal: np.ndarray) -> float:
    """
    Возвращает энергию сигнала.

    Энергия считается как сумма квадратов всех отсчетов:
        E = sum(signal^2)
    """
    return float(np.sum(signal ** 2))


def calculate_max_abs(signal: np.ndarray) -> float:
    """
    Возвращает максимальное абсолютное отклонение сигнала.

    Используется как амплитуда импульса для каталогов,
    статистических графиков и b-value.
    """
    if len(signal) == 0:
        return 0.0

    return float(np.max(np.abs(signal)))


def calculate_power(
    signal: np.ndarray,
    sample_interval_seconds: float,
) -> float:
    """
    Возвращает среднюю мощность сигнала за длительность импульса.

    power = energy / duration
    duration = number_of_samples * sample_interval_seconds
    """
    duration_seconds = len(signal) * sample_interval_seconds

    if duration_seconds <= 0:
        return 0.0

    return calculate_energy(signal) / duration_seconds
