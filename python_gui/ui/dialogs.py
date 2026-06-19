# python_gui/ui/dialogs.py

"""
Пользовательские диалоги CAMAC Signal Analyser.

Стандартные QMessageBox на некоторых Linux/Ubuntu окружениях
могут выглядеть тесно или обрезать текст. Поэтому здесь используются
собственные QDialog с нормальной шириной, переносом строк и деталями ошибки.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def show_message_dialog(
    parent: QWidget,
    title: str,
    text: str,
    icon: QMessageBox.Icon = QMessageBox.Information,
    details: str | None = None,
) -> None:
    """
    Показывает информационное окно, ошибку или предупреждение.

    icon оставлен в параметрах для совместимости с вызовами из GUI.
    Сейчас внешний вид диалога одинаковый, а тип сообщения передается
    в основном для читаемости кода.
    """
    _ = icon

    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumWidth(620)

    if details is not None and details.strip() != "":
        dialog.setMinimumHeight(360)
    else:
        dialog.setMinimumHeight(180)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(12)

    text_label = QLabel(text)
    text_label.setWordWrap(True)
    text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    text_label.setMinimumWidth(560)
    text_label.setStyleSheet("font-size: 13px;")
    layout.addWidget(text_label)

    if details is not None and details.strip() != "":
        details_box = QTextEdit()
        details_box.setReadOnly(True)
        details_box.setPlainText(details)
        details_box.setMinimumHeight(140)
        layout.addWidget(details_box)

    buttons = QDialogButtonBox(QDialogButtonBox.Ok)
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons)

    dialog.exec()


def ask_confirmation_dialog(
    parent: QWidget,
    title: str,
    text: str,
    yes_text: str = "Да",
    no_text: str = "Нет",
) -> bool:
    """
    Показывает диалог подтверждения.

    Возвращает:
        True, если пользователь нажал кнопку подтверждения.
        False, если пользователь нажал отмену или закрыл окно.
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumWidth(520)
    dialog.setMinimumHeight(220)

    layout = QVBoxLayout(dialog)

    label = QLabel(text)
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    layout.addWidget(label)

    buttons = QDialogButtonBox()

    yes_button = QPushButton(yes_text)
    no_button = QPushButton(no_text)

    buttons.addButton(yes_button, QDialogButtonBox.AcceptRole)
    buttons.addButton(no_button, QDialogButtonBox.RejectRole)

    yes_button.clicked.connect(dialog.accept)
    no_button.clicked.connect(dialog.reject)

    layout.addWidget(buttons)

    return dialog.exec() == QDialog.Accepted
