"""Image display widget.

The original image is never resized: a QPixmap copy is displayed and the
view's transform scales it to fit or to the user's zoom level. The scene
stays 1:1 with the original image, so rectangle coordinates are always
stored in original-image pixels regardless of the on-screen zoom.
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
    QWheelEvent,
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

_ZOOM_STEP = 1.25  # Multiplier per click or wheel notch.
_ZOOM_MIN = 0.05
_ZOOM_MAX = 64.0


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
    """Displays an image that can be zoomed, keeping its aspect ratio."""

    # Emitted while a rectangle is moved or resized, with its new geometry:
    # (index, x, y, width, height) in original-image pixel coordinates.
    rectangle_changed = Signal(int, float, float, float, float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._rect_items: list[RectOverlayItem] = []
        self._manual_zoom = False  # True once the user zooms, until fit/reset.

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

    def fit_to_view(self) -> None:
        """Scale the view so the whole image is visible (drops the user zoom)."""
        self._manual_zoom = False
        if self._pixmap_item is not None:
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def zoom_in(self) -> None:
        """Zoom in one step around the viewport center."""
        self.zoom_by(_ZOOM_STEP)

    def zoom_out(self) -> None:
        """Zoom out one step around the viewport center."""
        self.zoom_by(1 / _ZOOM_STEP)

    def zoom_by(self, factor: float) -> None:
        """Multiply the zoom by ``factor``, clamped to sensible limits."""
        if self._pixmap_item is None:
            return
        self._manual_zoom = True
        current = self.transform().m11()
        target = max(_ZOOM_MIN, min(current * factor, _ZOOM_MAX))
        self.scale(target / current, target / current)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 (Qt API)
        """Scroll wheel zooms in (up) and out (down)."""
        factor = _ZOOM_STEP if event.angleDelta().y() > 0 else 1 / _ZOOM_STEP
        self.zoom_by(factor)
        event.accept()

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 (Qt API)
        super().resizeEvent(event)
        # Once the user has zoomed, keep the zoom level across resizes.
        if not self._manual_zoom:
            self.fit_to_view()