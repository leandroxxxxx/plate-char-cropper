"""Framework-provided dialogs."""

from collections.abc import Sequence
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


def ask_directory(parent: QWidget | None, start_directory: Path | None) -> Path | None:
    """Show a folder selection dialog. Returns None if the user cancels."""
    selected = QFileDialog.getExistingDirectory(
        parent,
        "Select destination folder",
        str(start_directory) if start_directory else "",
    )
    return Path(selected) if selected else None


def show_error(parent: QWidget | None, title: str, message: str) -> None:
    """Show a modal error message."""
    QMessageBox.critical(parent, title, message)


def ask_overwrite(
    parent: QWidget | None, existing_names: Sequence[str]
) -> bool | None:
    """Ask the user how to handle already-existing output files.

    Returns:
        True  -> overwrite all existing files,
        False -> skip all existing files,
        None  -> cancel the whole save.
    """
    shown = list(existing_names[:10])
    listing = "\n".join(f"• {name}" for name in shown)
    if len(existing_names) > len(shown):
        listing += f"\n… and {len(existing_names) - len(shown)} more"

    dialog = QMessageBox(parent)
    dialog.setIcon(QMessageBox.Icon.Warning)
    dialog.setWindowTitle("Files already exist")
    dialog.setText(
        f"The following output file(s) already exist:\n{listing}\n\n"
        "Overwrite all of them, skip them, or cancel the save?"
    )
    overwrite_button = dialog.addButton(
        "Overwrite All", QMessageBox.ButtonRole.YesRole
    )
    skip_button = dialog.addButton("Skip All", QMessageBox.ButtonRole.NoRole)
    dialog.addButton(QMessageBox.StandardButton.Cancel)
    dialog.setDefaultButton(skip_button)
    dialog.setEscapeButton(QMessageBox.StandardButton.Cancel)
    dialog.exec()

    clicked = dialog.clickedButton()
    if clicked == overwrite_button:
        return True
    if clicked == skip_button:
        return False
    return None
