
from schemas.base_models import KeywordExtractor
from keybert import KeyBERT



class KeyBERTKeywrodExtractor(KeywordExtractor):
    def __init__(self):
        self.kw_model = KeyBERT()

    def extract_keywords(self, text: str, num_keywords: int = 10) -> str:
        """
        Extracts keywords from the given text using KeyBERT.

        Args:
            text (str): The input text from which to extract keywords.
            num_keywords (int): The maximum number of keywords to extract.

        Returns:
            list[str]: A list of extracted keywords.
        """
        if not text:
            return ""

        keywords = self.kw_model.extract_keywords(text, top_n=num_keywords)

        return " ".join([keyword[0] for keyword in keywords])

