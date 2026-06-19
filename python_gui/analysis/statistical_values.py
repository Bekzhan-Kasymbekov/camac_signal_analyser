"""
Статистические коэффициенты для окна 3 CAMAC Signal Analyser.

Реализовано:
- d-value:
    фрактальная размерность формы сигнала методом box-counting.
- S-value:
    формула из предоставленного изображения.
- γ-value:
    методика из MATLAB proba.m.
- Tsallis q:
    подбор q и a по уравнению Тсаллиса через nonlinear fit.

Общая основа для распределительных коэффициентов:
    amplitude = max(abs(signal))
    M = log10(amplitude^2)
"""

import numpy as np

from analysis.signal_metrics import calculate_max_abs


# ================= BASE VALUES =================


def amplitudes_from_signals(signals: list[np.ndarray]) -> np.ndarray:
    """
    Возвращает амплитуды импульсов:
        amplitude = max(abs(signal))
    """
    return np.array(
        [calculate_max_abs(signal) for signal in signals],
        dtype=float,
    )


def magnitudes_from_amplitudes(amplitudes: np.ndarray) -> np.ndarray:
    """
    Возвращает условные магнитуды импульсов.

    Используется та же основа, что в proba.m:
        amps = max(abs(signal))
        amps_kv = amps^2
        M = log10(amps_kv)
    """
    amplitudes = np.asarray(amplitudes, dtype=float)
    amplitudes = amplitudes[np.isfinite(amplitudes)]
    amplitudes = amplitudes[amplitudes > 0]

    if len(amplitudes) == 0:
        return np.array([], dtype=float)

    return np.log10(amplitudes ** 2)


# ================= d-value =================


def calculate_waveform_d_value(
    signal: np.ndarray,
    min_power: int = 2,
    max_power: int = 7,
) -> float:
    """
    Рассчитывает d-value как фрактальную размерность формы сигнала.

    Метод:
    - нормируем время и амплитуду в [0, 1];
    - накладываем сетки разных размеров epsilon;
    - считаем количество ячеек N(epsilon), через которые проходит сигнал;
    - строим log(N(epsilon)) от log(1 / epsilon);
    - d-value = slope.

    Формула:
        d = slope(log(N(epsilon)), log(1 / epsilon))

    Это не механическая степень повреждения D.
    """
    signal = np.asarray(signal, dtype=float)
    signal = signal[np.isfinite(signal)]

    if len(signal) < 4:
        return 0.0

    time = np.linspace(0.0, 1.0, len(signal))

    signal_min = float(np.min(signal))
    signal_max = float(np.max(signal))

    if signal_max == signal_min:
        signal_norm = np.full_like(signal, 0.5, dtype=float)
    else:
        signal_norm = (signal - signal_min) / (signal_max - signal_min)

    box_sizes = np.array(
        [1.0 / (2 ** power) for power in range(min_power, max_power + 1)],
        dtype=float,
    )

    box_counts = []

    for epsilon in box_sizes:
        grid_size = int(round(1.0 / epsilon))

        time_indices = np.floor(time * grid_size).astype(int)
        signal_indices = np.floor(signal_norm * grid_size).astype(int)

        time_indices = np.clip(time_indices, 0, grid_size - 1)
        signal_indices = np.clip(signal_indices, 0, grid_size - 1)

        touched_boxes = set(zip(time_indices, signal_indices))
        box_counts.append(len(touched_boxes))

    box_counts = np.array(box_counts, dtype=float)
    valid_mask = box_counts > 0

    if np.sum(valid_mask) < 2:
        return 0.0

    x = np.log(1.0 / box_sizes[valid_mask])
    y = np.log(box_counts[valid_mask])

    slope, _ = np.polyfit(x, y, 1)

    return float(slope)


def calculate_d_values_from_signals(signals: list[np.ndarray]) -> np.ndarray:
    """
    Рассчитывает d-value отдельно для каждого импульса.
    """
    return np.array(
        [calculate_waveform_d_value(signal) for signal in signals],
        dtype=float,
    )


def calculate_d_values_by_windows(
    signals: list[np.ndarray],
    window_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Рассчитывает средний d-value по непересекающимся окнам.
    """
    d_values = calculate_d_values_from_signals(signals)

    x_values = []
    windowed_d_values = []

    for start in range(0, len(d_values) - window_size + 1, window_size):
        end = start + window_size

        x_values.append(start + 1)
        windowed_d_values.append(float(np.mean(d_values[start:end])))

    return np.array(x_values, dtype=int), np.array(windowed_d_values, dtype=float)


# ================= S-value =================


def calculate_s_value_from_magnitudes(magnitudes: np.ndarray) -> float:
    """
    Рассчитывает S-value по формуле:

        S = 0.117 * lg(N + 1)
            + 0.029 * lg((1 / N) * sum(10^(0.075 * m_si)))
            + 0.00075 * m_s

    Интерпретация:
        N = количество импульсов;
        m_si = магнитуда отдельного импульса;
        m_s = сумма магнитуд sum(m_si).
    """
    magnitudes = np.asarray(magnitudes, dtype=float)
    magnitudes = magnitudes[np.isfinite(magnitudes)]

    if len(magnitudes) == 0:
        return 0.0

    event_count = len(magnitudes)
    magnitude_sum = float(np.sum(magnitudes))

    exponential_mean = np.mean(10.0 ** (0.075 * magnitudes))

    if exponential_mean <= 0:
        return 0.0

    s_value = (
        0.117 * np.log10(event_count + 1)
        + 0.029 * np.log10(exponential_mean)
        + 0.00075 * magnitude_sum
    )

    return float(s_value)


def calculate_s_value_from_amplitudes(amplitudes: np.ndarray) -> float:
    """
    Рассчитывает S-value из амплитуд импульсов.
    """
    magnitudes = magnitudes_from_amplitudes(amplitudes)
    return calculate_s_value_from_magnitudes(magnitudes)


def calculate_s_values_by_windows(
    amplitudes: np.ndarray,
    window_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Рассчитывает S-value по непересекающимся окнам.
    """
    amplitudes = np.asarray(amplitudes, dtype=float)

    x_values = []
    s_values = []

    for start in range(0, len(amplitudes) - window_size + 1, window_size):
        end = start + window_size

        x_values.append(start + 1)
        s_values.append(
            calculate_s_value_from_amplitudes(amplitudes[start:end])
        )

    return np.array(x_values, dtype=int), np.array(s_values, dtype=float)


# ================= γ-value =================


def calculate_gamma_value_from_amplitudes(
    amplitudes: np.ndarray,
    histogram_bins: int = 50,
) -> float:
    """
    Рассчитывает γ-value по MATLAB proba.m.

    MATLAB-логика:
        amps_kv = amps.^2
        [n, A] = hist(log10(amps_kv), h)
        берем правую часть гистограммы от максимума n
        p_x = polyfit(A1(2:end), log10(n1(2:end)), 1)
        gamma = abs(p_x(1))
    """
    amplitudes = np.asarray(amplitudes, dtype=float)
    amplitudes = amplitudes[np.isfinite(amplitudes)]
    amplitudes = amplitudes[amplitudes > 0]

    if len(amplitudes) < 5:
        return 0.0

    log_energy = np.log10(amplitudes ** 2)

    counts, bin_edges = np.histogram(log_energy, bins=histogram_bins)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0

    if len(counts) == 0 or np.max(counts) <= 0:
        return 0.0

    peak_index = int(np.argmax(counts))

    tail_counts = counts[peak_index:]
    tail_centers = bin_centers[peak_index:]

    valid_mask = tail_counts > 0
    tail_counts = tail_counts[valid_mask]
    tail_centers = tail_centers[valid_mask]

    # MATLAB использует A1(2:end), log10(n1(2:end)).
    if len(tail_counts) > 2:
        tail_counts = tail_counts[1:]
        tail_centers = tail_centers[1:]

    if len(tail_counts) < 2:
        return 0.0

    slope, _ = np.polyfit(
        tail_centers,
        np.log10(tail_counts),
        1,
    )

    return abs(float(slope))


def calculate_gamma_values_by_windows(
    amplitudes: np.ndarray,
    window_size: int,
    histogram_bins: int = 50,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Рассчитывает γ-value по непересекающимся окнам.
    """
    amplitudes = np.asarray(amplitudes, dtype=float)

    x_values = []
    gamma_values = []

    for start in range(0, len(amplitudes) - window_size + 1, window_size):
        end = start + window_size

        x_values.append(start + 1)
        gamma_values.append(
            calculate_gamma_value_from_amplitudes(
                amplitudes[start:end],
                histogram_bins,
            )
        )

    return np.array(x_values, dtype=int), np.array(gamma_values, dtype=float)


# ================= Tsallis q =================


def _tsallis_model(
    magnitudes: np.ndarray,
    q: float,
    log10_a: float,
) -> np.ndarray:
    """
    Модель Тсаллиса:

        log(N(M > M_th) / N)
        =
        ((2 - q) / (1 - q))
        * log[
            1 - ((1 - q) / (2 - q)) * (10^M_th / a^(2/3))
          ]

    Для устойчивости подбираем log10(a), а не a напрямую.
    """
    a_power = 10.0 ** ((2.0 / 3.0) * log10_a)

    inside = (
        1.0
        - ((1.0 - q) / (2.0 - q))
        * ((10.0 ** magnitudes) / a_power)
    )

    inside = np.maximum(inside, 1e-300)

    return ((2.0 - q) / (1.0 - q)) * np.log10(inside)


def calculate_tsallis_parameters_from_amplitudes(
    amplitudes: np.ndarray,
    threshold_count: int = 30,
) -> tuple[float, float, np.ndarray, np.ndarray, np.ndarray]:
    """
    Подбирает параметры Тсаллиса q и a по распределению амплитуд.

    Используется:
        M = log10(max_abs^2)

    Возвращает:
    - q:
        параметр Тсаллиса;
    - a:
        коэффициент из модели;
    - x:
        пороговые магнитуды M_th;
    - y:
        экспериментальные log(N(M > M_th) / N);
    - y_fit:
        значения модели.
    """
    from scipy.optimize import curve_fit

    magnitudes = magnitudes_from_amplitudes(amplitudes)

    if len(magnitudes) < 5:
        raise ValueError("Недостаточно событий для расчета Tsallis q.")

    min_magnitude = float(np.min(magnitudes))
    max_magnitude = float(np.max(magnitudes))

    if min_magnitude == max_magnitude:
        raise ValueError("Все магнитуды одинаковые, Tsallis q не определяется.")

    thresholds = np.linspace(
        min_magnitude,
        max_magnitude,
        threshold_count,
    )

    total_count = len(magnitudes)

    cumulative_counts = np.array(
        [
            np.sum(magnitudes > threshold)
            for threshold in thresholds
        ],
        dtype=float,
    )

    valid_mask = cumulative_counts > 0

    x = thresholds[valid_mask]
    y = np.log10(cumulative_counts[valid_mask] / total_count)

    if len(x) < 5:
        raise ValueError("Недостаточно точек для подбора Tsallis q.")

    initial_q = 1.5
    initial_log10_a = 1.5 * max_magnitude

    lower_log10_a = max(0.0, 1.5 * min_magnitude - 6.0)
    upper_log10_a = max(1.0, 1.5 * max_magnitude + 6.0)

    parameters, _ = curve_fit(
        _tsallis_model,
        x,
        y,
        p0=[initial_q, initial_log10_a],
        bounds=(
            [1.001, lower_log10_a],
            [1.999, upper_log10_a],
        ),
        maxfev=20_000,
    )

    q = float(parameters[0])
    log10_a = float(parameters[1])
    a = float(10.0 ** log10_a)

    y_fit = _tsallis_model(x, q, log10_a)

    return q, a, x, y, y_fit


def calculate_tsallis_q_values_by_windows(
    amplitudes: np.ndarray,
    window_size: int,
    threshold_count: int = 30,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Рассчитывает Tsallis q по непересекающимся окнам.

    Если в окне q не удалось подобрать, ставится 0.0.
    """
    amplitudes = np.asarray(amplitudes, dtype=float)

    x_values = []
    q_values = []

    for start in range(0, len(amplitudes) - window_size + 1, window_size):
        end = start + window_size

        x_values.append(start + 1)

        try:
            q, _, _, _, _ = calculate_tsallis_parameters_from_amplitudes(
                amplitudes[start:end],
                threshold_count,
            )
        except Exception:
            q = 0.0

        q_values.append(q)

    return np.array(x_values, dtype=int), np.array(q_values, dtype=float)
