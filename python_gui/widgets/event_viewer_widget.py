import numpy as np
import pyqtgraph as pg

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app_state import app_state


class event_viewer_widget(QWidget):
    def __init__(self, state: app_state) -> None:
        super().__init__()

        self.state = state

        self.info_label = QLabel("Load a CAMAC file to view events.")

        self.event_index_input = QLineEdit("1")
        self.event_index_input.setFixedWidth(100)

        self.show_button = QPushButton("Show Event")
        self.show_button.clicked.connect(self.show_selected_event)

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("Event number:"))
        controls_layout.addWidget(self.event_index_input)
        controls_layout.addWidget(self.show_button)
        controls_layout.addStretch()

        self.ae_plot = pg.PlotWidget()
        self.ae_plot.setLabel("bottom", "Local time", units="us")
        self.ae_plot.setLabel("left", "AE signal")
        self.ae_plot.showGrid(x=True, y=True)

        self.eme_plot = pg.PlotWidget()
        self.eme_plot.setLabel("bottom", "Local time", units="us")
        self.eme_plot.setLabel("left", "EME signal")
        self.eme_plot.showGrid(x=True, y=True)
        
        self.ae_fft_plot = pg.PlotWidget()
        self.ae_fft_plot.setLabel("bottom", "Frequency", units="Hz")
        self.ae_fft_plot.setLabel("left", "AE FFT magnitude")
        self.ae_fft_plot.showGrid(x=True, y=True)

        self.eme_fft_plot = pg.PlotWidget()
        self.eme_fft_plot.setLabel("bottom", "Frequency", units="Hz")
        self.eme_fft_plot.setLabel("left", "EME FFT magnitude")
        self.eme_fft_plot.showGrid(x=True, y=True)

        layout = QVBoxLayout()
        layout.addWidget(self.info_label)
        layout.addLayout(controls_layout)
        layout.addWidget(self.ae_plot)
        layout.addWidget(self.eme_plot)
        layout.addWidget(self.ae_fft_plot)
        layout.addWidget(self.eme_fft_plot)

        self.setLayout(layout)

    def refresh(self) -> None:
        self.ae_plot.clear()
        self.eme_plot.clear()
        self.ae_fft_plot.clear()
        self.eme_fft_plot.clear()

        if not self.state.has_archive():
            self.info_label.setText("Load a CAMAC file to view events.")
            return

        self.show_event(1)

    def show_selected_event(self) -> None:
        if not self.state.has_archive():
            return

        try:
            event_number = int(self.event_index_input.text())
        except ValueError:
            self.info_label.setText("Invalid event number.")
            return

        self.show_event(event_number)

    def show_event(self, event_number: int) -> None:
        archive = self.state.archive

        if event_number < 1 or event_number > archive.event_count():
            self.info_label.setText("Event number out of range.")
            return

        event_index = event_number - 1

        ae_signal = np.array(archive.ae_signal(event_index), dtype=float)
        eme_signal = np.array(archive.eme_signal(event_index), dtype=float)

        ae_time_us = np.arange(len(ae_signal)) * 0.5
        eme_time_us = np.arange(len(eme_signal)) * 0.5
        
        sample_interval_seconds = 500e-9

        ae_freqs = np.fft.rfftfreq(len(ae_signal), d=sample_interval_seconds)
        eme_freqs = np.fft.rfftfreq(len(eme_signal), d=sample_interval_seconds)

        ae_fft = np.abs(np.fft.rfft(ae_signal))
        eme_fft = np.abs(np.fft.rfft(eme_signal))

        info = archive.event_info(event_index)

        self.info_label.setText(
            f"Event {event_number} | "
            f"Relative time: {info['relative_seconds']:.6f} s | "
            f"AE max abs: {info['ae_max_abs']:.3f} | "
            f"EME max abs: {info['eme_max_abs']:.3f}"
        )

        self.ae_plot.clear()
        self.eme_plot.clear()
        self.ae_fft_plot.clear()
        self.eme_fft_plot.clear()

        self.ae_plot.plot(ae_time_us, ae_signal)
        self.eme_plot.plot(eme_time_us, eme_signal)

        self.ae_fft_plot.plot(ae_freqs, ae_fft)
        self.eme_fft_plot.plot(eme_freqs, eme_fft)
