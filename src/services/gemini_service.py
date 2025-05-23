import os
import tempfile
import google.generativeai as genai
from src.config.config import GOOGLE_API_KEY, MODEL_CONFIG
import logging

class GeminiService:
    def __init__(self):
        """Инициализация сервиса Gemini"""
        genai.configure(api_key=GOOGLE_API_KEY)
        # Модель для текста
        self.text_model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
        # Модель для мультимодального контента (с поддержкой изображений)
        self.vision_model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
    
    async def generate_response(self, text: str) -> str:
        """
        Генерирует ответ с помощью Gemini
        
        Args:
            text: Входной текст
            
        Returns:
            str: Сгенерированный ответ
        """
        response = self.text_model.generate_content(
            text,
            generation_config=genai.types.GenerationConfig(
                temperature=MODEL_CONFIG['temperature'],
                top_p=MODEL_CONFIG['top_p'],
                top_k=MODEL_CONFIG['top_k'],
                max_output_tokens=MODEL_CONFIG['max_output_tokens'],
            )
        )
        return response.text
    
    async def analyze_image(self, image_data: bytes, prompt: str = None) -> str:
        """
        Анализирует изображение с помощью Gemini
        
        Args:
            image_data: Байты изображения
            prompt: Дополнительный текст для описания запроса (опционально)
            
        Returns:
            str: Результат анализа изображения
        """
        # Проверяем, что изображение не пустое
        if not image_data or len(image_data) < 100:
            raise ValueError("Изображение пустое или слишком маленькое")
            
        try:
            # Формируем текст запроса
            query_text = "Опиши, что изображено на этом изображении."
            if prompt:
                query_text = prompt
            
            # Прямой способ через PIL
            try:
                from PIL import Image
                import io
                
                # Создаем изображение из байтов
                image = Image.open(io.BytesIO(image_data))
                
                # Логируем информацию об изображении
                logging.info(f"Изображение загружено: {image.format}, размер {image.size}")
                
                # Отправляем запрос на анализ изображения с использованием PIL
                logging.info("Отправляем запрос на анализ изображения через PIL")
                response = self.vision_model.generate_content(
                    [query_text, image],
                    generation_config=genai.types.GenerationConfig(
                        temperature=MODEL_CONFIG['temperature'],
                        top_p=MODEL_CONFIG['top_p'],
                        top_k=MODEL_CONFIG['top_k'],
                        max_output_tokens=MODEL_CONFIG['max_output_tokens'],
                    )
                )
                
                # Проверяем, что ответ есть
                if not response or not hasattr(response, 'text') or not response.text:
                    logging.error("Получен пустой ответ от API")
                    return "Не удалось распознать изображение. Получен пустой ответ от API."
                
                logging.info("Получен ответ через PIL")
                return response.text
                
            except ImportError:
                logging.warning("PIL не установлен, используем временный файл")
                # Если PIL не установлен, используем временный файл
                temp_path = None
                
                try:
                    # Создаем временный файл
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                        temp_file.write(image_data)
                        temp_path = temp_file.name
                    
                    logging.info(f"Изображение сохранено во временный файл: {temp_path}")
                    
                    # Создаем объект для передачи в API
                    image_parts = genai.upload_file(temp_path)
                    
                    # Отправляем запрос на анализ изображения через файл
                    logging.info("Отправляем запрос на анализ изображения через файл")
                    response = self.vision_model.generate_content(
                        [query_text, image_parts],
                        generation_config=genai.types.GenerationConfig(
                            temperature=MODEL_CONFIG['temperature'],
                            top_p=MODEL_CONFIG['top_p'],
                            top_k=MODEL_CONFIG['top_k'],
                            max_output_tokens=MODEL_CONFIG['max_output_tokens'],
                        )
                    )
                    
                    # Проверяем, что ответ есть
                    if not response or not hasattr(response, 'text') or not response.text:
                        logging.error("Получен пустой ответ от API")
                        return "Не удалось распознать изображение. Получен пустой ответ от API."
                    
                    logging.info("Получен ответ через временный файл")
                    return response.text
                    
                finally:
                    # Удаляем временный файл
                    if temp_path and os.path.exists(temp_path):
                        os.remove(temp_path)
                        logging.info(f"Временный файл удален: {temp_path}")
                    
        except Exception as e:
            # Логируем ошибку и пробрасываем выше для обработки
            logging.error(f"Ошибка при анализе изображения: {str(e)}")
            raise e
    
    async def analyze_file(self, file_data: bytes, file_name: str) -> str:
        """
        Анализирует содержимое файла с помощью Gemini
        
        Args:
            file_data: Байты файла
            file_name: Имя файла с расширением
            
        Returns:
            str: Результат анализа файла
        """
        # Проверка входных данных
        if not file_data:
            logging.error("Получены пустые данные файла")
            return "Файл пуст или не может быть прочитан."
            
        if not file_name:
            file_name = "unknown_file"
            logging.warning("Имя файла не указано, используется значение по умолчанию")
        
        # Извлекаем расширение файла
        _, ext = os.path.splitext(file_name)
        ext = ext.lower() if ext else ""
        
        logging.info(f"Обрабатываем файл: {file_name}, расширение: {ext}, размер: {len(file_data)} байт")
        
        # Обрабатываем различные типы файлов
        if ext in ['.txt', '.py', '.js', '.html', '.css', '.json', '.md']:
            # Для текстовых файлов пытаемся декодировать содержимое как текст
            try:
                encoding = 'utf-8'
                try:
                    file_content = file_data.decode(encoding)
                except UnicodeDecodeError:
                    # Пробуем другие кодировки
                    for enc in ['cp1251', 'latin-1', 'iso-8859-1']:
                        try:
                            file_content = file_data.decode(enc)
                            encoding = enc
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        raise UnicodeDecodeError("Не удалось определить кодировку файла")
                
                logging.info(f"Файл успешно декодирован с кодировкой {encoding}")
                
                # Ограничиваем размер содержимого
                content_limit = 4000
                truncated = len(file_content) > content_limit
                trimmed_content = file_content[:content_limit]
                
                # Формируем запрос
                prompt = f"Это содержимое файла {file_name}. Проанализируй его и ответь на вопросы:\n1. Что это за файл?\n2. Какую информацию он содержит?\n3. Есть ли в нем что-то интересное?\n\nСодержание файла:\n```\n{trimmed_content}```"
                
                if truncated:
                    prompt += "\n\n(Файл слишком большой, показана только часть содержимого)"
                
                logging.info("Отправляем запрос на анализ текстового файла")
                response = self.text_model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=MODEL_CONFIG['temperature'],
                        top_p=MODEL_CONFIG['top_p'],
                        top_k=MODEL_CONFIG['top_k'],
                        max_output_tokens=MODEL_CONFIG['max_output_tokens'],
                    )
                )
                
                # Проверяем ответ
                if not response or not hasattr(response, 'text') or not response.text:
                    logging.error("Получен пустой ответ от API при анализе текстового файла")
                    return "Не удалось проанализировать файл. Получен пустой ответ от API."
                
                logging.info("Получен ответ на анализ текстового файла")
                return response.text
                
            except UnicodeDecodeError as e:
                logging.warning(f"Не удалось декодировать файл как текст: {str(e)}")
                return "Не удалось прочитать содержимое этого файла. Возможно, это бинарный файл."
                
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            # Для изображений используем анализ изображений
            logging.info("Перенаправляем файл изображения на анализ изображений")
            return await self.analyze_image(file_data, f"Это изображение из файла {file_name}. Опиши подробно, что на нем изображено.")
            
        else:
            # Для неподдерживаемых типов файлов
            logging.warning(f"Неподдерживаемое расширение файла: {ext}")
            return f"Извините, я не могу обработать файлы с расширением {ext}. Пожалуйста, отправьте текстовый файл или изображение." 