"""Refactored DualStreamlineWindow with horizontally scrollable timelines.

This refactor keeps all original behaviour but improves cohesion, adds typing
and docstrings, and splits responsibilities into smaller helper methods. No
logic was removed — only reorganized.

Change: wrap timelines in horizontal QScrollArea, hide visual scrollbars and
make any wheel event over the timeline widgets perform a horizontal pan that
mimics the horizontal scrollbar.
"""
from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Any, Callable

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSizePolicy, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, QEvent, QObject
from PyQt5.QtGui import QPixmap, QColor, QPainter, QFont

from schemas.activity_schemas import Activity, ApplicationActivity, ScreenshotActivity, Activities
from ui.utils import pil_to_qpixmap, sample_activities
from ui.timeline_ui import TimelineWidget
from ui.search_ui import SearchPanel


class ClickableLabel(QLabel):
    """QLabel that notifies its parent window via `on_preview_clicked` when clicked.

    The original project relied on this behaviour for interactive previewing.
    """

    def mousePressEvent(self, ev) -> None:  # type: ignore
        print('here')


class DualStreamlineWindow(QMainWindow):
    """
    Main window showing two timelines (screenshots and application clips) plus a
    central preview area and a search panel.

    This version adds horizontal scroll areas around each timeline so the user
    can pan left/right across a long time span. Visual scrollbars are hidden
    and any wheel event inside the timeline area performs horizontal panning.
    """

    def __init__(
        self,
        activities: Activities,
        faiss_index_manager: Any,
    ) -> None:
        """Initialize the DualStreamlineWindow.

        Args:
            activities: list of Activity instances to display on timelines.
            faiss_index_manager: index manager passed to the SearchPanel.
        """
        super().__init__()
        self.setWindowTitle("Dual Streamline — Screenshots (top) + Apps (bottom)")
        self.setGeometry(100, 100, 1280, 764)

        # dependencies & data
        self.faiss_index_manager = faiss_index_manager
        self.activities_list: List[Activity] = activities.to_list()

        # computed timeline range
        self.min_t: int
        self.max_t: int
        self._compute_global_time_range()

        # amount to move the playhead when scrolling one notch: 1 minute (60s)
        # touchpad or high-resolution wheels may produce fractional steps.
        # (note: wheel over timeline area now pans horizontally; this value
        # is still used elsewhere for playhead control)
        self.minute_step_seconds: float = 60

        # how many pixels represent one second on the timeline (tweakable)
        # 1.0 px/sec -> 3600 px/hour; reduce if you want denser display
        self.pixels_per_second: float = 1

        # scroll areas for timelines (populated in _init_ui)
        self.ss_scroll: Optional[QScrollArea] = None
        self.app_scroll: Optional[QScrollArea] = None

        # playhead / playback
        self.playhead: float = float(self.min_t)
        self.is_playing: bool = False
        self.play_timer: QTimer = self._init_play_timer()

        # selection
        self.selected: Optional[Activity] = None

        # build UI
        self._init_ui()

        # select the first activity if present to mirror original behaviour
        if self.activities_list:
            self.on_select_activity(self.activities_list[0])

    # -------------------- initialization helpers --------------------
    def _compute_global_time_range(self) -> None:
        """Compute min/max unix timestamps across provided activities.

        Sets self.min_t and self.max_t to integer seconds and ensures max_t > min_t.
        """
        starts: List[int] = []
        ends: List[int] = []
        for a in self.activities_list:
            if isinstance(a, ApplicationActivity):
                s = int(a.app_activity_timestamp.timestamp())
                e = s + max(1, int(a.duration_seconds))
            else:
                s = int(a.screenshot_timestamp.timestamp())
                e = s
            starts.append(s)
            ends.append(e)

        if not starts:
            self.min_t, self.max_t = 0, 1
        else:
            self.min_t = min(starts)
            self.max_t = max(ends)
            if self.max_t <= self.min_t:
                self.max_t = self.min_t + 1

    def _init_play_timer(self) -> QTimer:
        """Create and configure the play timer used for scrubbing playback."""
        timer = QTimer(self)
        timer.setInterval(40)
        timer.timeout.connect(self.on_play_tick)
        return timer

    def _compute_timeline_pixel_width(self) -> int:
        """Return desired pixel width for timelines based on the time span.

        Ensures a sensible minimum so UI doesn't collapse when span is tiny.
        """
        span = max(1, int(self.max_t - self.min_t))
        width = int(span * self.pixels_per_second)
        return max(width, 800)  # 800 px minimum for short ranges

    def _init_ui(self) -> None:
        """Construct UI elements, layout timelines and search panel."""
        root = QWidget()
        root.setStyleSheet("background-color: #151515; color: #EDEDED;")
        self.setCentralWidget(root)
        v = QVBoxLayout(root)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)

        # Top area: preview (left) + search (right)
        preview_row = QHBoxLayout()
        preview_row.setSpacing(20)

        # preview canvas
        self.preview_canvas = ClickableLabel()
        self.preview_canvas.mousePressEvent = (lambda x : self.selected.modified_screenshot_pil_image.show())
        self.preview_canvas.setFixedHeight(700)
        self.preview_canvas.setStyleSheet("background-color: #262626; border-radius: 6px;")
        self.preview_canvas.setAlignment(Qt.AlignCenter)
        self.preview_canvas.setCursor(Qt.PointingHandCursor)
        preview_row.addWidget(self.preview_canvas, 4, Qt.AlignTop)

        # search panel (injected dependency)
        self.search_panel = SearchPanel(self, self.faiss_index_manager)
        preview_row.addWidget(self.search_panel, 1, Qt.AlignTop)

        v.addLayout(preview_row)

        # screenshots timeline (top) inside horizontal QScrollArea
        self.ss_timeline = TimelineWidget(
            self.activities_list, self.min_t, self.max_t,
            activity_filter='screenshot',
            preview_callback=self.on_preview_time_changed,
            select_callback=self.on_select_activity,
        )
        self.ss_timeline.setMinimumWidth(self._compute_timeline_pixel_width())
        self.ss_scroll = QScrollArea()
        self.ss_scroll.setWidget(self.ss_timeline)
        self.ss_scroll.setWidgetResizable(False)
        # hide visual scrollbar but keep scrollbar available programmatically
        self.ss_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ss_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ss_scroll.setStyleSheet("QScrollBar:horizontal { height: 0px; } QScrollBar:vertical { width: 0px; }")
        self.ss_scroll.setFrameStyle(0)
        v.addWidget(self.ss_scroll)

        # application timeline (bottom) inside horizontal QScrollArea
        self.app_timeline = TimelineWidget(
            self.activities_list, self.min_t, self.max_t,
            activity_filter='app',
            preview_callback=self.on_preview_time_changed,
            select_callback=self.on_select_activity,
        )
        self.app_timeline.setMinimumWidth(self._compute_timeline_pixel_width())
        self.app_scroll = QScrollArea()
        self.app_scroll.setWidget(self.app_timeline)
        self.app_scroll.setWidgetResizable(False)
        # hide visual scrollbar but keep scrollbar available programmatically
        self.app_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.app_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.app_scroll.setStyleSheet("QScrollBar:horizontal { height: 0px; } QScrollBar:vertical { width: 0px; }")
        self.app_scroll.setFrameStyle(0)
        v.addWidget(self.app_scroll)


        self.ss_scroll.setFixedHeight(140)
        self.app_scroll.setFixedHeight(100)

        # install event filter so wheel events over timelines pan horizontally.
        # We install the filter on the timeline widgets themselves (they receive wheel events).
        try:
            self.ss_timeline.installEventFilter(self)
            self.app_timeline.installEventFilter(self)
        except Exception:
            # some TimelineWidget implementations might not be QObject; ignore safely
            traceback.print_exc()

    # -------------------- playback controls --------------------
    def on_play_clicked(self) -> None:
        """Toggle playback state (kept for API compatibility)."""
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def play(self) -> None:
        """Start the playback timer if not already playing."""
        if self.is_playing:
            return
        self.is_playing = True
        self.play_timer.start()

    def pause(self) -> None:
        """Stop the playback timer if currently playing."""
        if not self.is_playing:
            return
        self.is_playing = False
        self.play_timer.stop()

    def on_play_tick(self) -> None:
        """Advance playhead on each timer tick and stop at timeline end."""
        dt = self.play_timer.interval() / 1000.0
        self.set_playhead(self.playhead + dt)
        if self.playhead >= float(self.max_t):
            self.set_playhead(float(self.max_t))
            self.pause()

    def set_playhead(self, t_float: float) -> None:
        """Set playhead clamped within the global time range and update views.

        This is a public API used elsewhere in the application.
        """
        t_float = max(float(self.min_t), min(float(self.max_t), float(t_float)))
        self.playhead = t_float
        # timeline widgets expect set_playhead
        try:
            self.ss_timeline.set_playhead(self.playhead)
        except Exception:
            traceback.print_exc()
        try:
            self.app_timeline.set_playhead(self.playhead)
        except Exception:
            traceback.print_exc()
        self.on_preview_time_changed(self.playhead)

    # -------------------- selection & preview rendering --------------------
    def on_select_activity(self, activity: Activity) -> None:
        """Handle user selection of an activity from either timeline.

        This will update the internal selection, move the playhead, and update
        the central preview canvas with either an app-render or screenshot.
        """
        self.selected = activity
        if isinstance(activity, ApplicationActivity):
            t = int(activity.app_activity_timestamp.timestamp())
            self.set_playhead(float(t))
            self._render_app_preview_to_label(activity)
        else:
            t = int(activity.screenshot_timestamp.timestamp())
            self.set_playhead(float(t))
            self._render_screenshot_preview_to_label(activity)
        

    def _render_app_preview_to_label(self, activity: ApplicationActivity) -> None:
        """Render a textual preview (app name + window title) onto the preview label.

        The rendering matches the original behaviour: a QPixmap is produced and
        scaled to the preview widget to keep text sharp.
        """
        self.preview_canvas.setText("")
        pw = max(1, self.preview_canvas.width() or 800)
        ph = max(1, self.preview_canvas.height() or 320)
        pix = QPixmap(pw, ph)
        pix.fill(QColor(36, 36, 36))
        p = QPainter(pix)
        p.setPen(QColor(245, 245, 245))
        p.setFont(QFont("Segoe UI", 18, QFont.Bold))
        p.drawText(12, 40, activity.app_name)
        p.setFont(QFont("Segoe UI", 11))
        p.setPen(QColor(200, 200, 200))
        p.drawText(12, 72, activity.window_title[:140])
        p.end()
        self.preview_canvas.setPixmap(
            pix.scaled(self.preview_canvas.width(), self.preview_canvas.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def _render_screenshot_preview_to_label(self, activity: ScreenshotActivity) -> None:
        """Render a ScreenshotActivity's PIL image to the preview label as a pixmap."""
        pix = pil_to_qpixmap(activity.modified_screenshot_pil_image)
        self.preview_canvas.setPixmap(
            pix.scaled(self.preview_canvas.width(), self.preview_canvas.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    # -------------------- preview logic while scrubbing/playing --------------------
    def _find_nearest_screenshot(self, t: int) -> Optional[ScreenshotActivity]:
        """Return the nearest ScreenshotActivity within the full activities list by timestamp.

        If none exist, returns None.
        """
        nearest: Optional[ScreenshotActivity] = None
        best_d = float('inf')
        for a in self.activities_list:
            if isinstance(a, ScreenshotActivity):
                ts = int(a.screenshot_timestamp.timestamp())
                d = abs(ts - t)
                if d < best_d:
                    best_d = d
                    nearest = a
        return nearest if nearest is not None else None

    def _find_app_at_time(self, t: int) -> Optional[ApplicationActivity]:
        """Return an ApplicationActivity that contains timestamp t, if any."""
        for a in self.activities_list:
            if isinstance(a, ApplicationActivity):
                s = int(a.app_activity_timestamp.timestamp())
                e = s + max(1, int(a.duration_seconds))
                if s <= t <= e:
                    return a
        return None

    def on_preview_time_changed(self, t_float: float) -> None:
        """Update the central preview while the user scrubs or playback advances.

        The method prefers showing a nearby screenshot (<= 10s). Otherwise it
        falls back to showing an application preview that contains the requested time.
        If nothing matches, the preview is cleared.
        """
        t = int(round(t_float))
        # prefer screenshot within ±10s
        nearest = self._find_nearest_screenshot(t)
        if nearest:
            if abs(int(nearest.screenshot_timestamp.timestamp()) - t) <= 10:
                self._render_screenshot_preview_to_label(nearest)
                return

        # otherwise show an app that contains the time
        app = self._find_app_at_time(t)
        if app:
            self._render_app_preview_to_label(app)
            return

        # nothing nearby -> clear preview
        self.preview_canvas.clear()

    def update_history_ui(self, activities: Activities) -> None:
        """Update the history UI with new activities.

        This replaces the in-memory activity list, recomputes the global time range,
        rebuilds the two timeline widgets (screenshots + apps) and attempts to notify
        the SearchPanel about the new activities if it provides a compatible API.

        Args:
            activities: New Activities object containing the activities to display
        """
        # replace internal list and recompute timeline range
        self.activities_list = activities.to_list()
        self._compute_global_time_range()

        # safely remove old timeline widgets and scroll areas (if present)
        layout = self.centralWidget().layout()
        for attr in ("ss_scroll", "app_scroll", "ss_timeline", "app_timeline"):
            old = getattr(self, attr, None)
            if old is not None:
                try:
                    # remove from layout if present
                    if layout is not None and layout.indexOf(old) != -1:
                        layout.removeWidget(old)
                    # disconnect and free the widget
                    old.setParent(None)
                    old.deleteLater()
                except Exception:
                    # defensive: don't crash the whole UI if removal fails
                    traceback.print_exc()

        # recreate timeline widgets with the same callbacks used in __init__
        self.ss_timeline = TimelineWidget(
            self.activities_list, self.min_t, self.max_t,
            activity_filter="screenshot",
            preview_callback=self.on_preview_time_changed,
            select_callback=self.on_select_activity,
        )
        self.ss_timeline.setMinimumWidth(self._compute_timeline_pixel_width())
        self.ss_scroll = QScrollArea()
        self.ss_scroll.setWidget(self.ss_timeline)
        self.ss_scroll.setWidgetResizable(False)
        # hide visual scrollbar but keep scrollbar available programmatically
        self.ss_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ss_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ss_scroll.setStyleSheet("QScrollBar:horizontal { height: 0px; } QScrollBar:vertical { width: 0px; }")
        self.ss_scroll.setFrameStyle(0)

        self.app_timeline = TimelineWidget(
            self.activities_list, self.min_t, self.max_t,
            activity_filter="app",
            preview_callback=self.on_preview_time_changed,
            select_callback=self.on_select_activity,
        )
        self.app_timeline.setMinimumWidth(self._compute_timeline_pixel_width())
        self.app_scroll = QScrollArea()
        self.app_scroll.setWidget(self.app_timeline)
        self.app_scroll.setWidgetResizable(False)
        # hide visual scrollbar but keep scrollbar available programmatically
        self.app_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.app_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.app_scroll.setStyleSheet("QScrollBar:horizontal { height: 0px; } QScrollBar:vertical { width: 0px; }")
        self.app_scroll.setFrameStyle(0)

        # add the new scroll-wrapped timelines back into the main layout
        if layout is not None:
            layout.addWidget(self.ss_scroll)
            layout.addWidget(self.app_scroll)

        # re-install event filters on the new timeline widgets so wheel works
        try:
            self.ss_timeline.installEventFilter(self)
            self.app_timeline.installEventFilter(self)
        except Exception:
            traceback.print_exc()

        # Try to inform search panel / index manager about the updated activities.
        # We don't assume any specific API, so check a few likely method names.
        for candidate in ("set_activities", "update_activities", "reindex", "rebuild_index"):
            if hasattr(self.search_panel, candidate):
                try:
                    getattr(self.search_panel, candidate)(self.activities_list)
                except Exception:
                    # best-effort: don't crash UI if search panel code raises
                    traceback.print_exc()
                break

        # Ensure playhead is clamped to the new time range and notify views
        # Use set_playhead which updates timelines + preview for us
        # Keep the current playhead if it's inside the new range, otherwise clamp to min_t
        new_playhead = max(float(self.min_t), min(float(self.max_t), float(getattr(self, "playhead", float(self.min_t)))))
        self.set_playhead(new_playhead)

        # Select first activity for parity with initialization behavior, or clear preview
        if self.activities_list:
            try:
                self.on_select_activity(self.activities_list[0])
            except Exception:
                traceback.print_exc()
        else:
            self.selected = None
            if hasattr(self, "preview_canvas") and self.preview_canvas is not None:
                self.preview_canvas.clear()

    # -------------------- event filter to convert wheel -> horizontal scrollbar pan
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # type: ignore[override]
        """
        Intercept wheel events on timeline widgets and pan the corresponding
        hidden horizontal scrollbar so the timeline moves left/right. This
        mimics a normal horizontal scrollbar scroll (visual scrollbar is hidden).
        """
        try:
            if event.type() == QEvent.Wheel and (obj is getattr(self, "ss_timeline", None) or obj is getattr(self, "app_timeline", None)):
                delta_pt = event.angleDelta()
                # Prefer horizontal wheel delta when available, otherwise use vertical delta.
                delta = delta_pt.x() if delta_pt.x() != 0 else delta_pt.y()
                # fractional steps supported: 120 units per common step
                steps = delta / 120.0
                # choose scroll area corresponding to the timeline widget
                scroll = self.ss_scroll if obj is getattr(self, "ss_timeline", None) else self.app_scroll
                if scroll is None:
                    return False
                sb = scroll.horizontalScrollBar()
                # convert wheel steps into pixel movement: tune pixels_per_wheel_step for speed
                pixels_per_wheel_step = 40
                move_pixels = int(steps * pixels_per_wheel_step)
                # moving wheel upward/north (positive delta) should scroll content leftwards visually:
                new_val = sb.value() - move_pixels
                # clamp
                new_val = max(sb.minimum(), min(sb.maximum(), new_val))
                sb.setValue(new_val)
                return True  # consume the event
        except Exception:
            traceback.print_exc()
        return super().eventFilter(obj, event)

    # -------------------- UI events --------------------
    def resizeEvent(self, ev) -> None:  # type: ignore[override]
        """Re-render current selected/preview content when the window is resized."""
        super().resizeEvent(ev)
        if self.selected:
            try:
                if isinstance(self.selected, ApplicationActivity):
                    self._render_app_preview_to_label(self.selected)
                elif isinstance(self.selected, ScreenshotActivity):
                    self._render_screenshot_preview_to_label(self.selected)
            except Exception:
                traceback.print_exc()


