import asyncio
import logging
from aiogram import types
from aiogram.exceptions import TelegramRetryAfter

logger = logging.getLogger(__name__)

async def send_message_with_retry(message: types.Message, text: str, retry_count: int = 3, parse_mode: str = None, reply_markup = None) -> types.Message:
    """
    Отправляет сообщение с повторными попытками при ошибке флуд-контроля
    """
    for attempt in range(retry_count):
        try:
            return await message.answer(text, parse_mode=parse_mode, reply_markup=reply_markup)
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

async def update_message_with_retry(message: types.Message, text: str, retry_count: int = 3, parse_mode: str = None, reply_markup = None) -> bool:
    """
    Обновляет существующее сообщение с повторными попытками при ошибке флуд-контроля
    
    Args:
        message: Сообщение для обновления
        text: Новый текст
        retry_count: Количество попыток обновления
        parse_mode: Режим парсинга (Markdown или HTML или None)
        reply_markup: Разметка клавиатуры
        
    Returns:
        bool: True если обновление успешно, False в противном случае
    """
    if not message:
        logger.error("Попытка обновить пустое сообщение")
        return False
        
    for attempt in range(retry_count):
        try:
            await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
            return True
        except TelegramRetryAfter as e:
            if attempt < retry_count - 1:
                wait_time = e.retry_after
                logger.warning(f"Флуд-контроль, ожидание {wait_time} секунд...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Не удалось обновить сообщение после {retry_count} попыток из-за флуд-контроля")
                return False
        except Exception as e:
            logger.error(f"Ошибка при обновлении сообщения: {str(e)}")
            if "message is not modified" in str(e).lower():
                # Если сообщение не изменилось, считаем это успехом
                logger.info("Сообщение не изменилось, пропускаем обновление")
                return True
            elif "message to edit not found" in str(e).lower():
                logger.error("Сообщение для редактирования не найдено")
                return False
            elif attempt < retry_count - 1:
                # Если это не последняя попытка, ждем и пробуем снова
                logger.warning(f"Ошибка при обновлении сообщения, повторная попытка ({attempt+1}/{retry_count})")
                await asyncio.sleep(1)
            else:
                return False
                
    return False 