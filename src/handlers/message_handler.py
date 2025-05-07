import re
import logging
from aiogram import types
from src.utils.message_utils import send_message_with_retry, update_message_with_retry
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

class MessageHandler:
    def __init__(self):
        """Инициализация обработчика сообщений"""
        self.gemini_service = GeminiService()

    async def handle_message(self, message: types.Message):
        """
        Обработчик всех текстовых сообщений
        
        Args:
            message: Входящее сообщение
        """
        try:
            # Логируем получение сообщения
            logger.info(f"Получено сообщение от пользователя {message.from_user.id}: {message.text}")
            
            # Отправляем статус "печатает..."
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
            
            # Генерируем ответ с помощью Gemini
            response_text = await self.gemini_service.generate_response(message.text)
            
            # Создаем первое сообщение с плейсхолдером
            current_message = await send_message_with_retry(message, "...", parse_mode=None)
            
            # Разбиваем текст на предложения для постепенного появления
            sentences = re.split(r'(?<=[.!?])\s+', response_text)
            current_text = ""
            
            # Постепенно добавляем предложения
            for sentence in sentences:
                if sentence.strip():
                    # Добавляем пробел перед предложением, если это не первое предложение
                    if current_text:
                        current_text += " " + sentence
                    else:
                        current_text = sentence
                    
                    try:
                        # Пробуем обновить сообщение
                        if not await update_message_with_retry(current_message, current_text, parse_mode=None):
                            # Если не удалось обновить, создаем новое сообщение
                            current_message = await send_message_with_retry(message, current_text, parse_mode=None)
                    except Exception as e:
                        logger.error(f"Ошибка при обновлении сообщения: {str(e)}")
                        # Если произошла ошибка, пробуем отправить как обычный текст
                        current_message = await send_message_with_retry(message, current_text, parse_mode=None)
                    
                    # Задержка для эффекта печатания
                    await asyncio.sleep(0.5)
            
            logger.info(f"Отправлен ответ пользователю {message.from_user.id}")
            
        except Exception as e:
            # Обработка ошибок
            logger.error(f"Ошибка при обработке сообщения: {str(e)}")
            await send_message_with_retry(
                message,
                "Извините, произошла ошибка при обработке вашего сообщения.",
                parse_mode=None
            ) 