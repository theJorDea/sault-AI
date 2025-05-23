from aiogram import types
from aiogram.filters import Command
from src.utils.message_utils import send_message_with_retry
from src.utils.keyboard_utils import get_main_keyboard

async def cmd_start(message: types.Message):
    """Обработчик команды /start - приветственное сообщение"""
    await send_message_with_retry(
        message,
        "👋 Привет! Я бот, использующий Google Gemini AI.\n"
        "Я могу отвечать на ваши вопросы, анализировать изображения и обрабатывать файлы.\n\n"
        "Используйте кнопки ниже или просто напишите мне сообщение.",
        parse_mode=None,
        reply_markup=get_main_keyboard()
    )

async def cmd_help(message: types.Message):
    """Обработчик команды /help - информация о возможностях бота"""
    await send_message_with_retry(
        message,
        "🤖 Я могу:\n"
        "• Отвечать на ваши вопросы\n"
        "• Анализировать изображения\n"
        "• Обрабатывать файлы\n"
        "• Помогать с разными задачами\n\n"
        "Используйте кнопки меню или просто напишите мне сообщение!",
        parse_mode=None,
        reply_markup=get_main_keyboard()
    )

async def cmd_about(message: types.Message):
    """Обработчик информации о боте"""
    await send_message_with_retry(
        message,
        "ℹ️ О боте:\n"
        "Я работаю на базе Google Gemini AI, одной из самых продвинутых языковых моделей.\n"
        "Версия: 1.0\n"
        "Gemini Model: gemini-2.5-flash-preview-04-17",
        parse_mode=None,
        reply_markup=get_main_keyboard()
    ) 