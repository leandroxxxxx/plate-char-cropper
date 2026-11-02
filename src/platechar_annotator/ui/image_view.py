"""Image display widget.

The original image is never resized: a QPixmap copy is displayed and the
view's transform scales it to fit or to the user's zoom level. The scene
stays 1:1 with the original image, so rectangle coordinates are always
stored in original-image pixels regardless of the on-screen zoom.
"""

from collections.abc import Sequence

from PIL import Image
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPaintEvent,
    QPainter,
    QPen,
    QPixmap,
    QResizeEvent,
    QTransform,
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
from platechar_annotator.services.local_config import load_zoom_step_fraction
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

_ZOOM_MIN = 0.05
_ZOOM_MAX = 64.0
_MAX_BICUBIC_PIXELS = 16_000_000


def pil_to_qpixmap(image: Image.Image) -> QPixmap:
    """Convert a PIL image to a QPixmap for display (the PIL image is not modified)."""
    rgba = image.convert("RGBA")
    data = rgba.tobytes()
    qimage = QImage(
        data, rgba.width, rgba.height, rgba.width * 4, QImage.Format.Format_RGBA8888
    )
    # copy() detaches the QImage from the temporary bytes buffer.
    return QPixmap.fromImage(qimage.copy())


class ImagePreview(QFrame):
    """Small frame displaying the full image context and current visible region."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(160, 110)
        self.setStyleSheet(
            "QFrame { background-color: #202020; border: 1px solid #555; border-radius: 4px; }"
        )
        self._pixmap: QPixmap | None = None
        self._image_size: tuple[int, int] = (1, 1)
        self._view_rect: tuple[float, float, float, float] | None = None

    def set_image(self, image: Image.Image | None) -> None:
        """Update thumbnail pixmap from the loaded PIL image."""
        if image is None:
            self._pixmap = None
            self._view_rect = None
            self.update()
            return

        self._image_size = (image.width, image.height)
        qpix = pil_to_qpixmap(image)
        inner_w = max(1, self.width() - 4)
        inner_h = max(1, self.height() - 4)
        self._pixmap = qpix.scaled(
            inner_w,
            inner_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.update()

    def set_view_rect(self, rect: tuple[float, float, float, float] | None) -> None:
        """Update the region currently visible in the main image view."""
        self._view_rect = rect
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 (Qt API)
        super().paintEvent(event)
        painter = QPainter(self)
        if self._pixmap is None:
            painter.setPen(QColor(120, 120, 120))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No image")
            return

        pm_w = self._pixmap.width()
        pm_h = self._pixmap.height()
        x = (self.width() - pm_w) // 2
        y = (self.height() - pm_h) // 2
        painter.drawPixmap(x, y, self._pixmap)

        if self._view_rect and self._image_size[0] > 0 and self._image_size[1] > 0:
            vx, vy, vw, vh = self._view_rect
            img_w, img_h = self._image_size
            if vw < img_w * 0.99 or vh < img_h * 0.99:
                rx = x + (vx / img_w) * pm_w
                ry = y + (vy / img_h) * pm_h
                rw = max(2.0, (vw / img_w) * pm_w)
                rh = max(2.0, (vh / img_h) * pm_h)
                painter.setPen(QPen(QColor(0, 180, 255), 1.5))
                painter.setBrush(QBrush(QColor(0, 180, 255, 40)))
                painter.drawRect(QRectF(rx, ry, rw, rh))


class ImageView(QGraphicsView):
    """Displays an image that can be zoomed, keeping its aspect ratio."""

    # Emitted while a rectangle is moved or resized, with its new geometry:
    # (index, x, y, width, height) in original-image pixel coordinates.
    rectangle_changed = Signal(int, float, float, float, float)
    rectangle_deleted = Signal(int)
    selection_changed = Signal(int)
    view_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._scene.selectionChanged.connect(self._emit_selection_changed)
        self.setScene(self._scene)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._display_image: Image.Image | None = None
        self._rect_items: list[RectOverlayItem] = []
        self._manual_zoom = False  # True once the user zooms, until fit/reset.
        self._pan_last_pos: QPoint | None = None  # Set while middle-dragging.
        self._aspect_ratio: float | None = None  # None = free resizing.
        self._zoom_step_fraction = load_zoom_step_fraction()

        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setBackgroundBrush(QBrush(QColor(40, 40, 40)))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def set_image(self, image: Image.Image, preserve_zoom: bool = False) -> None:
        """Replace the displayed image, dropping any rectangle overlays."""
        should_preserve = (
            preserve_zoom
            and self._manual_zoom
            and self._display_image is not None
            and self._pixmap_item is not None
        )
        center_scene = (
            self.mapToScene(self.viewport().rect().center())
            if should_preserve
            else None
        )

        self._rect_items = []
        self._scene.clear()
        self._display_image = image.convert("RGBA")
        self._pixmap_item = self._scene.addPixmap(pil_to_qpixmap(self._display_image))
        self._scene.setSceneRect(self._pixmap_item.sceneBoundingRect())
        if should_preserve and center_scene is not None:
            new_w, new_h = self._display_image.size
            clamped_center = QPointF(
                max(0.0, min(center_scene.x(), float(new_w))),
                max(0.0, min(center_scene.y(), float(new_h))),
            )
            self.centerOn(clamped_center)
            self._update_bicubic_pixmap()
        else:
            self.fit_to_view()
        self.view_changed.emit()

    def _update_bicubic_pixmap(self) -> None:
        """Resample the display image at the current view scale with bicubic filtering.

        The pixmap is drawn with an inverse item transform, preserving the
        original image's scene bounds so overlays and crop coordinates remain
        aligned. A pixel cap limits memory use at very high zoom levels; Qt's
        smooth transform handles any remaining scale beyond that cap.
        """
        if self._display_image is None or self._pixmap_item is None:
            return

        view_scale = max(self.transform().m11(), 1e-6)
        source_width, source_height = self._display_image.size
        requested_pixels = source_width * source_height * view_scale * view_scale
        render_scale = view_scale
        if requested_pixels > _MAX_BICUBIC_PIXELS:
            render_scale *= (_MAX_BICUBIC_PIXELS / requested_pixels) ** 0.5

        target_size = (
            max(1, round(source_width * render_scale)),
            max(1, round(source_height * render_scale)),
        )
        if render_scale == 1.0:
            rendered = self._display_image
        else:
            rendered = self._display_image.resize(
                target_size, Image.Resampling.BICUBIC
            )

        self._pixmap_item.setPixmap(pil_to_qpixmap(rendered))
        inverse_x = source_width / target_size[0]
        inverse_y = source_height / target_size[1]
        self._pixmap_item.setTransform(QTransform.fromScale(inverse_x, inverse_y))
        self._pixmap_item.setTransformationMode(
            Qt.TransformationMode.SmoothTransformation
        )

    def set_rectangles(self, rectangles: Sequence[CharacterRect]) -> None:
        """Draw one overlay per rectangle, replacing any previous overlays.

        Rectangle coordinates are original-image pixels. Because the image is
        added to the scene at 1:1, scene coordinates equal original-image
        coordinates and the view transform handles all display scaling.
        """
        if self._pixmap_item is None:
            return  # No image loaded: nothing to overlay.

        old_items = self._rect_items
        self._rect_items = []
        for item in old_items:
            self._scene.removeItem(item)
        self._rect_items = [self._add_rect_overlay(rect) for rect in rectangles]

    def delete_selected_rectangle(self) -> bool:
        """Remove the selected character rectangle, if there is one."""
        selected = next(
            (item for item in self._rect_items if item.isSelected()), None
        )
        if selected is None:
            return False
        index = selected.character_index
        self._rect_items.remove(selected)
        self._scene.removeItem(selected)
        self.rectangle_deleted.emit(index)
        return True

    def _emit_selection_changed(self) -> None:
        selected_index = next(
            (
                item.character_index
                for item in self._rect_items
                if item.isSelected()
            ),
            -1,
        )
        self.selection_changed.emit(selected_index)

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
            self._update_bicubic_pixmap()
            self.view_changed.emit()

    def zoom_in(self) -> None:
        """Zoom in one step around the viewport center."""
        self.zoom_by(1 + self._zoom_step_fraction)

    def zoom_out(self) -> None:
        """Zoom out one step around the viewport center."""
        self.zoom_by(1 / (1 + self._zoom_step_fraction))

    def zoom_by(self, factor: float) -> None:
        """Multiply the zoom by ``factor``, clamped to sensible limits."""
        if self._pixmap_item is None:
            return
        self._manual_zoom = True
        current = self.transform().m11()
        target = max(_ZOOM_MIN, min(current * factor, _ZOOM_MAX))
        self.scale(target / current, target / current)
        self._update_bicubic_pixmap()
        self.view_changed.emit()

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
        delta = event.angleDelta().y() or event.pixelDelta().y()
        if delta == 0:
            event.accept()
            return
        factor = (1 + self._zoom_step_fraction) ** (delta / 120)
        # Keep the image point under the cursor fixed, so the user can zoom
        # straight into the part of interest.
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.zoom_by(factor)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (Qt API)
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self.delete_selected_rectangle():
                event.accept()
                return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt API)
        """Middle button starts panning; other buttons behave as usual."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_last_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        self.setFocus(Qt.FocusReason.MouseFocusReason)
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
            self.view_changed.emit()
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
        self.view_changed.emit()
