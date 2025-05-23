import asyncio
import logging
import signal
import os # Добавлено для os.getenv
from dotenv import load_dotenv # Добавлено для загрузки .env
from aiogram import Bot, Dispatcher, types # Добавлено types для Message
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from src.config.config import TELEGRAM_TOKEN, LOGGING_CONFIG
from src.handlers.command_handlers import cmd_start, cmd_help, cmd_about
from src.handlers.message_handler import MessageHandler, BotState

import google.generativeai as genai # Основной импорт для Gemini

# Загрузка переменных окружения .env
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=LOGGING_CONFIG['level'],
    format=LOGGING_CONFIG['format']
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
# Используем хранилище состояний в памяти
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Настройка Google Gemini
GEMINI_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GEMINI_API_KEY:
    logger.error("Переменная окружения GOOGLE_API_KEY не найдена!")
    # Тут можно либо выйти, либо установить model в None и обрабатывать это
    # exit()
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17') # Или ваша актуальная модель

# Инициализация обработчика сообщений
message_handler = MessageHandler()

# Регистрация обработчиков команд
dp.message.register(cmd_about, Command("about"))

# Регистрация обработчиков медиа-контента
dp.message.register(message_handler.handle_photo, lambda message: message.photo)
dp.message.register(message_handler.handle_document, lambda message: message.document)

# Регистрация обработчика текстовых сообщений (должен быть последним)
dp.message.register(message_handler.handle_message)

GENERATION_CONFIG = genai.types.GenerationConfig(
    temperature=0.7,
    top_p=0.8,
    top_k=40,
    max_output_tokens=1024,  # Уменьшаем максимальную длину ответа
)

def escape_html(text: str) -> str:
    """
    Обрабатывает текст для корректного отображения в HTML.
    Заменяет специальные символы HTML на их сущности.
    Args:
        text: Исходный текст
    Returns:
        str: Текст, готовый для отображения в HTML
    """
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    # Экранируем точку, как того требует ошибка Telegram API в некоторых случаях
    text = text.replace('.', '&#46;') 
    # При необходимости можно добавить text = text.replace('"', '&quot;')
    return text

# Обработчик команды /start
@dp.message(Command("start"))
async def local_cmd_start(message: types.Message):
    """Обработчик команды /start - приветственное сообщение"""
    text_content = (
        "👋 Привет! Я бот, использующий Google Gemini AI. "
        "Просто напишите мне сообщение, и я отвечу вам."
    )
    await message.answer(text_content, parse_mode=None)

# Обработчик команды /help
@dp.message(Command("help"))
async def local_cmd_help(message: types.Message):
    """Обработчик команды /help - информация о возможностях бота"""
    text_content = (
        "🤖 Я могу:\n"
        "• Отвечать на ваши вопросы\n"
        "• Помогать с задачами\n"
        "• Поддерживать диалог\n\n"
        "Просто напишите мне сообщение!"
    )
    await message.answer(text_content, parse_mode=None)

async def send_message_with_retry(message: types.Message, text: str, retry_count: int = 3, parse_mode: str = None) -> types.Message:
    """
    Отправляет сообщение с повторными попытками при ошибке флуд-контроля
    """
    for _ in range(retry_count):
        try:
            return await message.answer(text, parse_mode=parse_mode)
        except Exception as e:
            logger.warning(f"Ошибка при отправке сообщения: {str(e)}")
    raise Exception("Превышено максимальное количество попыток отправки сообщения")

async def update_message_with_retry(message: types.Message, text: str, retry_count: int = 3, parse_mode: str = None) -> bool:
    """
    Обновляет существующее сообщение с повторными попытками при ошибке флуд-контроля
    """
    for _ in range(retry_count):
        try:
            result = await message.edit_text(text, parse_mode=parse_mode)
            return bool(result)
        except Exception as e:
            logger.warning(f"Ошибка при обновлении сообщения: {str(e)}")
    return False

# Обработчик всех остальных сообщений
@dp.message()
async def handle_message(message: types.Message):
    """
    Обработчик всех текстовых сообщений
    
    Args:
        message: Входящее сообщение
    """
    try:
        # Логируем получение сообщения
        logger.info(f"Получено сообщение от пользователя {message.from_user.id}: {message.text}")
        
        # Отправляем начальное сообщение-плейсхолдер
        placeholder_text = "🤖 AI: ..."
        current_bot_message = await send_message_with_retry(
            message, 
            placeholder_text, 
            parse_mode=None
        )
        
        # Отправляем статус "печатает..."
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        
        # Генерируем ответ с помощью Gemini
        response = model.generate_content(
            message.text,
            generation_config=GENERATION_CONFIG
        )
        
        # Получаем текст ответа
        response_text_from_ai = response.text
        
        # Формируем итоговый текст без экранирования
        final_text_to_send = "🤖 AI: " + response_text_from_ai
        
        # Обновляем сообщение-плейсхолдер полным ответом AI без форматирования
        if not await update_message_with_retry(current_bot_message, final_text_to_send, parse_mode=None):
            # Если обновление не удалось (например, сообщение слишком старое), отправляем как новое
            logger.warning(f"Не удалось обновить сообщение {current_bot_message.message_id}, отправляем как новое.")
            await send_message_with_retry(message, final_text_to_send, parse_mode=None)
        
        logger.info(f"Отправлен ответ пользователю {message.from_user.id}")
        
    except Exception as e:
        # Обработка ошибок
        logger.error(f"Ошибка при обработке сообщения: {str(e)}")
        error_message_text = "🤖 AI: Извините, произошла ошибка при обработке вашего сообщения."
        await message.answer(error_message_text, parse_mode=None)

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