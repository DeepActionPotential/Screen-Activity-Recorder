from pydantic import BaseModel
from typing import List



class NEREntity(BaseModel):
    entity_text: str 
    entity_label: str
    confidence_score: float


class NEREntites(BaseModel):
    entities: List[NEREntity]


    def to_list(self) -> List[NEREntity]:
        """
        Convert entities to a list of dicts.
        """
        return [entity for entity in self.entities]

    