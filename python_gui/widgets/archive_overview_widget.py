import numpy as np
import pyqtgraph as pg

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app_state import app_state


class archive_overview_widget(QWidget):
    def __init__(self, state: app_state) -> None:
        super().__init__()

        self.state = state

        self.info_label = QLabel("Load a CAMAC file to see archive overview.")

        self.count_plot = pg.PlotWidget()
        self.count_plot.setLabel("bottom", "Relative time", units="s")
        self.count_plot.setLabel("left", "Cumulative impulse count")
        self.count_plot.showGrid(x=True, y=True)

        self.ae_energy_plot = pg.PlotWidget()
        self.ae_energy_plot.setLabel("bottom", "Relative time", units="s")
        self.ae_energy_plot.setLabel("left", "Cumulative AE energy")
        self.ae_energy_plot.showGrid(x=True, y=True)

        self.eme_energy_plot = pg.PlotWidget()
        self.eme_energy_plot.setLabel("bottom", "Relative time", units="s")
        self.eme_energy_plot.setLabel("left", "Cumulative EME energy")
        self.eme_energy_plot.showGrid(x=True, y=True)

        layout = QVBoxLayout()
        layout.addWidget(self.info_label)
        layout.addWidget(self.count_plot)
        layout.addWidget(self.ae_energy_plot)
        layout.addWidget(self.eme_energy_plot)

        self.setLayout(layout)

    def refresh(self) -> None:
        self.count_plot.clear()
        self.ae_energy_plot.clear()
        self.eme_energy_plot.clear()

        if not self.state.has_archive():
            self.info_label.setText("Load a CAMAC file to see archive overview.")
            return

        archive = self.state.archive

        event_count = archive.event_count()
        relative_seconds = np.array(archive.relative_seconds(), dtype=float)
        ae_energy = np.array(archive.ae_energy_values(), dtype=float)
        eme_energy = np.array(archive.eme_energy_values(), dtype=float)

        cumulative_count = np.arange(1, event_count + 1)
        cumulative_ae_energy = np.cumsum(ae_energy)
        cumulative_eme_energy = np.cumsum(eme_energy)

        self.info_label.setText(
            f"Events: {event_count} | "
            f"Duration: {relative_seconds[-1]:.3f} s"
        )

        self.count_plot.plot(relative_seconds, cumulative_count)
        self.ae_energy_plot.plot(relative_seconds, cumulative_ae_energy)
        self.eme_energy_plot.plot(relative_seconds, cumulative_eme_energy)
