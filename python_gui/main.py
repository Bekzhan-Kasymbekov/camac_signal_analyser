import sys

from PySide6.QtWidgets import QApplication

from windows.full_analysis_window import full_analysis_window

def solve() -> None:
    app = QApplication(sys.argv)

    window = full_analysis_window()
    window.resize(1400, 850)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    solve()
