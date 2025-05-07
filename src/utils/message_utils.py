import asyncio
import logging
from aiogram import types
from aiogram.exceptions import TelegramRetryAfter

logger = logging.getLogger(__name__)

async def send_message_with_retry(message: types.Message, text: str, retry_count: int = 3, parse_mode: str = "Markdown") -> types.Message:
    """
    Отправляет сообщение с повторными попытками при ошибке флуд-контроля
    """
    for attempt in range(retry_count):
        try:
            return await message.answer(text, parse_mode=parse_mode)
        except TelegramRetryAfter as e:
            if attempt < retry_count - 1:
                wait_time = e.retry_after
                logger.warning(f"Флуд-контроль, ожидание {wait_time} секунд...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Не удалось отправить сообщение после {retry_count} попыток")
                raise
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {str(e)}")
            raise
    raise Exception("Не удалось отправить сообщение")

async def update_message_with_retry(message: types.Message, text: str, retry_count: int = 3, parse_mode: str = "Markdown") -> bool:
    """
    Обновляет существующее сообщение с повторными попытками при ошибке флуд-контроля
    """
    for attempt in range(retry_count):
        try:
            await message.edit_text(text, parse_mode=parse_mode)
            return True
        except TelegramRetryAfter as e:
            if attempt < retry_count - 1:
                wait_time = e.retry_after
                logger.warning(f"Флуд-контроль, ожидание {wait_time} секунд...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Не удалось обновить сообщение после {retry_count} попыток")
                return False
        except Exception as e:
            logger.error(f"Ошибка при обновлении сообщения: {str(e)}")
            return False
    return False 