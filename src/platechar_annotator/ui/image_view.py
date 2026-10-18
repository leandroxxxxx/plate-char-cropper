"""Image display widget.

The original image is never resized: a QPixmap copy is displayed and the
view's transform scales it to fit the available area.
"""

from collections.abc import Sequence

from PIL import Image
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QPainter,
    QPen,
    QPixmap,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QWidget,
)

from platechar_annotator.models.selection import CharacterRect

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

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._rect_items: list[QGraphicsRectItem] = []

        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setBackgroundBrush(QBrush(QColor(40, 40, 40)))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def set_image(self, image: Image.Image) -> None:
        """Replace the displayed image, dropping any rectangle overlays."""
        self._scene.clear()
        self._rect_items = []  # clear() already deleted the overlay items.
        self._pixmap_item = self._scene.addPixmap(pil_to_qpixmap(image))
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self.fit_to_view()

    def set_rectangles(self, rectangles: Sequence[CharacterRect]) -> None:
        """Draw one overlay per rectangle, replacing any previous overlays.

        Rectangle coordinates are original-image pixels. Because the image is
        added to the scene at 1:1, scene coordinates equal original-image
        coordinates and the view transform handles all display scaling.
        """
        if self._pixmap_item is None:
            return  # No image loaded: nothing to overlay.

        for item in self._rect_items:
            self._scene.removeItem(item)
        self._rect_items = [self._add_rect_overlay(rect) for rect in rectangles]

    def _add_rect_overlay(self, rect: CharacterRect) -> QGraphicsRectItem:
        """Add the overlay (outline, tint, index label) for one rectangle."""
        color = QColor(_RECT_COLOR_HEX[(rect.index - 1) % len(_RECT_COLOR_HEX)])

        pen = QPen(color)
        pen.setWidth(2)
        pen.setCosmetic(True)  # Constant on-screen width at any zoom.

        tint = QColor(color)
        tint.setAlpha(40)

        item = QGraphicsRectItem(QRectF(rect.x, rect.y, rect.width, rect.height))
        item.setPen(pen)
        item.setBrush(QBrush(tint))
        item.setZValue(1)

        label = QGraphicsSimpleTextItem(str(rect.index), item)
        label.setBrush(QBrush(color))
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        # Keep the label a constant, readable size regardless of zoom.
        label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        label.setPos(rect.x, rect.y)

        self._scene.addItem(item)
        return item

    def fit_to_view(self) -> None:
        """Scale the view so the whole image is visible."""
        if self._pixmap_item is not None:
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 (Qt API)
        super().resizeEvent(event)
        self.fit_to_view()