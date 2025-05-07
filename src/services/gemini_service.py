import google.generativeai as genai
from src.config.config import GOOGLE_API_KEY, MODEL_CONFIG

class GeminiService:
    def __init__(self):
        """Инициализация сервиса Gemini"""
        genai.configure(api_key=GOOGLE_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')

    async def generate_response(self, text: str) -> str:
        """
        Генерирует ответ с помощью Gemini
        
        Args:
            text: Входной текст
            
        Returns:
            str: Сгенерированный ответ
        """
        response = self.model.generate_content(
            text,
            generation_config=genai.types.GenerationConfig(
                temperature=MODEL_CONFIG['temperature'],
                top_p=MODEL_CONFIG['top_p'],
                top_k=MODEL_CONFIG['top_k'],
                max_output_tokens=MODEL_CONFIG['max_output_tokens'],
            )
        )
        return response.text 