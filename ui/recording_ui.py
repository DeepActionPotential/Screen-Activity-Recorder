import sys
import time
import random
import math
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QRect, QPointF
from PyQt5.QtGui import QPainter, QBrush, QColor, QFont


# ---------- Particle + Ripple Background ----------
class ParticleRippleBackground(QWidget):
    """
    Particle background that emits drifting particles while parent.is_recording is True.
    Also supports simple expanding ripples on start/stop.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        # Use monotonic time for animation deltas
        self.last_time = time.monotonic()
        self.timer_ms = 16  # ~60 FPS
        self.timer = QTimer(self)
        self.timer.setInterval(self.timer_ms)
        self.timer.timeout.connect(self.on_frame)
        self.timer.start()

        # Particles
        self.particles = []
        self.particle_emit_rate = 40.0  # particles/sec when recording
        self._emit_acc = 0.0
        self.particle_speed = 20.0  # px/s
        self.particle_max_life = 3.0  # seconds
        self.max_particles = 200

        # Ripples (simple expanding circles)
        self.ripples = []  # each: {'center': QPointF, 'r': float, 'max_r': float, 'life':0, 'max_life':float}

        # Color (tuple and base QColor without alpha)
        self.G = (45, 190, 110)
        self.base_color = QColor(*self.G)

    def on_frame(self):
        now = time.monotonic()
        dt = max(1e-6, now - self.last_time)
        self.last_time = now

        parent = self.parent()
        recording = bool(parent and getattr(parent, "is_recording", False))

        # Emit particles if recording
        if recording:
            self._emit_acc += self.particle_emit_rate * dt
            while self._emit_acc >= 1.0 and len(self.particles) < self.max_particles:
                self._emit_particle()
                self._emit_acc -= 1.0
        else:
            # decay emitter accumulator so we don't burst when resuming
            self._emit_acc = max(0.0, self._emit_acc - 5.0 * dt)

        # Update particles
        alive = []
        for p in self.particles:
            p['life'] += dt
            if p['life'] >= p['max_life']:
                continue
            # apply drag (simple)
            drag = (1.0 - 0.08 * dt)
            vx = p['vel'].x() * drag
            vy = p['vel'].y() * drag
            p['vel'] = QPointF(vx, vy)
            # update position
            dp = QPointF(p['vel'].x() * dt, p['vel'].y() * dt)
            p['pos'] = QPointF(p['pos'].x() + dp.x(), p['pos'].y() + dp.y())
            alive.append(p)
        self.particles = alive

        # Update ripples
        new_ripples = []
        for r in self.ripples:
            r['life'] += dt
            if r['life'] >= r['max_life']:
                continue
            frac = r['life'] / r['max_life']
            r['r'] = r['max_r'] * frac
            new_ripples.append(r)
        self.ripples = new_ripples

        if self.particles or self.ripples:
            self.update()

    def _emit_particle(self):
        # Emit around the recording indicator center if available
        parent = self.parent()
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        if parent and hasattr(parent, "recording_indicator"):
            try:
                ri = parent.recording_indicator
                c = ri.rect().center()
                mapped = ri.mapToParent(c)         # QPoint
                center = QPointF(mapped.x(), mapped.y())
            except Exception:
                pass

        angle = random.random() * 2 * math.pi
        spread = 8 + random.random() * 28
        px = center.x() + math.cos(angle) * spread
        py = center.y() + math.sin(angle) * spread

        speed = (0.3 + random.random() * 1.0) * self.particle_speed
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed

        life = 1.2 + random.random() * (self.particle_max_life - 1.2)
        size = 2.0 + random.random() * 3.0

        color = QColor(self.G[0], self.G[1], self.G[2])  # base, alpha set per-draw

        self.particles.append({
            'pos': QPointF(px, py),
            'vel': QPointF(vx, vy),
            'life': 0.0,
            'max_life': life,
            'size': size,
            'color': color
        })

    def spawn_ripple(self, strong=False):
        # Create a short-lived expanding circle at the recording indicator center
        parent = self.parent()
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        if parent and hasattr(parent, "recording_indicator"):
            try:
                ri = parent.recording_indicator
                c = ri.rect().center()
                mapped = ri.mapToParent(c)
                center = QPointF(mapped.x(), mapped.y())
            except Exception:
                pass

        max_r = 80 if strong else 46
        max_life = 0.6 if strong else 0.45
        self.ripples.append({
            'center': center,
            'r': 0.0,
            'max_r': max_r,
            'life': 0.0,
            'max_life': max_life
        })
        # immediate paint
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        # Base background
        painter.fillRect(rect, QColor(18, 18, 18))

        # Draw ripples first (under particles)
        painter.save()
        for r in self.ripples:
            frac = max(0.0, min(1.0, r['life'] / r['max_life']))
            alpha = int((1.0 - frac) * 160)
            pen_color = QColor(self.G[0], self.G[1], self.G[2], alpha)
            painter.setPen(pen_color)
            painter.setBrush(Qt.NoBrush)
            radius = r['r']
            c = r['center']
            painter.drawEllipse(int(c.x() - radius), int(c.y() - radius),
                                int(radius * 2), int(radius * 2))
        painter.restore()

        # Draw particles
        painter.save()
        for p in self.particles:
            life_frac = max(0.0, min(1.0, p['life'] / p['max_life']))
            alpha = int((1.0 - life_frac) * 120)  # fade out
            col = QColor(self.G[0], self.G[1], self.G[2], alpha)
            painter.setBrush(col)
            painter.setPen(Qt.NoPen)
            s = p['size'] * (0.9 + 0.3 * math.sin(life_frac * math.pi))
            painter.drawEllipse(int(p['pos'].x() - s / 2), int(p['pos'].y() - s / 2), int(s), int(s))
        painter.restore()


# ---------- Recording Indicator ----------
class RecordingIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.recording = False
        self.recording_time = 0  # seconds
        self.bar_heights = [0.25] * 5  # normalized 0..1

        # animation for bars (fast)
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(100)  # 100 ms

        # timer for recording seconds
        self.recording_timer = QTimer(self)
        self.recording_timer.timeout.connect(self.update_recording_time)

        # Slightly wider for balance
        self.setFixedSize(300, 70)

    def update_animation(self):
        if self.recording:
            for i in range(5):
                # smoother random-like motion
                self.bar_heights[i] = 0.2 + random.random() * 0.75
        else:
            # idle: low bars
            for i in range(5):
                self.bar_heights[i] = 0.18 + i * 0.01
        self.update()

    def update_recording_time(self):
        self.recording_time += 1
        self.update()

    def start_recording(self, continue_timer=True):


        if not continue_timer:
            self.recording_time = 0

        self.recording = True
        self.recording_timer.start(1000)  # Update every second
        self.update()

    def stop_recording(self):
        self.recording = False
        self.recording_timer.stop()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        w, h = rect.width(), rect.height()

        # Background rounded pill (slightly translucent)
        bg_color = QColor(36, 36, 36, 220)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)
        radius = h / 2
        painter.drawRoundedRect(rect, radius, radius)

        # Pulsing dot (left) - green
        base_dot = min(h * 0.45, 26)
        if self.recording:
            pulse = (math.sin(time.monotonic() * 2.5) + 1) / 2  # smooth 0..1
            size = base_dot + pulse * (base_dot * 0.25)
            dot_color = QColor(45, 190, 110)
        else:
            size = base_dot
            dot_color = QColor(45, 190, 110, 140)

        x_dot = 12
        y_dot = (h - size) / 2
        painter.setBrush(QBrush(dot_color))
        painter.drawEllipse(int(x_dot), int(y_dot), int(size), int(size))

        # Text: REC / PAUSED and timer
        font = QFont("Segoe UI", 10, QFont.Bold)
        painter.setFont(font)
        text_x = int(x_dot + size + 12)
        text_width = 140
        text_rect = QRect(text_x, 0, text_width, h)

        status_text = "REC" if self.recording else "PAUSED"
        status_color = QColor(45, 190, 110) if self.recording else QColor(180, 180, 180)
        painter.setPen(status_color)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, status_text)

        # Timer text to the right of status
        mins = self.recording_time // 60
        secs = self.recording_time % 60
        timer_text = f"{mins:02d}:{secs:02d}"
        timer_font = QFont("Segoe UI", 9)
        painter.setFont(timer_font)
        painter.setPen(QColor(200, 200, 200))
        timer_rect = QRect(text_x + 70, 0, 70, h)
        painter.drawText(timer_rect, Qt.AlignLeft | Qt.AlignVCenter, timer_text)

        # Audio level bars (right side) - green
        bar_count = 5
        bar_width = 8
        bar_spacing = 6
        total_width = bar_count * bar_width + (bar_count - 1) * bar_spacing
        start_x = w - total_width - 14
        max_bar_height = int(h * 0.55)

        for i in range(bar_count):
            nh = max(1, int(self.bar_heights[i] * max_bar_height))
            y_pos = (h - nh) // 2
            color = QColor(45, 190, 110) if self.recording else QColor(45, 190, 110, 110)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            bx = start_x + i * (bar_width + bar_spacing)
            painter.drawRoundedRect(bx, y_pos, bar_width, nh, 2, 2)


from core.activity_manager import ActivityManager

# ---------- Main Window ----------
class SimpleRecorderWindow(QMainWindow):
    def __init__(self, activity_manager:ActivityManager):
        super().__init__()
        self.activity_manager = activity_manager
        self.setWindowTitle("Recorder")
        self.setGeometry(100, 100, 1280, 764)
        self.center_window()

        # recording flag used by both UI and background
        self.is_recording = False

        # build particle + ripple central widget
        central = ParticleRippleBackground(self)
        self.setCentralWidget(central)

        self.set_dark_theme()
        self.setup_ui()

    def center_window(self):
        frame_geometry = self.frameGeometry()
        screen_center = QApplication.primaryScreen().availableGeometry().center()
        frame_geometry.moveCenter(screen_center)
        self.move(frame_geometry.topLeft())

    def set_dark_theme(self):
        # styling for a rectangular button that matches indicator width (green)
        self.setStyleSheet("""
            QMainWindow { background-color: #151515; }
            QPushButton {
                border-radius: 10px;
                padding: 10px;
                font-size: 22px;
                color: white;
                background-color: #2DBE6E;
            }
            QPushButton:hover { background-color: #28A65A; }
            QPushButton:pressed { background-color: #1F7A43; }
        """)

    def setup_ui(self):
        central = self.centralWidget()

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(18)
        central.setLayout(layout)

        # Recording animation (kept as visual indicator)
        self.recording_indicator = RecordingIndicator(central)

        # Create the rectangular icon-only Start/Stop button to match the indicator width
        self.record_btn = QPushButton("⏺", central)
        self.record_btn.setFont(QFont("Segoe UI Symbol", 20, QFont.Bold))
        btn_width = self.recording_indicator.width()  # safe because RecordingIndicator setFixedSize in ctor
        btn_height = 64
        self.record_btn.setFixedSize(btn_width, btn_height)
        self.record_btn.setToolTip("Start recording (⏺). Click to stop (⏹).")
        self.record_btn.setAccessibleName("Recording Toggle Button")
        self.record_btn.clicked.connect(self.toggle_recording)

        # layout ordering: button over indicator
        layout.addWidget(self.record_btn, 0, Qt.AlignHCenter)
        layout.addWidget(self.recording_indicator, 0, Qt.AlignHCenter)

    
    def show_warning_message(self, message:str):

        """
        Show a warning message in a modal dialog.
        """

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Warning")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setStyleSheet("""QMessageBox {
                background-color: #fffff;
                color: #ffffff;
                font-size: 14px;
            }""")
        msg_box.exec_()



    def toggle_recording(self, continue_timer = True, force_restart=False):
        # toggle the recording flag, update indicator visuals, and spawn a ripple

        is_there_index = self.activity_manager.faiss_index_manager.index
        
        if not is_there_index:
            self.show_warning_message('Load Session First!!')
            return
        
        if is_there_index and not force_restart:
            continue_timer = True
        
        self.is_recording = not self.is_recording

        if self.is_recording:
            self.record_btn.setText("⏹")
            self.record_btn.setToolTip("Stop recording (⏹).")
            self.recording_indicator.start_recording(continue_timer=continue_timer)
            # stronger ripple on start
            self.centralWidget().spawn_ripple(strong=True)
            self.centralWidget().update()
            self.activity_manager.start_recording()
        else:
            self.activity_manager.stop_recording()
            self.record_btn.setText("⏺")
            self.record_btn.setToolTip("Start recording (⏺).")
            self.recording_indicator.stop_recording()
            # softer ripple on stop
            self.centralWidget().spawn_ripple(strong=False)
            self.centralWidget().update()



    def closeEvent(self, event):
        # stop timers cleanly
        self.recording_indicator.animation_timer.stop()
        self.recording_indicator.recording_timer.stop()
        self.centralWidget().timer.stop()
        super().closeEvent(event)


