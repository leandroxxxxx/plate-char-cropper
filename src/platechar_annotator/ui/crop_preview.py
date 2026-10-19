"""Panel that previews the crop of the selected rectangle.

Display only: the crop itself is never resized or filtered. It is merely
magnified (nearest-neighbour, so pixels stay visible) or reduced to fit the
preview box.
"""

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from platechar_annotator.ui.image_view import pil_to_qpixmap

_PANEL_WIDTH = 220
_BOX_SIZE = 200
_PLACEHOLDER = "Select a rectangle to preview its crop."


class CropPreview(QWidget):
    """Shows one crop, with its size in original pixels."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(_PANEL_WIDTH)

        title = QLabel("Crop preview")
        title_font = title.font()
        title_font.setBold(True)
        title.setFont(title_font)

        self._image_label = QLabel()
        self._image_label.setFixedSize(_BOX_SIZE, _BOX_SIZE)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setWordWrap(True)
        self._image_label.setFrameShape(QFrame.Shape.StyledPanel)

        self._caption = QLabel()
        self._caption.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
        )
        self._caption.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(self._image_label)
        layout.addWidget(self._caption)
        layout.addStretch(1)

        self.clear_preview()

    def clear_preview(self) -> None:
        """Reset to the placeholder text."""
        self.show_message(_PLACEHOLDER)

    def show_message(self, message: str) -> None:
        """Show text instead of a crop (e.g. an invalid-region error)."""
        self._image_label.clear()
        self._image_label.setText(message)
        self._caption.clear()

    def show_crop(self, index: int, crop: Image.Image) -> None:
        """Show a crop, scaled to fit the box for display only."""
        fits = crop.width <= _BOX_SIZE and crop.height <= _BOX_SIZE
        mode = (
            Qt.TransformationMode.FastTransformation
            if fits
            else Qt.TransformationMode.SmoothTransformation
        )
        scaled = pil_to_qpixmap(crop).scaled(
            _BOX_SIZE, _BOX_SIZE, Qt.AspectRatioMode.KeepAspectRatio, mode
        )
        self._image_label.setPixmap(scaled)
        self._caption.setText(f"Rectangle {index}\n{crop.width} × {crop.height} px")