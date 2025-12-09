
import numpy as np
from typing import List

from schemas.base_models import Embedder

class SentenceTransformerEmbedder(Embedder):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", dim: int = 512, device: str = "cpu"):
        self.model = None
        self.device = device
        self.model_name = model_name
        self.dim = dim

        self._create_model()
        
    

    def _create_model(self):

        from sentence_transformers import SentenceTransformer
        import torch.nn as nn

        self.model = SentenceTransformer(self.model_name, device=self.device)
        original_dim = self.model.get_sentence_embedding_dimension()
        self.projection = nn.Linear(original_dim, self.dim).to(self.device)

    def embed_text(self, text: str) -> np.ndarray:
        """
        Embed a single text string into a vector of size `self.dim`.

        :param text: The input text string.
        :return: NumPy array of shape (dim,)
        """
        
    
        
        embedding = self.model.encode(text, convert_to_numpy=False, normalize_embeddings=True)
        projected = self.projection(embedding)
        return projected.detach().cpu().numpy().astype("float32")




