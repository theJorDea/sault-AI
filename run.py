import asyncio
import os
import sys
import logging

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.abspath('.'))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Импортируем основную функцию из src/main.py
from src.main import main

if __name__ == '__main__':
    try:
        # Запуск бота
        logger.info("Запуск бота через run.py")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except ImportError as e:
        logger.error(f"Ошибка импорта: {str(e)}")
        logger.info("Проверьте, что установлены все зависимости (pip install -r requirements.txt)")
    except Exception as e:
        logger.error(f"Необработанная ошибка: {str(e)}")
    finally:
        logger.info("Программа завершена")                                                                                                            