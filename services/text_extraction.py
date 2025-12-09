import easyocr
from utils.utils import open_image
from PIL import Image
import numpy as np
from doctr.models import ocr_predictor
from doctr.io import DocumentFile
from PIL import Image
import numpy as np
from io import BytesIO


from schemas.ocr_schemas import TextOCRChunk, TextOCRChunks

import os
import psutil
import time
import numpy as np
from PIL import Image

import numpy as np
from PIL import Image
from typing import List
import easyocr


class EasyOCRTextExtractor:
    """
    Wrapper for EasyOCR to extract text chunks from images.
    """

    def __init__(self, model: easyocr.Reader):
        """
        Initialize the extractor with an EasyOCR reader.

        Args:
            model (easyocr.Reader): An initialized EasyOCR reader object.
        """
        self._model = model

    def extract(self, image: Image.Image) -> TextOCRChunks:
        """
        Extract text chunks from a PIL image using EasyOCR.

        Args:
            image (Image.Image): The input image.

        Returns:
            TextOCRChunks: A collection of detected text chunks with bounding boxes and confidence scores.
        """
        print("Extracting text...")
        
        # Convert PIL Image to numpy array
        image_np = np.array(image)
        
        # Perform OCR
        results = self._model.readtext(image_np)
        
        # Build structured result
        text_ocr_chunks: List[TextOCRChunk] = [
            TextOCRChunk(text_bounding_box=box, text=text, confidence_score=confidence)
            for box, text, confidence in results
        ]

        return TextOCRChunks(text_ocr_chunks=text_ocr_chunks)



class DoctrTextExtractor:
    """
    Wrapper for Doctr OCR to extract text chunks with 4-point bounding boxes.
    """

    def __init__(self, model: ocr_predictor):
        self._model = model

    def extract(self, image: Image.Image) -> TextOCRChunks:
        """
        Extract text chunks from a PIL image using Doctr.

        Args:
            image (Image.Image): The input image.

        Returns:
            TextOCRChunks: A collection of detected text chunks with 4-point bounding boxes.
        """


        # Convert to PNG bytes
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()  
 
        doc = DocumentFile.from_images(img_bytes)
        result = self._model(doc)

        width, height = image.size
        text_ocr_chunks = []

        for page in result.pages:
            for block in page.blocks:
                for line in block.lines:
                    for word in line.words:
                        (x_min, y_min), (x_max, y_max) = word.geometry

                        # Convert normalized coords → pixel coords
                        x_min_px, y_min_px = x_min * width, y_min * height
                        x_max_px, y_max_px = x_max * width, y_max * height

                        # Create 4-point polygon (clockwise)
                        polygon_box = [
                            [x_min_px, y_min_px],  # Top-left
                            [x_max_px, y_min_px],  # Top-right
                            [x_max_px, y_max_px],  # Bottom-right
                            [x_min_px, y_max_px],  # Bottom-left
                        ]

                        text_ocr_chunks.append(
                            TextOCRChunk(
                                text=word.value,
                                text_bounding_box=polygon_box,
                                confidence_score=word.confidence
                            )
                        )

        return TextOCRChunks(text_ocr_chunks=text_ocr_chunks)
