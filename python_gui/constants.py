# python_gui/constants.py

"""
Константы CAMAC Signal Analyser.

Здесь хранятся фиксированные параметры записи CAMAC,
которые используются в GUI, FFT, экспорте CSV и вейвлет-анализе.
"""

# CAMAC записывает сигнал с шагом 500 нс.
# Это соответствует частоте дискретизации 2 MHz.
SAMPLE_INTERVAL_SECONDS = 500e-9
SAMPLE_INTERVAL_MICROSECONDS = 0.5
SAMPLE_INTERVAL_MILLISECONDS = 0.0005

DEFAULT_WAVELET_MIN_FREQ = 1000.0
DEFAULT_WAVELET_MAX_FREQ = 1_000_000.0
DEFAULT_WAVELET_FREQUENCY_COUNT_SINGLE = 128
DEFAULT_WAVELET_FREQUENCY_COUNT_ALL = 64
