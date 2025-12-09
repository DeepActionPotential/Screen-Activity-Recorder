import os
os.environ["TRANSFORMERS_NO_TF"] = "1"

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
import sys

import traceback
from dataclasses import dataclass

from services.index_manager import FaissIndexManager
from services.media_embedding import SentenceTransformerEmbedder


import os
import time
import traceback  # Added for full traceback
from datetime import datetime, timedelta
from doctr.models import ocr_predictor
from services.text_extraction import DoctrTextExtractor
from services.ner_extraction import NERBILSTMCRFExtractor
from services.keyword_extraction import KeyBERTKeywrodExtractor
from services.media_embedding import SentenceTransformerEmbedder
from services.index_manager import FaissIndexManager
from services.activity_recording import ScreenshotActivityRecorder, ApplicationActivityRecorder
from core.activity_manager import ActivityManager
from config import EmbeddingConfig, RecordingConfig, TokenizerConfig
import torch
from services.ner_extraction import NERBILSTMCRFExtractor, BiLSTMCRF
from config import TokenizerConfig, LLMConfig, NERConfig, RecordingConfig
from transformers import AutoTokenizer

def setup_ocr_service():
    """Set up the Doctr OCR service."""
    try:
        print("Loading Doctr OCR model...")
        model = ocr_predictor(pretrained=True)
        return DoctrTextExtractor(model)
    except Exception as e:
        print("Error in setup_ocr_service:")
        traceback.print_exc()
        raise

def setup_ner_service():
    """Set up the NER service."""
    try:
        print("Loading NER model...")
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        tokenizer = AutoTokenizer.from_pretrained(TokenizerConfig.tokenizer_name)
        ner_model = torch.load(NERConfig.model_path, weights_only=False, map_location='cpu')
        return NERBILSTMCRFExtractor(
            ner_model,
            tokenizer=tokenizer,
            label2id=TokenizerConfig.label2id,
            max_len=TokenizerConfig.max_len,
            device=device
        )
    except Exception as e:
        print("Error in setup_ner_service:")
        traceback.print_exc()
        raise

def setup_embedding_service():
    """Set up the embedding service."""
    try:
        print("Loading embedding model...")
        return SentenceTransformerEmbedder(
            model_name=EmbeddingConfig.embedding_model_name,
            dim=EmbeddingConfig.embedding_dim,
            device=EmbeddingConfig.embedding_device
        )
    except Exception as e:
        print("Error in setup_embedding_service:")
        traceback.print_exc()
        raise

def setup_index_manager(embedder):
    """Set up the FAISS index manager."""
    try:
        return FaissIndexManager(embedder, dim=EmbeddingConfig.embedding_dim)
    except Exception as e:
        print("Error in setup_index_manager:")
        traceback.print_exc()
        raise




if __name__ == "__main__":
    # High DPI scaling helpful on modern displays
    from core.activity_manager import ActivityManager
    from services.activity_recording import ScreenshotActivityRecorder, ApplicationActivityRecorder
    from services.index_manager import FaissIndexManager
    from services.media_embedding import SentenceTransformerEmbedder
    from services.text_extraction import EasyOCRTextExtractor
    from services.ner_extraction import NERBILSTMCRFExtractor
    from services.keyword_extraction import KeyBERTKeywrodExtractor
    from config import RecordingConfig, TokenizerConfig
    from ui.recording_ui import SimpleRecorderWindow

    import easyocr
    # Initialize components
    embedder = SentenceTransformerEmbedder()
    index_manager = FaissIndexManager(embedder, 512)
    ocr_service = setup_ocr_service()
    ner_service = setup_ner_service()
    keyword_extractor = KeyBERTKeywrodExtractor()
    
    # Create activity recorders
    screen_recorder = ScreenshotActivityRecorder(
        ocr_service=ocr_service,
        ner_service=ner_service,
        keyword_extractor=keyword_extractor,
        tokenizer_config=TokenizerConfig()
    )
    
    app_recorder = ApplicationActivityRecorder(
        keyword_extractor=keyword_extractor
    )
    
    # Create activity manager
    activity_manager = ActivityManager(
        screen_activity_recorder=screen_recorder,
        app_activity_recorder=app_recorder,
        faiss_index_manager=index_manager,
        recording_config=RecordingConfig()
    )

    from ui.main_ui import MainWindow

    if __name__ == "__main__":
        app = QApplication(sys.argv)
        app.setFont(QFont("Segoe UI", 10))
        # index_manager.load_index(r'E:\ML\temps\ActivityScreenRecorder\data\session_20250825_190908.joblib')
        window = MainWindow(activity_manager, index_manager)
        window.show()
        sys.exit(app.exec_())
