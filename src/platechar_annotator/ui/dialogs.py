"""Framework-provided dialogs."""

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

_IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.webp);;All files (*)"


def ask_image_path(parent: QWidget | None, start_directory: Path | None) -> Path | None:
    """Show an image selection dialog. Returns None if the user cancels."""
    selected, _ = QFileDialog.getOpenFileName(
        parent,
        "Open image",
        str(start_directory) if start_directory else "",
        _IMAGE_FILTER,
    )
    return Path(selected) if selected else None


def show_error(parent: QWidget | None, title: str, message: str) -> None:
    """Show a modal error message."""
    QMessageBox.critical(parent, title, message)