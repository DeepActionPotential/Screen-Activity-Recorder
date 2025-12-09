# dual_streamline_with_clickable_preview.py
import sys
import os
import subprocess
import tempfile
import traceback
from dataclasses import dataclass
from typing import List, Union, Optional
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QRect, QPoint
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QBrush, QLinearGradient, QPixmap

from PIL import Image, ImageDraw, ImageFont

from schemas.activity_schemas import Activities, ApplicationActivity, ScreenshotActivity



# -------------------------
# Utility: robust PIL -> QPixmap
# -------------------------
def pil_to_qpixmap(pil_img):
    """Robust conversion from PIL.Image to QPixmap (falls back to PNG buffer)."""
    if pil_img is None:
        return QPixmap()
    # Try ImageQt if present
    try:
        from PIL import ImageQt as ImageQt_mod
        try:
            qimage = ImageQt_mod.ImageQt(pil_img.convert("RGBA"))
            return QPixmap.fromImage(qimage)
        except Exception:
            pass
    except Exception:
        pass
    # Fallback: write to in-memory PNG and load into QPixmap
    try:
        import io
        buf = io.BytesIO()
        pil_img.convert("RGBA").save(buf, format="PNG")
        pix = QPixmap()
        pix.loadFromData(buf.getvalue(), "PNG")
        return pix
    except Exception:
        return QPixmap()


# -------------------------
# Placeholder & loader helpers
# -------------------------
def create_placeholder_pil(text: str, size=(1280, 720), bg=(36, 36, 36), accent=(255, 183, 77)):
    w, h = size
    img = Image.new("RGBA", (w, h), bg)
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        f = ImageFont.load_default()
    d.rectangle([0, 0, w, 28], fill=accent)
    max_chars = 80
    s = text.replace("\n", " ")
    y = 36
    for i in range(0, len(s), max_chars):
        d.text((10, y), s[i:i+max_chars], font=f, fill=(230, 230, 230))
        y += 20
    return img

def load_or_placeholder(path: str, fallback_text: str, size=(1280, 720)):
    try:
        pil = Image.open(path).convert("RGBA")
        return pil
    except Exception:
        return create_placeholder_pil(fallback_text, size=size)


def sample_activities():
    base = datetime(2025, 8, 25, 19, 9, 8)
    acts: List[Activity] = []

    # Provided image paths (raw strings)
    path1 = r"C:\Users\Dream\Downloads\test2.jpg"
    path2 = r"C:\Users\Dream\Downloads\test.jpg"

    pil1 = load_or_placeholder(path1, "Missing test2.jpg", size=(1280, 720))
    pil2 = load_or_placeholder(path2, "Missing test.jpg", size=(1280, 720))

    mod1 = pil1.copy()
    overlay = Image.new("RGBA", mod1.size, (0, 0, 0, 60))
    mod1.paste(overlay, (0, 0), overlay)

    mod2 = pil2.copy()
    overlay2 = Image.new("RGBA", mod2.size, (0, 0, 0, 60))
    mod2.paste(overlay2, (0, 0), overlay2)

    acts.append(ScreenshotActivity(
        screenshot_id="shotA",
        screenshot_ocr_text="OCR A",
        keywords="test2",
        original_screenshot_pil_image=pil1,
        modified_screenshot_pil_image=mod1,
        screenshot_timestamp=base + timedelta(seconds=8)
    ))

    acts.append(ScreenshotActivity(
        screenshot_id="shotA",
        screenshot_ocr_text="OCR A",
        keywords="test2",
        original_screenshot_pil_image=pil2,
        modified_screenshot_pil_image=mod2,
        screenshot_timestamp=base + timedelta(seconds=40)
    ))


    acts.append(ScreenshotActivity(
        screenshot_id="shotA",
        screenshot_ocr_text="OCR A",
        keywords="test2",
        original_screenshot_pil_image=pil1,
        modified_screenshot_pil_image=mod1,
        screenshot_timestamp=base + timedelta(seconds=80)
    ))

    acts.append(ScreenshotActivity(
        screenshot_id="shotA",
        screenshot_ocr_text="OCR A",
        keywords="test2",
        original_screenshot_pil_image=pil2,
        modified_screenshot_pil_image=mod2,
        screenshot_timestamp=base + timedelta(seconds=110)
    ))

    acts.append(ScreenshotActivity(
        screenshot_id="shotB",
        screenshot_ocr_text="OCR B",
        keywords="test",
        original_screenshot_pil_image=pil1,
        modified_screenshot_pil_image=mod1,
        screenshot_timestamp=base + timedelta(seconds=160)
    ))


    acts.append(ScreenshotActivity(
        screenshot_id="shotA",
        screenshot_ocr_text="OCR A",
        keywords="test2",
        original_screenshot_pil_image=pil1,
        modified_screenshot_pil_image=mod1,
        screenshot_timestamp=base + timedelta(seconds=200)
    ))

    acts.append(ScreenshotActivity(
        screenshot_id="shotA",
        screenshot_ocr_text="OCR A",
        keywords="test2",
        original_screenshot_pil_image=pil2,
        modified_screenshot_pil_image=mod2,
        screenshot_timestamp=base + timedelta(seconds=400)
    ))


    acts.append(ScreenshotActivity(
        screenshot_id="shotA",
        screenshot_ocr_text="OCR A",
        keywords="test2",
        original_screenshot_pil_image=pil1,
        modified_screenshot_pil_image=mod1,
        screenshot_timestamp=base + timedelta(seconds=500)
    ))

    acts.append(ScreenshotActivity(
        screenshot_id="shotA",
        screenshot_ocr_text="OCR A",
        keywords="test2",
        original_screenshot_pil_image=pil2,
        modified_screenshot_pil_image=mod2,
        screenshot_timestamp=base + timedelta(seconds=800)
    ))

    acts.append(ScreenshotActivity(
        screenshot_id="shotB",
        screenshot_ocr_text="OCR B",
        keywords="test",
        original_screenshot_pil_image=pil1,
        modified_screenshot_pil_image=mod1,
        screenshot_timestamp=base + timedelta(seconds=3000)
    ))


    

    acts.append(ApplicationActivity(
        app_name="msedge.exe",
        window_title="Edge - many tabs",
        exe_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        cmd_command="msedge.exe --profile-directory=Default",
        duration_seconds=50,
        keywords="edge",
        app_activity_timestamp=base + timedelta(seconds=75)
    ))
    acts.append(ApplicationActivity(
        app_name="TogglTrack.exe",
        window_title="Toggl Track",
        exe_path=r"C:\Users\Dream\AppData\Local\TogglTrack\TogglTrack.exe",
        cmd_command="TogglTrack.exe",
        duration_seconds=30,
        keywords="toggl",
        app_activity_timestamp=base + timedelta(seconds=155)
    ))
    acts.append(ApplicationActivity(
        app_name="msedge.exe",
        window_title="Edge - YouTube",
        exe_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        cmd_command="msedge.exe --profile-directory=Default",
        duration_seconds=10,
        keywords="edge",
        app_activity_timestamp=base + timedelta(seconds=263)
    )),
    
    acts.append(ApplicationActivity(
        app_name="msedge.exe",
        window_title="Edge - YouTube",
        exe_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        cmd_command="msedge.exe --profile-directory=Default",
        duration_seconds=10,
        keywords="edge",
        app_activity_timestamp=base + timedelta(seconds=263)
    )),
    
    acts.append(ApplicationActivity(
        app_name="msedge.exe",
        window_title="Edge - YouTube",
        exe_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        cmd_command="msedge.exe --profile-directory=Default",
        duration_seconds=10,
        keywords="edge",
        app_activity_timestamp=base + timedelta(seconds=263)
    )),
    
    
    acts.append(ApplicationActivity(
        app_name="msedge.exe",
        window_title="Edge - YouTube",
        exe_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        cmd_command="msedge.exe --profile-directory=Default",
        duration_seconds=10,
        keywords="edge",
        app_activity_timestamp=base + timedelta(seconds=263)
    )),
    
    
    acts.append(ApplicationActivity(
        app_name="msedge.exe",
        window_title="Edge - YouTube",
        exe_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        cmd_command="msedge.exe --profile-directory=Default",
        duration_seconds=10,
        keywords="edge",
        app_activity_timestamp=base + timedelta(seconds=263)
    ))

    def key(a):
        if isinstance(a, ApplicationActivity):
            return a.app_activity_timestamp
        else:
            return a.screenshot_timestamp

    
    return Activities(activities=sorted(acts, key=key))