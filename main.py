import os
import logging
import asyncio
import signal
import re
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.exceptions import TelegramRetryAfter, TelegramConflictError
import google.generativeai as genai

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Инициализация бота и диспетчера
bot = Bot(token=os.getenv('TELEGRAM_TOKEN'))
dp = Dispatcher()

# Настройка Google Gemini
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')

def escape_markdown_v2(text: str) -> str:
    """
    Обрабатывает текст для корректного отображения в Markdown
    
    Args:
        text: Исходный текст
        
    Returns:
        str: Текст, готовый для отображения в Markdown
    """
    # Заменяем множественные пробелы на один
    text = re.sub(r'\s+', ' ', text)
    
    
    return text

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start - приветственное сообщение"""
    await message.answer(
        "👋 Привет! Я бот, использующий Google Gemini AI. "
        "Просто напишите мне сообщение, и я отвечу вам.",
        parse_mode="Markdown"
    )

# Обработчик команды /help
@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help - информация о возможностях бота"""
    await message.answer(
        "🤖 Я могу:\n"
        "• Отвечать на ваши вопросы\n"
        "• Помогать с задачами\n"
        "• Поддерживать диалог\n\n"
        "Просто напишите мне сообщение!",
        parse_mode="Markdown"
    )

async def send_message_with_retry(message: Message, text: str, retry_count: int = 3, parse_mode: str = "Markdown") -> Message:
    """
    Отправляет сообщение с повторными попытками при ошибке флуд-контроля
    
    Args:
        message: Исходное сообщение
        text: Текст для отправки
        retry_count: Количество попыток отправки
        parse_mode: Режим парсинга (Markdown или None)
        
    Returns:
        Message: Объект отправленного сообщения
        
    Raises:
        Exception: Если не удалось отправить сообщение после всех попыток
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

async def update_message_with_retry(message: Message, text: str, retry_count: int = 3, parse_mode: str = "Markdown") -> bool:
    """
    Обновляет существующее сообщение с повторными попытками при ошибке флуд-контроля
    
    Args:
        message: Сообщение для обновления
        text: Новый текст
        retry_count: Количество попыток обновления
        parse_mode: Режим парсинга (Markdown или None)
        
    Returns:
        bool: True если обновление успешно, False в противном случае
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

# Обработчик всех остальных сообщений
@dp.message()
async def handle_message(message: Message):
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
        response = model.generate_content(
            message.text,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                top_p=0.8,
                top_k=40,
                max_output_tokens=2048,
            )
        )
        
        # Получаем текст ответа
        response_text = response.text
        
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
        await message.answer("Извините, произошла ошибка при обработке вашего сообщения.", parse_mode=None)

async def main():
    """Основная функция запуска бота"""
    # Настройка graceful shutdown
    loop = asyncio.get_event_loop()
    
    def shutdown_handler(signum, frame):
        """Обработчик сигналов завершения"""
        logger.info("Получен сигнал завершения, останавливаем бота...")
        loop.stop()
    
    # Регистрируем обработчики сигналов
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, shutdown_handler)
    
    try:
        # Запускаем бота
        logger.info("Бот запущен и готов к работе!")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except TelegramConflictError:
        # Обработка конфликта с другим экземпляром бота
        logger.error("Обнаружен конфликт с другим экземпляром бота")
        logger.info("Ждем 10 секунд перед повторной попыткой...")
        await asyncio.sleep(10)
        logger.info("Пробуем запустить бота снова...")
        await main()
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
    finally:
        # Завершение работы бота
        logger.info("Завершение работы бота...")
        await bot.session.close()

if __name__ == '__main__':
    try:
        # Запуск бота
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Необработанная ошибка: {str(e)}")
    finally:
        logger.info("Программа завершена")