"""
Фоновый расчет статистических коэффициентов окна 3.

Этот worker запускается в QThread, чтобы тяжелые расчеты d-value,
S-value, γ-value и Tsallis q не блокировали GUI.
"""

import traceback

import numpy as np
from PySide6.QtCore import QObject, Signal, Slot

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


class StatisticsWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(
        self,
        ae_data: list[np.ndarray],
        eme_data: list[np.ndarray],
        mode: str,
        window_size: int | None = None,
    ) -> None:
        super().__init__()

        self.ae_data = [np.array(signal, dtype=float, copy=True) for signal in ae_data]
        self.eme_data = [np.array(signal, dtype=float, copy=True) for signal in eme_data]
        self.mode = mode
        self.window_size = window_size

    @Slot()
    def run(self) -> None:
        try:
            if self.mode == "single":
                result = self.calculate_single_mode()
            else:
                result = self.calculate_window_mode()

            self.finished.emit(result)

        except Exception:
            self.failed.emit(traceback.format_exc())

    def calculate_single_mode(self) -> dict:
        event_count = len(self.ae_data)
        x = np.arange(1, event_count + 1)

        ae_amplitudes = amplitudes_from_signals(self.ae_data)
        eme_amplitudes = amplitudes_from_signals(self.eme_data)

        ae_d_values = calculate_d_values_from_signals(self.ae_data)
        eme_d_values = calculate_d_values_from_signals(self.eme_data)

        ae_s_value = calculate_s_value_from_amplitudes(ae_amplitudes)
        eme_s_value = calculate_s_value_from_amplitudes(eme_amplitudes)

        ae_gamma = calculate_gamma_value_from_amplitudes(ae_amplitudes)
        eme_gamma = calculate_gamma_value_from_amplitudes(eme_amplitudes)

        ae_q = None
        ae_a = None
        eme_q = None
        eme_a = None

        try:
            ae_q, ae_a, _, _, _ = calculate_tsallis_parameters_from_amplitudes(
                ae_amplitudes
            )
        except Exception:
            pass

        try:
            eme_q, eme_a, _, _, _ = calculate_tsallis_parameters_from_amplitudes(
                eme_amplitudes
            )
        except Exception:
            pass

        return {
            "mode": "single",
            "x": x,
            "ae_d_values": ae_d_values,
            "eme_d_values": eme_d_values,
            "ae_s_value": ae_s_value,
            "eme_s_value": eme_s_value,
            "ae_gamma": ae_gamma,
            "eme_gamma": eme_gamma,
            "ae_q": ae_q,
            "ae_a": ae_a,
            "eme_q": eme_q,
            "eme_a": eme_a,
        }

    def calculate_window_mode(self) -> dict:
        if self.window_size is None:
            raise ValueError("window_size is required for window mode.")

        window_size = self.window_size

        ae_amplitudes = amplitudes_from_signals(self.ae_data)
        eme_amplitudes = amplitudes_from_signals(self.eme_data)

        d_x_ae, ae_d_windowed = calculate_d_values_by_windows(
            self.ae_data,
            window_size,
        )
        d_x_eme, eme_d_windowed = calculate_d_values_by_windows(
            self.eme_data,
            window_size,
        )

        s_x_ae, ae_s_windowed = calculate_s_values_by_windows(
            ae_amplitudes,
            window_size,
        )
        s_x_eme, eme_s_windowed = calculate_s_values_by_windows(
            eme_amplitudes,
            window_size,
        )

        gamma_x_ae, ae_gamma_windowed = calculate_gamma_values_by_windows(
            ae_amplitudes,
            window_size,
        )
        gamma_x_eme, eme_gamma_windowed = calculate_gamma_values_by_windows(
            eme_amplitudes,
            window_size,
        )

        tsallis_x_ae, ae_q_windowed = calculate_tsallis_q_values_by_windows(
            ae_amplitudes,
            window_size,
        )
        tsallis_x_eme, eme_q_windowed = calculate_tsallis_q_values_by_windows(
            eme_amplitudes,
            window_size,
        )

        return {
            "mode": "window",
            "d_x_ae": d_x_ae,
            "ae_d_windowed": ae_d_windowed,
            "d_x_eme": d_x_eme,
            "eme_d_windowed": eme_d_windowed,
            "s_x_ae": s_x_ae,
            "ae_s_windowed": ae_s_windowed,
            "s_x_eme": s_x_eme,
            "eme_s_windowed": eme_s_windowed,
            "gamma_x_ae": gamma_x_ae,
            "ae_gamma_windowed": ae_gamma_windowed,
            "gamma_x_eme": gamma_x_eme,
            "eme_gamma_windowed": eme_gamma_windowed,
            "tsallis_x_ae": tsallis_x_ae,
            "ae_q_windowed": ae_q_windowed,
            "tsallis_x_eme": tsallis_x_eme,
            "eme_q_windowed": eme_q_windowed,
        }
