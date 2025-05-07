from aiogram import types
from aiogram.filters import Command
from src.utils.message_utils import send_message_with_retry

async def cmd_start(message: types.Message):
    """Обработчик команды /start - приветственное сообщение"""
    await send_message_with_retry(
        message,
        "👋 Привет! Я бот, использующий Google Gemini AI. "
        "Просто напишите мне сообщение, и я отвечу вам.",
        parse_mode="Markdown"
    )

async def cmd_help(message: types.Message):
    """Обработчик команды /help - информация о возможностях бота"""
    await send_message_with_retry(
        message,
        "🤖 Я могу:\n"
        "• Отвечать на ваши вопросы\n"
        "• Помогать с задачами\n"
        "• Поддерживать диалог\n\n"
        "Просто напишите мне сообщение!",
        parse_mode="Markdown"
    ) 