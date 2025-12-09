from PIL import ImageGrab
import os
import datetime
from PIL import Image
import time


from datetime import datetime

from schemas.activity_schemas import ScreenshotActivity, ApplicationActivity
from schemas.base_models import ActivityRecorder, KeywordExtractor
from services.ner_extraction import NERBILSTMCRFExtractor
from services.text_extraction import EasyOCRTextExtractor

from config import TokenizerConfig
from utils.utils import extract_sensitive_sequences, blur_region_with_bbox, blur_regions_with_bboxs, extract_common_pii_sequences, generate_timestamp_id, run_command_against_text, get_active_window_info


class ScreenshotActivityRecorder(ActivityRecorder):

    def __init__(self, 
                 ocr_service:EasyOCRTextExtractor, 
                 ner_service:NERBILSTMCRFExtractor,
                 keyword_extractor: KeywordExtractor,
                 tokenizer_config: TokenizerConfig):
        
        self.ocr_service = ocr_service
        self.ner_service = ner_service
        self.tokenizer_config = tokenizer_config
        self.keyword_extractor = keyword_extractor



    def take_screenshot(self, save_dir=None):
        """
        Capture a screenshot of the current screen and return it as a PIL Image.
        Optionally save the screenshot to a specified directory.

        Args:
            save_dir (str, optional): Directory to save the screenshot. 
                                    If None, the screenshot will not be saved.

        Returns:
            PIL.Image.Image: The captured screenshot as a PIL Image.

        Raises:
            ValueError: If save_dir is provided but is not a valid directory.
        """
        # Capture screenshot
        screenshot = ImageGrab.grab()

        # Save if save_dir is provided
        if save_dir:
            if not os.path.isdir(save_dir):
                raise ValueError(f"Invalid directory: {save_dir}")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(save_dir, f"screenshot_{timestamp}.png")
            screenshot.save(file_path)

        return screenshot
    

    


    def record_activity(self, ner_confidence_threshold: float = 0.4, from_path: str = "", show_image: bool = False, hide_sensitive_info: bool = True) -> ScreenshotActivity:
        
        
        if from_path:
            screenshot = Image.open(from_path)
        else:
            screenshot = self.take_screenshot()
        
        
        original_screenshot = screenshot

        

        if not hide_sensitive_info:


            return  ScreenshotActivity(
            screenshot_id=generate_timestamp_id(),
            screenshot_timestamp=datetime.now(),
            screenshot_ocr_text="",
            keywords="",
            original_screenshot_pil_image=screenshot,
            modified_screenshot_pil_image=screenshot

        )


        non_senstive_pii_labels = self.tokenizer_config.non_senstive_label2id
        pii_extracted_bounding_boxes = []

        
        text_ocr_chunks = self.ocr_service.extract(screenshot).to_list()

        
        all_text = " ".join([text_ocr_chunk.text.lower() for text_ocr_chunk in text_ocr_chunks])



        ner_entities = self.ner_service.extract(all_text, ner_confidence_threshold)

        common_pii_sequneces = extract_common_pii_sequences(all_text)
        bilstm_crf_pii_sequences = extract_sensitive_sequences(ner_entities, non_senstive_pii_labels)
        
        # print(all_text)
        # print(common_pii_sequneces)
        # print(bilstm_crf_pii_sequences)

        for text_ocr_chunk in text_ocr_chunks:
            for sequence in bilstm_crf_pii_sequences + common_pii_sequneces:
                if sequence in text_ocr_chunk.text.lower():
                    pii_extracted_bounding_boxes.append(text_ocr_chunk.text_bounding_box)
        
        
        blurred_screenshot = blur_regions_with_bboxs(screenshot, pii_extracted_bounding_boxes)

        screenshot_keywords = self.keyword_extractor.extract_keywords(all_text)

   
        screenshot_activity = ScreenshotActivity(
            screenshot_id=generate_timestamp_id(),
            screenshot_timestamp=datetime.now(),
            screenshot_ocr_text=all_text,
            keywords=screenshot_keywords,
            original_screenshot_pil_image=original_screenshot,
            modified_screenshot_pil_image=blurred_screenshot


        )

        if show_image:
            blurred_screenshot.show()

        return screenshot_activity







class ApplicationActivityRecorder(ActivityRecorder):

    def __init__(self, keyword_extractor: KeywordExtractor):

        self.keyword_extractor = keyword_extractor
        self.last_switch_time = None
        self.last_window = None


    def record_activity(self) -> ApplicationActivity:
        """
        Records the current active window as an ApplicationActivity.
        Calculates duration since the last window switch.
        """
        process_name, window_title, exe_path, cmd_command = get_active_window_info()
        now = time.time()
        
        # Calculate duration based on whether the window has changed
        current_window = (process_name, window_title)
        
        if self.last_window is None:
            # First call, no duration
            duration = 0.0
        elif current_window != self.last_window:
            # Window changed, calculate duration since last switch
            duration = now - self.last_switch_time
        else:
            # Same window, return 0 as duration (will be accumulated on next switch)
            duration = 0.0
        
        # Update state for next call
        window_changed = (self.last_window is None) or (current_window != self.last_window)
        if window_changed:
            self.last_switch_time = now
            self.last_window = current_window

        return ApplicationActivity(
            app_name=process_name,
            window_title=window_title,
            exe_path=exe_path,
            cmd_command=cmd_command,
            duration_seconds=duration,
            keywords=self.keyword_extractor.extract_keywords(window_title + "" + process_name + "" + cmd_command),
            app_activity_timestamp=datetime.fromtimestamp(now),
        )