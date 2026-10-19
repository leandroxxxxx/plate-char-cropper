"""Image display widget.

The original image is never resized: a QPixmap copy is displayed and the
view's transform scales it to fit the available area.
"""

from collections.abc import Sequence

from PIL import Image
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QPainter,
    QPixmap,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QWidget,
)

from platechar_annotator.models.selection import CharacterRect
from platechar_annotator.ui.rect_item import RectOverlayItem

# Distinct overlay colors for rectangles 1..7 (left to right).
_RECT_COLOR_HEX = [
    "#e6194b",
    "#f58231",
    "#ffe119",
    "#3cb44b",
    "#42d4f4",
    "#4363d8",
    "#f032e6",
]


def pil_to_qpixmap(image: Image.Image) -> QPixmap:
    """Convert a PIL image to a QPixmap for display (the PIL image is not modified)."""
    rgba = image.convert("RGBA")
    data = rgba.tobytes()
    qimage = QImage(
        data, rgba.width, rgba.height, rgba.width * 4, QImage.Format.Format_RGBA8888
    )
    # copy() detaches the QImage from the temporary bytes buffer.
    return QPixmap.fromImage(qimage.copy())


class ImageView(QGraphicsView):
    """Displays an image scaled to fit the widget, keeping its aspect ratio."""

    # Emitted while a rectangle is moved or resized, with its new geometry:
    # (index, x, y, width, height) in original-image pixel coordinates.
    rectangle_changed = Signal(int, float, float, float, float)

    # Emitted when the selection changes: the selected rectangle's index, or
    # 0 when no rectangle is selected.
    rectangle_selected = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._scene.selectionChanged.connect(self._on_selection_changed)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._rect_items: list[RectOverlayItem] = []

        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setBackgroundBrush(QBrush(QColor(40, 40, 40)))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def set_image(self, image: Image.Image) -> None:
        """Replace the displayed image, dropping any rectangle overlays."""
        # Qt deletes the old items in clear(); keep it from calling back into us.
        self._scene.blockSignals(True)
        self._scene.clear()
        self._scene.blockSignals(False)
        self._rect_items = []  # clear() already deleted the overlay items.
        self._pixmap_item = self._scene.addPixmap(pil_to_qpixmap(image))
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self.fit_to_view()
        self.rectangle_selected.emit(0)  # The old selection no longer exists.

    def set_rectangles(self, rectangles: Sequence[CharacterRect]) -> None:
        """Draw one overlay per rectangle, replacing any previous overlays.

        Rectangle coordinates are original-image pixels. Because the image is
        added to the scene at 1:1, scene coordinates equal original-image
        coordinates and the view transform handles all display scaling.
        """
        if self._pixmap_item is None:
            return  # No image loaded: nothing to overlay.

        self._scene.blockSignals(True)
        for item in self._rect_items:
            self._scene.removeItem(item)
        self._scene.blockSignals(False)
        self._rect_items = [self._add_rect_overlay(rect) for rect in rectangles]
        self.rectangle_selected.emit(0)  # Fresh overlays start unselected.

    def _add_rect_overlay(self, rect: CharacterRect) -> RectOverlayItem:
        """Add the interactive overlay for one rectangle."""
        color = QColor(_RECT_COLOR_HEX[(rect.index - 1) % len(_RECT_COLOR_HEX)])

        item = RectOverlayItem(
            rect.index,
            QRectF(rect.x, rect.y, rect.width, rect.height),
            color,
            self._on_overlay_changed,
        )

        self._scene.addItem(item)
        return item

    def _on_overlay_changed(self, index: int, rect: QRectF) -> None:
        """Forward an overlay's new geometry to listeners."""
        self.rectangle_changed.emit(
            index, rect.x(), rect.y(), rect.width(), rect.height()
        )

    def _on_selection_changed(self) -> None:
        """Report which rectangle (if any) is now selected."""
        selected = [
            item
            for item in self._scene.selectedItems()
            if isinstance(item, RectOverlayItem)
        ]
        index = selected[0].character_index if selected else 0
        self.rectangle_selected.emit(index)

    def fit_to_view(self) -> None:
        """Scale the view so the whole image is visible."""
        if self._pixmap_item is not None:
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 (Qt API)
        super().resizeEvent(event)
        self.fit_to_view()