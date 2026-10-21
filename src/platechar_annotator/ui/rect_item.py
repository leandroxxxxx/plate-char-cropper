"""Interactive rectangle overlay: drag to move, drag edges/corners to resize.

The scene's coordinates equal original-image pixels (the image is added to the
scene at 1:1), so all drag math below happens directly in original-image
pixels. The view's display scale only affects the on-screen size of handles
and hit zones, never the stored geometry.
"""

from collections.abc import Callable
from enum import IntFlag
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QCursor, QPen, QTransform
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsSceneHoverEvent,
    QGraphicsSceneMouseEvent,
    QGraphicsSimpleTextItem,
)

_HANDLE_PX = 8  # On-screen handle size and edge hit zone, in screen pixels.
_MIN_SIZE = 2.0  # Minimum rectangle width/height, in original-image pixels.

_PEN_WIDTH = 2
_PEN_WIDTH_ACTIVE = 3
_TINT_ALPHA = 40
_TINT_ALPHA_ACTIVE = 90
_Z_NORMAL = 1.0
_Z_ACTIVE = 2.0

# Handle anchor points as fractions of the rectangle (x, y): corners and edge
# midpoints. Handles are drawn inside the rectangle so the hit zone matches.
_HANDLE_FRACTIONS = [
    (0.0, 0.0),
    (0.5, 0.0),
    (1.0, 0.0),
    (0.0, 0.5),
    (1.0, 0.5),
    (0.0, 1.0),
    (0.5, 1.0),
    (1.0, 1.0),
]


class _Edge(IntFlag):
    """Edges a drag is attached to. NONE means the whole rectangle moves."""

    NONE = 0
    LEFT = 1
    RIGHT = 2
    TOP = 4
    BOTTOM = 8


_CURSORS = {
    _Edge.NONE: Qt.CursorShape.SizeAllCursor,
    _Edge.LEFT: Qt.CursorShape.SizeHorCursor,
    _Edge.RIGHT: Qt.CursorShape.SizeHorCursor,
    _Edge.TOP: Qt.CursorShape.SizeVerCursor,
    _Edge.BOTTOM: Qt.CursorShape.SizeVerCursor,
    _Edge.LEFT | _Edge.TOP: Qt.CursorShape.SizeFDiagCursor,
    _Edge.RIGHT | _Edge.BOTTOM: Qt.CursorShape.SizeFDiagCursor,
    _Edge.RIGHT | _Edge.TOP: Qt.CursorShape.SizeBDiagCursor,
    _Edge.LEFT | _Edge.BOTTOM: Qt.CursorShape.SizeBDiagCursor,
}


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp value to [low, high]; if the range is inverted, return low."""
    return max(low, min(value, high))


def _moved_rect(start: QRectF, dx: float, dy: float, bounds: QRectF) -> QRectF:
    """Translate a rectangle by (dx, dy), keeping it inside bounds."""
    x = _clamp(start.x() + dx, bounds.left(), bounds.right() - start.width())
    y = _clamp(start.y() + dy, bounds.top(), bounds.bottom() - start.height())
    return QRectF(x, y, start.width(), start.height())


def _resized_rect(
    start: QRectF, edges: _Edge, dx: float, dy: float, bounds: QRectF
) -> QRectF:
    """Move the given edges by (dx, dy), keeping the minimum size and bounds."""
    left, top, right, bottom = start.left(), start.top(), start.right(), start.bottom()
    if edges & _Edge.LEFT:
        left = _clamp(left + dx, bounds.left(), right - _MIN_SIZE)
    if edges & _Edge.RIGHT:
        right = _clamp(right + dx, left + _MIN_SIZE, bounds.right())
    if edges & _Edge.TOP:
        top = _clamp(top + dy, bounds.top(), bottom - _MIN_SIZE)
    if edges & _Edge.BOTTOM:
        bottom = _clamp(bottom + dy, top + _MIN_SIZE, bounds.bottom())
    return QRectF(QPointF(left, top), QPointF(right, bottom))


def _axis(
    start_low: float,
    start_high: float,
    drag_low: bool,
    delta: float,
    bound_low: float,
    bound_high: float,
) -> tuple[float, float, float]:
    """Resolve one axis of a drag.

    Returns ``(anchor, desired_length, room)``: the fixed coordinate (the side
    opposite the dragged one), the length the cursor asks for, and the space
    between the anchor and the bound on the dragged side.
    """
    if drag_low:
        return start_high, start_high - (start_low + delta), start_high - bound_low
    return start_low, (start_high + delta) - start_low, bound_high - start_low


def _locked_extent(desired: float, minimum: float, maximum: float) -> float | None:
    """Clamp ``desired`` to [minimum, maximum]; None if that range is empty."""
    if maximum < minimum:
        return None
    return min(max(desired, minimum), maximum)


def _resized_rect_locked(
    start: QRectF, edges: _Edge, dx: float, dy: float, bounds: QRectF, ratio: float
) -> QRectF:
    """Like ``_resized_rect`` but keeps ``width / height == ratio``.

    A dragged corner keeps the opposite corner fixed. A dragged side edge keeps
    the opposite edge fixed and centres the other dimension on the start
    rectangle. The result stays inside bounds and above the minimum size; if no
    such size exists, the start rectangle is returned unchanged.
    """
    on_left = bool(edges & _Edge.LEFT)
    on_top = bool(edges & _Edge.TOP)
    horizontal = on_left or bool(edges & _Edge.RIGHT)
    vertical = on_top or bool(edges & _Edge.BOTTOM)
    if not (horizontal or vertical):
        return QRectF(start)

    center = start.center()
    min_width = max(_MIN_SIZE, _MIN_SIZE * ratio)
    min_height = max(_MIN_SIZE, _MIN_SIZE / ratio)

    if horizontal and vertical:  # Corner: the opposite corner stays fixed.
        anchor_x, desired_w, room_x = _axis(
            start.left(), start.right(), on_left, dx, bounds.left(), bounds.right()
        )
        anchor_y, desired_h, room_y = _axis(
            start.top(), start.bottom(), on_top, dy, bounds.top(), bounds.bottom()
        )
        width = _locked_extent(
            max(desired_w, desired_h * ratio), min_width, min(room_x, room_y * ratio)
        )
        if width is None:
            return QRectF(start)
        height = width / ratio
        left = anchor_x - width if on_left else anchor_x
        top = anchor_y - height if on_top else anchor_y
        return QRectF(left, top, width, height)

    if horizontal:  # Left or right edge: height follows, centred vertically.
        anchor_x, desired_w, room_x = _axis(
            start.left(), start.right(), on_left, dx, bounds.left(), bounds.right()
        )
        room_y = 2 * min(center.y() - bounds.top(), bounds.bottom() - center.y())
        width = _locked_extent(desired_w, min_width, min(room_x, room_y * ratio))
        if width is None:
            return QRectF(start)
        height = width / ratio
        left = anchor_x - width if on_left else anchor_x
        return QRectF(left, center.y() - height / 2, width, height)

    # Top or bottom edge: width follows, centred horizontally.
    anchor_y, desired_h, room_y = _axis(
        start.top(), start.bottom(), on_top, dy, bounds.top(), bounds.bottom()
    )
    room_x = 2 * min(center.x() - bounds.left(), bounds.right() - center.x())
    height = _locked_extent(desired_h, min_height, min(room_y, room_x / ratio))
    if height is None:
        return QRectF(start)
    width = height * ratio
    top = anchor_y - height if on_top else anchor_y
    return QRectF(center.x() - width / 2, top, width, height)


class RectOverlayItem(QGraphicsRectItem):
    """A character rectangle that can be selected, moved and resized.

    The item's position stays at the scene origin; moving or resizing changes
    its rect, so ``rect()`` is always in original-image pixel coordinates.
    """

    def __init__(
        self,
        character_index: int,
        rect: QRectF,
        color: QColor,
        on_changed: Callable[[int, QRectF], None],
    ) -> None:
        super().__init__(rect)
        self.character_index = character_index
        self._color = QColor(color)
        self._on_changed = on_changed
        self._aspect_ratio: float | None = None  # None = free resizing.

        self._drag_edges = _Edge.NONE
        self._drag_start_scene: QPointF | None = None
        self._drag_start_rect: QRectF | None = None

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)

        self._label = self._create_label()
        self._handles = self._create_handles()
        self._apply_style(selected=False)
        self._update_children()

    def set_aspect_ratio(self, ratio: float | None) -> None:
        """Lock resizing to width/height == ratio, or free it with None.

        Only edge and corner drags are affected. The current shape is kept
        until the next resize, which then snaps to the ratio.
        """
        self._aspect_ratio = ratio if ratio is not None and ratio > 0 else None

    # ----- construction helpers -----

    def _create_label(self) -> QGraphicsSimpleTextItem:
        label = QGraphicsSimpleTextItem(str(self.character_index), self)
        label.setBrush(QBrush(self._color))
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        # Constant, readable size at any zoom, nudged clear of the corner handle.
        label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        label.setTransform(QTransform.fromTranslate(_HANDLE_PX + 2, 1))
        label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        return label

    def _create_handles(self) -> list[QGraphicsRectItem]:
        pen = QPen(self._color)
        pen.setWidth(1)
        pen.setCosmetic(True)

        handles = []
        for fx, fy in _HANDLE_FRACTIONS:
            # Local rect offset so the handle sits inside its anchor point.
            local = QRectF(-_HANDLE_PX * fx, -_HANDLE_PX * fy, _HANDLE_PX, _HANDLE_PX)
            handle = QGraphicsRectItem(local, self)
            handle.setPen(pen)
            handle.setBrush(QBrush(Qt.GlobalColor.white))
            handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
            handle.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            handle.setVisible(False)
            handles.append(handle)
        return handles

    # ----- appearance -----

    def _apply_style(self, selected: bool) -> None:
        """Update outline, tint, stacking order and handles for the active state."""
        pen = QPen(self._color)
        pen.setWidth(_PEN_WIDTH_ACTIVE if selected else _PEN_WIDTH)
        pen.setCosmetic(True)  # Constant on-screen width at any zoom.
        self.setPen(pen)

        tint = QColor(self._color)
        tint.setAlpha(_TINT_ALPHA_ACTIVE if selected else _TINT_ALPHA)
        self.setBrush(QBrush(tint))

        self.setZValue(_Z_ACTIVE if selected else _Z_NORMAL)
        for handle in self._handles:
            handle.setVisible(selected)

    def _update_children(self) -> None:
        """Re-anchor the label and handles to the current rectangle."""
        rect = self.rect()
        for handle, (fx, fy) in zip(self._handles, _HANDLE_FRACTIONS):
            handle.setPos(rect.x() + rect.width() * fx, rect.y() + rect.height() * fy)
        self._label.setPos(rect.topLeft())

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._apply_style(bool(value))
        return super().itemChange(change, value)

    # ----- hit testing -----

    def _view_scale(self) -> float:
        """Screen pixels per scene unit (original-image pixel) in the first view."""
        scene = self.scene()
        views = scene.views() if scene is not None else []
        scale = views[0].transform().m11() if views else 1.0
        return scale if scale > 0 else 1.0

    def _edges_at(self, pos: QPointF) -> _Edge:
        """Which edges the point is close enough to grab (NONE = move)."""
        rect = self.rect()
        # The edge zone never takes more than a third of the smaller side, so a
        # grabbable body area always remains.
        tolerance = min(
            _HANDLE_PX / self._view_scale(), min(rect.width(), rect.height()) / 3
        )
        edges = _Edge.NONE
        if pos.x() - rect.left() <= tolerance:
            edges |= _Edge.LEFT
        elif rect.right() - pos.x() <= tolerance:
            edges |= _Edge.RIGHT
        if pos.y() - rect.top() <= tolerance:
            edges |= _Edge.TOP
        elif rect.bottom() - pos.y() <= tolerance:
            edges |= _Edge.BOTTOM
        return edges

    # ----- mouse interaction -----

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent) -> None:  # noqa: N802
        self.setCursor(QCursor(_CURSORS[self._edges_at(event.pos())]))
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        self.scene().clearSelection()
        self.setSelected(True)
        self._drag_edges = self._edges_at(event.pos())
        self._drag_start_scene = event.scenePos()
        self._drag_start_rect = QRectF(self.rect())
        event.accept()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:  # noqa: N802
        if self._drag_start_rect is None or self._drag_start_scene is None:
            event.ignore()
            return
        delta = event.scenePos() - self._drag_start_scene
        bounds = self.scene().sceneRect()
        if self._drag_edges == _Edge.NONE:
            new_rect = _moved_rect(self._drag_start_rect, delta.x(), delta.y(), bounds)
        elif self._aspect_ratio is None:
            new_rect = _resized_rect(
                self._drag_start_rect, self._drag_edges, delta.x(), delta.y(), bounds
            )
        else:
            new_rect = _resized_rect_locked(
                self._drag_start_rect,
                self._drag_edges,
                delta.x(),
                delta.y(),
                bounds,
                self._aspect_ratio,
            )
        self._set_geometry(new_rect)
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:  # noqa: N802
        self._drag_edges = _Edge.NONE
        self._drag_start_scene = None
        self._drag_start_rect = None
        event.accept()

    def _set_geometry(self, rect: QRectF) -> None:
        """Apply new geometry and notify the owner if it actually changed."""
        if rect == self.rect():
            return
        self.setRect(rect)
        self._update_children()
        self._on_changed(self.character_index, rect)