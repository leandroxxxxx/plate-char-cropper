"""Image display widget.

The original image is never resized: a QPixmap copy is displayed and the
view's transform scales it to fit or to the user's zoom level. The scene
stays 1:1 with the original image, so rectangle coordinates are always
stored in original-image pixels regardless of the on-screen zoom.
"""

from collections.abc import Sequence

from PIL import Image
from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QMouseEvent,
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
        self._pan_last_pos: QPoint | None = None  # Set while middle-dragging.
        self._aspect_ratio: float | None = None  # None = free resizing.

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

    def set_aspect_ratio(self, ratio: float | None) -> None:
        """Lock rectangle resizing to width/height == ratio (None = free).

        Applies to the current overlays and to any created later.
        """
        self._aspect_ratio = ratio
        for item in self._rect_items:
            item.set_aspect_ratio(ratio)

    def _add_rect_overlay(self, rect: CharacterRect) -> RectOverlayItem:
        """Add the interactive overlay for one rectangle."""
        color = QColor(_RECT_COLOR_HEX[(rect.index - 1) % len(_RECT_COLOR_HEX)])

        item = RectOverlayItem(
            rect.index,
            QRectF(rect.x, rect.y, rect.width, rect.height),
            color,
            self._on_overlay_changed,
        )
        item.set_aspect_ratio(self._aspect_ratio)

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

    def visible_image_rect(self) -> tuple[float, float, float, float] | None:
        """The part of the image currently visible, in original-image pixels.

        Returns ``(x, y, width, height)`` clipped to the image bounds, or None
        if no image is loaded or nothing of it is visible.
        """
        if self._pixmap_item is None:
            return None
        visible = self.mapToScene(self.viewport().rect()).boundingRect()
        visible = visible.intersected(self._scene.sceneRect())
        if visible.width() <= 0 or visible.height() <= 0:
            return None
        return (visible.x(), visible.y(), visible.width(), visible.height())

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 (Qt API)
        """Scroll wheel zooms in (up) and out (down), around the cursor."""
        factor = _ZOOM_STEP if event.angleDelta().y() > 0 else 1 / _ZOOM_STEP
        # Keep the image point under the cursor fixed, so the user can zoom
        # straight into the part of interest.
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.zoom_by(factor)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt API)
        """Middle button starts panning; other buttons behave as usual."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_last_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt API)
        if self._pan_last_pos is not None:
            pos = event.position().toPoint()
            delta = pos - self._pan_last_pos
            self._pan_last_pos = pos
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt API)
        if (
            event.button() == Qt.MouseButton.MiddleButton
            and self._pan_last_pos is not None
        ):
            self._pan_last_pos = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 (Qt API)
        super().resizeEvent(event)
        # Once the user has zoomed, keep the zoom level across resizes.
        if not self._manual_zoom:
            self.fit_to_view()