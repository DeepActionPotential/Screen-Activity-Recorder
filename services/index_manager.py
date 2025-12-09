import faiss
import os
import numpy as np
import joblib
from typing import Dict, List, Optional, Any

from schemas.base_models import Embedder
from schemas.activity_schemas import Activities

class FaissIndexManager:
    def __init__(self, text_embedder: Embedder, dim: int):
        """
        :param text_embedder: A callable that converts text into embeddings (list or np.array)
        :param dim: Dimensionality of the embeddings
        """
        self.text_embedder = text_embedder
        self.index: Optional[faiss.Index] = None
        self.metadata_store: List[Dict[str, Any]] = []  # To store metadata in order
        self.dim = dim
        self.current_index_file_path = None

    def add_text(self, text: str, metadata: dict):
        """
        Add single text and its metadata to FAISS index.
        """
        embedding = self.text_embedder.embed_text(text)

        if self.index is None:
            raise "No index was created neither loaded"

        self.index.add(embedding.reshape(1, -1))
        self.metadata_store.append(metadata)
        self.save_index()

    def add_texts(self, texts: list[str], metadatas: list[dict]):
        """
        Add multiple texts and their metadata to FAISS index.
        """
        if len(texts) != len(metadatas):
            raise ValueError("texts and metadatas must have the same length.")

        embeddings = [self.text_embedder.embed_text(t) for t in texts]
        embeddings = np.array(embeddings, dtype="float32")

        if self.index is None:
            raise "No index was created neither loaded"


        self.index.add(embeddings)
        self.metadata_store.extend(metadatas)

    def create_index(self, index_pkl_path: str):
        """
        Create index if not found, else load it. Ensure .joblib extension.
        """
        if not index_pkl_path.endswith(".joblib"):
            index_pkl_path += ".joblib"

        if os.path.exists(index_pkl_path):
            self.load_index(index_pkl_path)
            
        else:
            # Initialize new FAISS index with the specified dimension
            self.index = faiss.IndexFlatL2(self.dim)
            self.metadata_store = []
            # Save the newly created index
            self.current_index_file_path = index_pkl_path
            self.save_index()
            print(f"Created a new FAISS index: {index_pkl_path}")
        
        self.current_index_file_path = index_pkl_path
        return self.get_activities_metadata()

    def save_index(self, compress: int = 3):
        """
        Save the FAISS index and metadata to a file using joblib.
        
        Args:
            index_pkl_path: Path to save the index file
            compress: Compression level (0-9). Higher values mean more compression,
                    but slower saving/loading. 3 is a good balance.
        """
    


        if not self.index:
            raise ValueError("No index to save")
            
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(self.current_index_file_path)), exist_ok=True)
        
        # Prepare data to save
        data = {
            'index': self.index,
            'metadata': self.metadata_store,
            'dim': self.dim,
            'faiss_version': faiss.__version__  # Store FAISS version for compatibility
        }
        
        # Save with joblib
        joblib.dump(data, self.current_index_file_path, compress=compress)
    
    def load_index(self, index_pkl_path: str):
        """
        Load a FAISS index and metadata from a file saved with joblib.
        
        Args:
            index_pkl_path: Path to the saved index file
            
        Returns:
            dict: The loaded data containing index and metadata
        """
        if not index_pkl_path.endswith(".joblib"):
            index_pkl_path += ".joblib"

        if not os.path.exists(index_pkl_path):
            raise FileNotFoundError(f"Index file not found: {index_pkl_path}")
            
        # Load with joblib
        data = joblib.load(index_pkl_path)
        
        # Check FAISS version compatibility
        if 'faiss_version' in data and data['faiss_version'] != faiss.__version__:
            print(f"Warning: FAISS version mismatch. Saved: {data['faiss_version']}, "
                  f"Current: {faiss.__version__}. This might cause issues.")
            
        self.index = data['index']
        self.metadata_store = data.get('metadata', [])
        self.dim = data.get('dim', self.dim)
        self.current_index_file_path = index_pkl_path

        
        return self.get_activities_metadata()
    

    
    def get_activities_metadata(self) -> Activities:
        """
        Get the activities metadata.
        """
        return Activities(activities=[activity_dict['activity'] for activity_dict in self.metadata_store])
  


    def search_by_text(self, query: str, k: int = 5) -> Activities:
        """
        Search for the top-k most similar items to the query text.
        """
        if self.index is None:
            raise ValueError("Index is empty. Add texts first.")

        query_embedding = self.text_embedder.embed_text(query)
        query_embedding = np.array(query_embedding).reshape(1, -1).astype('float32')

        distances, indices = self.index.search(query_embedding, k)

        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < len(self.metadata_store):
                results.append(self.metadata_store[idx]['activity'])


        return Activities(activities=results)

