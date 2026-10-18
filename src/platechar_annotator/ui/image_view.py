"""Image display widget.

The original image is never resized: a QPixmap copy is displayed and the
view's transform scales it to fit the available area.
"""

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QWidget,
)


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

        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setBackgroundBrush(QBrush(QColor(40, 40, 40)))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def set_image(self, image: Image.Image) -> None:
        """Replace the displayed image."""
        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(pil_to_qpixmap(image))
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self.fit_to_view()

    def fit_to_view(self) -> None:
        """Scale the view so the whole image is visible."""
        if self._pixmap_item is not None:
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 (Qt API)
        super().resizeEvent(event)
        self.fit_to_view()