from aiogram.types import KeyboardButton, KeyboardBuilder

def get_main_keyboard() -> KeyboardBuilder:
    """
    Создает основную клавиатуру с кнопками основного меню
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура с основными кнопками
    """
    keyboard = KeyboardBuilder()
    keyboard.row(KeyboardButton(text="🔍 Задать вопрос"))
    keyboard.row(KeyboardButton(text="📷 Анализ изображения"), KeyboardButton(text="📁 Отправить файл"))
    keyboard.row(KeyboardButton(text="❓ Помощь"), KeyboardButton(text="ℹ️ О боте"))
    return keyboard

def get_cancel_keyboard() -> KeyboardBuilder:
    """
    Создает клавиатуру с кнопкой отмены
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопкой отмены
    """
    keyboard = KeyboardBuilder()
    keyboard.row(KeyboardButton(text="❌ Отмена"))
    return keyboard 