import asyncio
import logging
import signal
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from src.config.config import TELEGRAM_TOKEN, LOGGING_CONFIG
from src.handlers.command_handlers import cmd_start, cmd_help
from src.handlers.message_handler import MessageHandler

# Настройка логирования
logging.basicConfig(
    level=LOGGING_CONFIG['level'],
    format=LOGGING_CONFIG['format']
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Инициализация обработчика сообщений
message_handler = MessageHandler()

# Регистрация обработчиков команд
dp.message.register(cmd_start, Command("start"))
dp.message.register(cmd_help, Command("help"))
dp.message.register(message_handler.handle_message)

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