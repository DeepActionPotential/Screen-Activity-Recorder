from abc import ABC, abstractmethod
from PIL import Image
import numpy as np
from typing import List, Optional, Union


from .ner_schemas import NEREntites
from .ocr_schemas import TextOCRChunks
from .activity_schemas import ScreenshotActivity, ApplicationActivity






class NERExtractor(ABC):

    @abstractmethod
    def extract(self, text:str, confidence_score_threshold:float) -> NEREntites:
        pass



class TextExtractor(ABC):

    @abstractmethod
    def extract(self, image: Image.Image) -> TextOCRChunks:
        pass


class Embedder(ABC):
    
    @abstractmethod
    def embed_text(self, text: str) -> np.ndarray:
        pass




class LLMManager(ABC):
     
    @abstractmethod
    def send_text_prompt(self, prompt: str) -> Optional[str]:
        pass
    
    @abstractmethod
    def send_image_prompt(self, image: Image, prompt: str = "") -> Optional[str]:
        pass

    @abstractmethod
    def send_multimodal_prompt(self, image_path: str, prompt: str) -> Optional[str]:
        pass




class ActivityRecorder(ABC):
    
    @abstractmethod
    def record_activity(self) -> Union[ScreenshotActivity, ApplicationActivity]:
        pass



class KeywordExtractor(ABC):

    @abstractmethod
    def extract_keywords(self, text: str) -> str:
        pass

