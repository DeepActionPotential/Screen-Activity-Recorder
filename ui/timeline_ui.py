# dual_streamline_with_clickable_preview_timeline_refactor.py
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Callable, Dict

from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtCore import Qt, QRect, QPoint
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QBrush, QLinearGradient, QPixmap, QMouseEvent

from schemas.activity_schemas import Activity, ApplicationActivity, ScreenshotActivity
from ui.utils import pil_to_qpixmap


# --- Lightweight value objects to improve cohesion ---
@dataclass
class Clip:
    """Represents a time-span (application activity) rendered as a rectangular clip."""
    activity: ApplicationActivity
    rect: QRect
    lane: int = 0


@dataclass
class Marker:
    """Represents a single-point (screenshot) marker rendered as a square thumbnail."""
    activity: ScreenshotActivity
    rect: QRect


class TimelineWidget(QWidget):
    """
    A compact timeline widget that renders application activity clips and screenshot markers
    and exposes a draggable playhead.

    This refactor keeps the original behavior but improves cohesion by splitting
    layout/painting/interaction responsibilities, adding typing and docstrings,
    and introducing small value objects for clips/markers.
    """

    # layout constants (tweakable)
    _LEFT_PADDING: int = 12
    _RIGHT_PADDING: int = 12
    MIN_CLIP_GAP: int = 10

    def __init__(
        self,
        activities: List[Activity],
        min_t: int,
        max_t: int,
        activity_filter: str,
        preview_callback: Callable[[float], None],
        select_callback: Callable[[Activity], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize timeline widget.

        Args:
            activities: list of Activity objects (ApplicationActivity or ScreenshotActivity).
            min_t: minimum timestamp (unix seconds) for left edge of the timeline.
            max_t: maximum timestamp (unix seconds) for right edge of the timeline.
            activity_filter: either 'screenshot' or any other string meaning app activities.
            preview_callback: called with a float timestamp while previewing/dragging.
            select_callback: called with an Activity when user clicks a clip/marker.
            parent: optional QWidget parent.
        """
        super().__init__(parent)
        # public configuration
        self.activities_all: List[Activity] = activities
        self.activity_filter: str = activity_filter
        self.preview_callback = preview_callback
        self.select_callback = select_callback

        # visual sizing (can be tuned)
        self.ruler_height: int = 10
        self.lane_h: int = 25
        self.lane_sp: int = 6
        self.marker_size: int = 50

        self.setMinimumHeight(self.ruler_height + self.lane_h + self.lane_sp + self.marker_size + 10)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # timeline range
        self.min_t: int = int(min_t)
        self.max_t: int = int(max_t)
        if self.max_t <= self.min_t:
            self.max_t = self.min_t + 1
        self.total_span: int = max(1, int(self.max_t - self.min_t))

        # playhead and dragging state
        self.playhead: float = float(self.min_t)
        self.dragging: bool = False
        self.handle_radius: int = 6

        # geometry containers
        self.clips: List[Clip] = []
        self.markers: List[Marker] = []

        # thumbnail cache: screenshot_id -> QPixmap|None
        self._marker_thumb_cache: Dict[str, Optional[QPixmap]] = {}

        # initial layout
        self._layout_activities()
        self.setFocusPolicy(Qt.ClickFocus)

    # ---------------------- activity filtering & layout ----------------------
    def _visible_activities(self) -> List[Activity]:
        """Return activities filtered by the configured activity_filter."""
        if self.activity_filter == "screenshot":
            return [a for a in self.activities_all if not isinstance(a, ApplicationActivity)]
        return [a for a in self.activities_all if isinstance(a, ApplicationActivity)]

    def _compute_usable_width(self) -> int:
        """Compute the horizontal space available for the timeline content."""
        return max(1, self.width() - self._LEFT_PADDING - self._RIGHT_PADDING)

    def _time_to_x_int(self, t_int: int) -> int:
        """Convert an integer unix timestamp to an X coordinate (int).

        This mirrors :meth:`time_to_x` but accepts/returns integers to be used
        when computing rects.
        """
        frac = (t_int - self.min_t) / max(1, self.total_span)
        return self._LEFT_PADDING + int(frac * self._compute_usable_width())

    def _ensure_thumb_cached(self, a: ScreenshotActivity) -> None:
        """Ensure a thumbnail entry exists in the cache for a screenshot activity.

        If an image exists on the activity (original_screenshot_pil_image), convert
        it to a QPixmap and scale it to marker_size keeping the original aspect via
        KeepAspectRatioByExpanding (matching original behaviour).
        """
        if a.screenshot_id in self._marker_thumb_cache:
            return
        try:
            pil_img = getattr(a, "modified_screenshot_pil_image", None)
            if pil_img is not None:
                qpix = pil_to_qpixmap(pil_img)
                thumb = qpix.scaled(self.marker_size, self.marker_size,
                                    Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self._marker_thumb_cache[a.screenshot_id] = thumb
            else:
                self._marker_thumb_cache[a.screenshot_id] = None
        except Exception:
            # preserve original behaviour: store None on failure
            self._marker_thumb_cache[a.screenshot_id] = None

    def _layout_activities(self) -> None:
        """Compute clip and marker rectangles from the current activities and widget size.

        This populates self.clips and self.markers with Clip/Marker instances.
        """
        w = max(600, int(self.width() if self.width() > 0 else 900))
        usable = w - self._LEFT_PADDING - self._RIGHT_PADDING
        lane_y0 = self.ruler_height + 10

        self.clips = []
        self.markers = []

        visible_ids = set()

        for a in self._visible_activities():
            if isinstance(a, ApplicationActivity):
                start = int(a.app_activity_timestamp.timestamp())
                end = start + max(1, int(a.duration_seconds))
                x1 = self._time_to_x_int(start)
                x2 = self._time_to_x_int(end)
                if x2 - x1 < 8:
                    x2 = x1 + 8
                rect = QRect(x1, lane_y0, x2 - x1, self.lane_h)
                self.clips.append(Clip(a, rect, 0))
            else:
                t = int(a.screenshot_timestamp.timestamp())
                x = self._time_to_x_int(t)
                marker_y = lane_y0 + self.lane_h + self.lane_sp
                rect = QRect(x - self.marker_size // 2, marker_y, self.marker_size, self.marker_size)
                self.markers.append(Marker(a, rect))
                visible_ids.add(a.screenshot_id)
                # ensure cache exists (but do not block/raise)
                self._ensure_thumb_cached(a)
            

    def resizeEvent(self, e) -> None:  # type: ignore
        """Recompute layout when widget is resized (preserve thumbnail cache)."""
        self._layout_activities()
        super().resizeEvent(e)

    # ---------------------- painting ----------------------
    def paintEvent(self, e) -> None:  # type: ignore
        """Paint timeline background, ruler, clips, markers and playhead."""
        p = QPainter(self)
        r = self.rect()
        p.fillRect(r, QColor(24, 24, 24))
        self._paint_ruler(p, r)
        for clip in self.clips:
            self._paint_clip(p, clip)
        for marker in self.markers:
            self._paint_marker(p, marker)
        self._paint_playhead(p)

    def _paint_ruler(self, p: QPainter, r: QRect) -> None:
        """Draw top ruler with tick marks and time labels."""
        p.save()
        p.setPen(QColor(130, 130, 130))
        p.setFont(QFont("Segoe UI", 8))
        ticks = 8
        tick_top = 6
        tick_bottom = max(10, self.ruler_height - 6)
        for i in range(ticks + 1):
            frac = i / ticks
            x = int(r.left() + self._LEFT_PADDING + frac * (r.width() - (self._LEFT_PADDING + self._RIGHT_PADDING)))
            p.drawLine(x, tick_top, x, tick_bottom)
            t = int(self.min_t + frac * self.total_span)
            tstr = datetime.fromtimestamp(t).strftime("%H:%M:%S")
            p.drawText(x - 25, 0, 50, self.ruler_height, Qt.AlignCenter, tstr)
        p.restore()

    def _paint_clip(self, p: QPainter, clip: Clip) -> None:
        """Paint a single application clip rectangle with label and border."""
        a = clip.activity
        rect = clip.rect
        p.save()

        base_top = (18, 75, 150)
        base_bottom = (10, 45, 110)

        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0.0, QColor(*base_top, 255))
        grad.setColorAt(1.0, QColor(*base_bottom, 255))
        p.setBrush(QBrush(grad))

        p.setPen(Qt.NoPen)
        p.drawRect(rect)

        border_color = QColor(max(0, base_bottom[0] - 10), max(0, base_bottom[1] - 10), max(0, base_bottom[2] - 20))
        pen = QPen(border_color)
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRect(rect.adjusted(0, 0, -1, -1))

        p.setPen(QColor(255, 255, 255))
        p.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        txt = a.app_name if len(a.app_name) <= 24 else a.app_name[:22] + "…"
        p.drawText(rect.adjusted(8, 0, -6, 0), Qt.AlignVCenter | Qt.AlignLeft, txt)

        p.restore()

    def _paint_marker(self, p: QPainter, marker: Marker) -> None:
        """Paint a screenshot marker; if a thumbnail exists in cache, draw it."""
        a = marker.activity
        rect = marker.rect
        p.save()
        p.setPen(QColor(100, 100, 100))
        p.setBrush(QColor(30, 30, 30))
        p.drawRect(rect)

        thumb = self._marker_thumb_cache.get(a.screenshot_id)
        if thumb:
            p.drawPixmap(rect, thumb)
            p.setPen(QColor(80, 80, 80))
            p.setBrush(Qt.NoBrush)
            p.drawRect(rect.adjusted(0, 0, -1, -1))
        else:
            p.setBrush(QColor(255, 183, 77, 220))
            p.setPen(QColor(200, 140, 20))
            p.drawRect(rect)
            p.setPen(QColor(30, 30, 30))
            p.setFont(QFont("Segoe UI", 8))
            p.drawText(rect, Qt.AlignCenter, a.screenshot_id[-3:])
        p.restore()

    def _paint_playhead(self, p: QPainter) -> None:
        """Draw the vertical playhead line, circular handle and the time tooltip."""
        p.save()
        x = int(self.time_to_x(self.playhead))
        p.setPen(QPen(QColor(255, 255, 255), 1))
        p.drawLine(x, 0, x, self.height())

        cx = self.ruler_height // 2
        p.setBrush(QColor(255, 255, 255))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPoint(x, cx), int(self.handle_radius), int(self.handle_radius))

        t_int = int(round(self.playhead))
        tstr = datetime.fromtimestamp(t_int).strftime("%H:%M:%S")
        tw, th = 70, 20
        label_y = self.ruler_height + 6
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(32, 32, 32, 220))
        p.drawRect(x - tw // 2, label_y, tw, th)
        p.setPen(QColor(220, 220, 220))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(x - tw // 2, label_y, tw, th, Qt.AlignCenter, tstr)
        p.restore()

    # ---------------------- coordinate helpers ----------------------
    def time_to_x(self, t_float: float) -> int:
        """Convert a float timestamp to an X coordinate (keeps behaviour of original).

        Args:
            t_float: timestamp in seconds (float)
        Returns:
            x coordinate (int)
        """
        frac = (float(t_float) - self.min_t) / max(1, self.total_span)
        return self._LEFT_PADDING + int(frac * self._compute_usable_width())

    def set_playhead(self, t_float: float) -> None:
        """Set the playhead position to the given timestamp and repaint.

        This method restores the original public API used elsewhere in the
        application (e.g. `history_ui.py`) — it simply updates the internal
        playhead and schedules a repaint.

        Args:
            t_float: timestamp (seconds) to set the playhead to.
        """
        self.playhead = t_float
        self.update()

    def x_to_time(self, x: int) -> float:
        """Convert an X coordinate to a float timestamp clamped to the timeline range."""
        usable = self._compute_usable_width()
        frac = (x - self._LEFT_PADDING) / max(1, usable)
        frac = max(0.0, min(1.0, frac))
        return float(self.min_t + int(frac * self.total_span))

    # ---------------------- interactions (mouse) ----------------------
    def mousePressEvent(self, ev: QMouseEvent) -> None:  # type: ignore
        """Handle clicks on the playhead, clips or markers.

        If the user clicks near the playhead within the ruler area, begin dragging.
        Clicking clips/markers will set the playhead and call select/preview callbacks.
        """
        x, y = ev.x(), ev.y()
        hx = self.time_to_x(self.playhead)
        if abs(x - hx) <= 12 and y <= (self.ruler_height + 8):
            self.dragging = True
            return

        for clip in self.clips:
            if clip.rect.contains(int(x), int(y)):
                self.playhead = float(int(clip.activity.app_activity_timestamp.timestamp()))
                self.select_callback(clip.activity)
                self.preview_callback(self.playhead)
                self.update()
                return

        for marker in self.markers:
            if marker.rect.contains(int(x), int(y)):
                self.playhead = float(int(marker.activity.screenshot_timestamp.timestamp()))
                self.select_callback(marker.activity)
                self.preview_callback(self.playhead)
                self.update()
                return

    def mouseMoveEvent(self, ev: QMouseEvent) -> None:  # type: ignore
        """While dragging, update the playhead position and call preview callback."""
        if self.dragging:
            t = self.x_to_time(ev.x())
            self.playhead = t
            self.preview_callback(self.playhead)
            self.update()

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:  # type: ignore
        """On mouse release finish drag and send final preview event."""
        if self.dragging:
            self.dragging = False
            self.preview_callback(self.playhead)
            self.update()
