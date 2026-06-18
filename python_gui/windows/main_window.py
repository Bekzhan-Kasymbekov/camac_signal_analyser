from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app_state import app_state
from widgets.archive_overview_widget import archive_overview_widget
from widgets.event_viewer_widget import event_viewer_widget

class main_window(QMainWindow):
    def __init__(self, state: app_state) -> None:
        super().__init__()

        self.state = state

        self.setWindowTitle("CAMAC Signal Analyser")

        self.archive_overview = archive_overview_widget(self.state)
        self.event_viewer = event_viewer_widget(self.state)

        self.file_label = QLabel("No file loaded")

        self.open_button = QPushButton("Open CAMAC File")
        self.open_button.clicked.connect(self.open_file)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.open_button)
        top_layout.addWidget(self.file_label, stretch=1)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.archive_overview, "Archive Overview")
        self.tabs.addTab(self.event_viewer, "Event Viewer")

        root_layout = QVBoxLayout()
        root_layout.addLayout(top_layout)
        root_layout.addWidget(self.tabs)

        root = QWidget()
        root.setLayout(root_layout)

        self.setCentralWidget(root)

    def open_file(self) -> None:
        start_directory = str(Path.home())

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open CAMAC binary file",
            start_directory,
            "CAMAC binary files (*.001 *.002 *.bin);;All files (*)",
        )

        if file_path == "":
            return

        self.state.file_path = Path(file_path)

        try:
            import camac_core

            self.state.archive = camac_core.parse_camac_file(
                str(self.state.file_path),
            )
        except Exception as error:
            QMessageBox.critical(
                self,
                "Failed to load CAMAC file",
                str(error),
            )
            return

        self.file_label.setText(str(self.state.file_path))

        self.archive_overview.refresh()
        self.event_viewer.refresh()
