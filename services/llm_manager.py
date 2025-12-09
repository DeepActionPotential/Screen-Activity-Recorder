import google.generativeai as genai
from typing import Optional, Union
from PIL import Image
import os
from schemas.base_models import LLMManager


class GeminiAPIManager(LLMManager):
    """
    A manager for the Gemini API. This class provides convenience methods to interact with the Gemini API.

    Args:
        api_key (str): The API key to use for the requests.
        text_model_name (str): The name of the model to use for text prompts.
        vision_model_name (str): The name of the model to use for vision prompts.

    Attributes:
        api_key (str): The API key to use for the requests.
        text_model_name (str): The name of the model to use for text prompts.
        vision_model_name (str): The name of the model to use for vision prompts.
        text_model (genai.GenerativeModel): The model to use for text prompts.
        vision_model (genai.GenerativeModel): The model to use for vision prompts.
    """

    def __init__(self, api_key: str, text_model_name:str, vision_model_name:str):

        self.api_key = api_key
        self.text_model_name = text_model_name
        self.vision_model_name = vision_model_name
        self._initialize_api()

        self.text_model = genai.GenerativeModel(self.text_model_name)
        self.vision_model = genai.GenerativeModel(self.vision_model_name)


    def _initialize_api(self):
        """Initialize the API by setting the API key."""
        genai.configure(api_key=self.api_key)

    def is_api_key_valid(self) -> bool:
        """Checks if the API key is valid by making a test call.

        Returns:
            bool: If the API key is valid.
        """
        try:
            models = genai.list_models()
            return bool(models)
        except Exception:
            return False

    def send_text_prompt(self, prompt: str) -> Optional[str]:
        """Sends a text-only prompt to the model.

        Args:
            prompt (str): The text to send to the model.

        Returns:
            Optional[str]: The response from the model.
        """
        try:
            response = self.text_model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error in send_text_prompt: {e}")
            return None

    def send_image_prompt(self, image: Image.Image, prompt: str = "") -> Optional[str]:
        """Sends a prompt with only an image (optional text) to the model.

        Args:
            image (str): PIL image.
            prompt (str): The text to send to the model (optional).

        Returns:
            Optional[str]: The response from the model.
        """
        try:
            response = self.vision_model.generate_content([prompt, image])
            return response.text
        except Exception as e:
            print(f"Error in send_image_prompt: {e}")
            return ""

    def send_multimodal_prompt(self, image_path: str, prompt: str) -> Optional[str]:
        """Sends a prompt with both text and image to the model.

        Args:
            prompt (str): The text to send to the model.
            image_path (str): The path to the image.

        Returns:
            Optional[str]: The response from the model.
        """
        return self.send_image_prompt(image_path=image_path, prompt=prompt)



