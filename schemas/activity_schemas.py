from pydantic import BaseModel
from PIL.Image import Image
from typing import List, Union

from datetime import datetime




class KeyboardActivity(BaseModel):
    keys_pressed: set
    keys_pressed_timestamp: datetime



class MouseClickActicity(BaseModel):
    x: int
    y: int
    click_type: str
    mouse_click_timestamp: datetime





class ApplicationActivity(BaseModel):
    app_name: str
    window_title: str
    exe_path: str
    cmd_command: str
    duration_seconds: float
    keywords: str
    app_activity_timestamp: datetime

    def dict(self):
        return {
            "app_name": self.app_name,
            "window_title": self.window_title,
            "exe_path": self.exe_path,
            "cmd_command": self.cmd_command,
            "duration_seconds": self.duration_seconds,
            "keywords": self.keywords,
            "app_activity_timestamp": self.app_activity_timestamp
        }






class ScreenshotActivity(BaseModel):
    screenshot_id: str
    screenshot_ocr_text: str
    keywords: str
    original_screenshot_pil_image: Image
    modified_screenshot_pil_image: Image
    screenshot_timestamp: datetime

    class Config:
        arbitrary_types_allowed = True
    

    def dict(self):
        return {
            "screenshot_id": self.screenshot_id,
            "screenshot_ocr_text": self.screenshot_ocr_text,
            "keywords": self.keywords,
            "original_screenshot_pil_image": self.original_screenshot_pil_image,
            "modified_screenshot_pil_image": self.modified_screenshot_pil_image,
            "screenshot_timestamp": self.screenshot_timestamp
        }



class Activities(BaseModel):
    activities: List[Union[ScreenshotActivity, ApplicationActivity]]

    def to_list(self):
        return self.activities


Activity = Union[ApplicationActivity, ScreenshotActivity]