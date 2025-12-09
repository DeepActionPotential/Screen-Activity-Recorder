from pydantic import BaseModel
from typing import List, Union



class TextOCRChunk(BaseModel):
    text: str
    text_bounding_box: List[List[Union[int, float]]]
    confidence_score: float


class TextOCRChunks(BaseModel):
    text_ocr_chunks: list[TextOCRChunk]

    
    def to_list(self) -> List[TextOCRChunk]:
        """
        Convert text_ocr_chunks to a list of dicts.
        """
        return [chunk for chunk in self.text_ocr_chunks]

    class Config:
        arbitrary_types_allowed = True
    

    



