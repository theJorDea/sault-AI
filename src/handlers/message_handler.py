import re
import logging
import asyncio
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.utils.message_utils import send_message_with_retry, update_message_with_retry
from src.utils.keyboard_utils import get_main_keyboard, get_cancel_keyboard
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

# Определение состояний для конечного автомата
class BotState(StatesGroup):
    WAITING_FOR_PHOTO = State()  # Ожидание фото
    WAITING_FOR_FILE = State()   # Ожидание файла

class MessageHandler:
    def __init__(self):
        """Инициализация обработчика сообщений"""
        self.gemini_service = GeminiService()
        self._loading_tasks = {}  # Словарь для хранения задач анимации загрузки
        self._loading_messages = {}  # Словарь для хранения сообщений с индикаторами загрузки

    async def _animate_loading(self, message: types.Message, prefix: str = "🤖 AI: Обрабатываю ваш запрос"):
        """
        Анимирует индикатор загрузки, меняя количество точек
        
        Args:
            message: Сообщение, которое будет обновляться
            prefix: Префикс текста загрузки
        """
        dots = 0
        max_dots = 3
        try:
            # Отправляем первоначальное сообщение с более заметной анимацией
            initial_text = f"{prefix}{'.' * dots} ⏳"
            loading_message = await send_message_with_retry(message, initial_text)
            logger.info(f"Создано сообщение с индикатором загрузки для пользователя {message.from_user.id}: {loading_message.message_id}")
            
            # Сохраняем сообщение в словаре для возможности получения его позже
            self._loading_messages[message.from_user.id] = loading_message
            
            # Начинаем анимацию с более длинной задержкой
            while True:
                # Увеличиваем задержку для лучшей видимости анимации
                await asyncio.sleep(1.2)  # Увеличиваем задержку с 0.7 до 1.2 секунд
                
                # Обновляем количество точек
                dots = (dots + 1) % (max_dots + 1)
                
                # Создаем текст с эмодзи часов для лучшей заметности
                emojis = ["⏳", "⌛", "⏳", "⌛"]
                emoji = emojis[dots % len(emojis)]
                loading_text = f"{prefix}{'.' * dots} {emoji}"
                
                # Обновляем сообщение
                try:
                    success = await update_message_with_retry(
                        loading_message, 
                        loading_text
                    )
                    logger.info(f"Обновлена анимация загрузки для пользователя {message.from_user.id}, точек: {dots}, успех: {success}")
                except Exception as e:
                    logger.error(f"Ошибка при обновлении анимации: {str(e)}")
                
        except asyncio.CancelledError:
            # Задача была отменена - это нормально, просто возвращаем сообщение
            logger.info(f"Анимация загрузки для пользователя {message.from_user.id} была отменена")
            # Задача была отменена, возвращаем сообщение для дальнейшего использования
            return self._loading_messages.get(message.from_user.id)
        except Exception as e:
            logger.error(f"Ошибка в анимации загрузки: {str(e)}")
            return self._loading_messages.get(message.from_user.id)

    async def _start_loading_animation(self, message: types.Message, prefix: str = "🤖 AI: Обрабатываю ваш запрос"):
        """
        Запускает анимацию загрузки в отдельной задаче
        
        Args:
            message: Сообщение от пользователя
            prefix: Префикс текста загрузки
            
        Returns:
            task: Задача анимации
        """
        # Создаем словарь сообщений, если его еще нет
        if not hasattr(self, "_loading_messages"):
            self._loading_messages = {}
        
        user_id = message.from_user.id
        
        # Если уже есть задача для этого пользователя, останавливаем ее
        if user_id in self._loading_tasks:
            try:
                self._loading_tasks[user_id].cancel()
                await asyncio.sleep(0.1)  # Даем время задаче завершиться
                logger.info(f"Остановлена предыдущая анимация для пользователя {user_id}")
            except Exception as e:
                logger.error(f"Ошибка при остановке предыдущей анимации: {str(e)}")
        
        # Создаем и запускаем задачу анимации
        task = asyncio.create_task(self._animate_loading(message, prefix))
        
        # Сохраняем в словаре по ID пользователя
        self._loading_tasks[user_id] = task
        
        return task

    async def _stop_loading_animation(self, user_id: int):
        """
        Останавливает анимацию загрузки
        
        Args:
            user_id: ID пользователя
            
        Returns:
            message: Сообщение с индикатором загрузки
        """
        # Проверяем наличие словаря сообщений
        if not hasattr(self, "_loading_messages"):
            self._loading_messages = {}
            
        # Проверяем, есть ли запущенная задача для пользователя
        if user_id in self._loading_tasks:
            task = self._loading_tasks[user_id]
            
            try:
                # Отменяем задачу
                task.cancel()
                
                # Даем задаче время на отмену
                await asyncio.sleep(0.2)
                
                # Получаем сообщение напрямую из словаря сообщений
                loading_message = self._loading_messages.get(user_id)
                
                if loading_message:
                    logger.info(f"Получено сообщение с индикатором загрузки для пользователя {user_id}: {loading_message.message_id}")
                else:
                    logger.error(f"Сообщение с индикатором загрузки не найдено для пользователя {user_id}")
                
                # Удаляем задачу из словаря
                del self._loading_tasks[user_id]
                
                # Возвращаем сообщение
                return loading_message
            except Exception as e:
                logger.error(f"Ошибка при остановке анимации: {str(e)}")
                # Пытаемся получить сообщение напрямую из словаря
                return self._loading_messages.get(user_id)
        
        # Если задачи нет, пытаемся вернуть сообщение из словаря
        logger.warning(f"Не найдена задача анимации для пользователя {user_id}")
        return self._loading_messages.get(user_id)

    async def handle_message(self, message: types.Message, state: FSMContext = None):
        """
        Обработчик всех текстовых сообщений
        
        Args:
            message: Входящее сообщение
            state: Состояние FSM (если используется)
        """
        user_id = message.from_user.id
        loading_message = None
        
        try:
            # Проверяем текущее состояние
            if state:
                current_state = await state.get_state()
                if current_state:
                    # Если есть активное состояние, проверяем на отмену
                    if message.text == "❌ Отмена":
                        await state.clear()
                        await send_message_with_retry(
                            message,
                            "🤖 AI: Действие отменено. Чем я могу помочь?",
                            reply_markup=get_main_keyboard()
                        )
                        return
                    
                    # Возвращаемся, потому что другие обработчики будут обрабатывать состояния
                    return
            
            # Обрабатываем кнопки меню
            if message.text == "🔍 Задать вопрос":
                await send_message_with_retry(
                    message,
                    "🤖 AI: Пожалуйста, задайте свой вопрос, и я постараюсь на него ответить.",
                    reply_markup=get_main_keyboard()
                )
                return
            
            elif message.text == "📷 Анализ изображения":
                if state:
                    await state.set_state(BotState.WAITING_FOR_PHOTO)
                    await send_message_with_retry(
                        message,
                        "🤖 AI: Отправьте мне изображение, которое нужно проанализировать.",
                        reply_markup=get_cancel_keyboard()
                    )
                return
            
            elif message.text == "📁 Отправить файл":
                if state:
                    await state.set_state(BotState.WAITING_FOR_FILE)
                    await send_message_with_retry(
                        message,
                        "🤖 AI: Отправьте мне файл, который нужно обработать. Я могу анализировать текстовые файлы и изображения.",
                        reply_markup=get_cancel_keyboard()
                    )
                return
            
            elif message.text == "❓ Помощь":
                await send_message_with_retry(
                    message,
                    "🤖 AI: Я могу:\n"
                    "• Отвечать на ваши вопросы\n"
                    "• Анализировать изображения\n"
                    "• Обрабатывать текстовые файлы\n"
                    "• Помогать с разными задачами\n\n"
                    "Используйте кнопки меню или просто напишите мне сообщение!",
                    reply_markup=get_main_keyboard()
                )
                return
            
            elif message.text == "ℹ️ О боте":
                await send_message_with_retry(
                    message,
                    "🤖 AI: О боте:\n"
                    "Я работаю на базе Google Gemini AI, одной из самых продвинутых языковых моделей.\n"
                    "Версия: 1.0\n"
                    "Gemini Model: gemini-2.5-flash-preview-04-17",
                    reply_markup=get_main_keyboard()
                )
                return
            
            # Логируем получение сообщения
            logger.info(f"Получено сообщение от пользователя {user_id}: {message.text}")
            
            # Отправляем статус "печатает..."
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
            
            # Запускаем анимацию загрузки
            await self._start_loading_animation(message)
            logger.info(f"Запущена анимация загрузки для пользователя {user_id}")
            
            # Добавим искусственную задержку, чтобы пользователь успел увидеть анимацию
            await asyncio.sleep(2.0)
            
            try:
                # Генерируем ответ с помощью Gemini
                response_text = await self.gemini_service.generate_response(message.text)
                logger.info(f"Получен ответ от Gemini для пользователя {user_id}")
                
                # Добавим еще небольшую задержку перед остановкой анимации
                await asyncio.sleep(1.0)
                
                # Останавливаем анимацию загрузки и получаем сообщение
                loading_message = await self._stop_loading_animation(user_id)
                
                if loading_message:
                    logger.info(f"Начинаем обновление сообщения для пользователя {user_id}")
                    
                    # Разбиваем текст на более крупные части для более быстрого отображения
                    chunks = re.split(r'(?<=[.!?])\s+(?=[А-ЯA-Z])', response_text)
                    current_text = "🤖 AI: "
                    
                    # Постепенно добавляем части текста
                    for i, chunk in enumerate(chunks):
                        if chunk.strip():
                            # Добавляем пробел перед частью, если это не первая часть
                            if current_text != "🤖 AI: ":
                                current_text += " " + chunk
                            else:
                                current_text += chunk
                            
                            # Обновляем сообщение с новым содержимым
                            try:
                                await update_message_with_retry(loading_message, current_text)
                                logger.info(f"Обновлено сообщение часть {i+1}/{len(chunks)} для пользователя {user_id}")
                                # Увеличиваем задержку между обновлениями
                                await asyncio.sleep(0.5)  # Увеличиваем задержку с 0.2 до 0.5 секунд
                            except Exception as e:
                                logger.error(f"Ошибка при обновлении сообщения: {str(e)}")
                                # Если не удалось обновить, отправляем новое сообщение
                                loading_message = await send_message_with_retry(message, current_text)
                    
                    # В конце добавляем клавиатуру
                    try:
                        await update_message_with_retry(
                            loading_message, 
                            current_text, 
                            reply_markup=get_main_keyboard()
                        )
                        logger.info(f"Добавлена клавиатура к сообщению для пользователя {user_id}")
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении клавиатуры: {str(e)}")
                        # Если не удалось обновить, отправляем новое сообщение с клавиатурой
                        await send_message_with_retry(
                            message, 
                            current_text, 
                            reply_markup=get_main_keyboard()
                        )
                else:
                    logger.error(f"Не удалось получить сообщение с индикатором загрузки для пользователя {user_id}")
                    # Если не получили сообщение с загрузкой, отправляем новое сообщение
                    await send_message_with_retry(
                        message, 
                        f"🤖 AI: {response_text}", 
                        reply_markup=get_main_keyboard()
                    )
                
                logger.info(f"Отправлен ответ пользователю {user_id}")
            except Exception as e:
                # Останавливаем анимацию при ошибке
                if user_id in self._loading_tasks:
                    await self._stop_loading_animation(user_id)
                
                # Обработка ошибок
                logger.error(f"Ошибка при обработке сообщения: {str(e)}")
                await send_message_with_retry(
                    message,
                    f"🤖 AI: Извините, произошла ошибка при обработке вашего сообщения. Ошибка: {str(e)}",
                    reply_markup=get_main_keyboard()
                )
            
        except Exception as e:
            # Обработка ошибок
            logger.error(f"Критическая ошибка при обработке сообщения: {str(e)}")
            
            # Останавливаем анимацию при ошибке, если она запущена
            if user_id in self._loading_tasks:
                await self._stop_loading_animation(user_id)
            
            await send_message_with_retry(
                message,
                f"🤖 AI: Извините, произошла ошибка при обработке вашего сообщения. Ошибка: {str(e)}",
                reply_markup=get_main_keyboard()
            )
            
    async def handle_photo(self, message: types.Message, state: FSMContext = None):
        """
        Обработчик фотографий
        
        Args:
            message: Сообщение с фотографией
            state: Состояние FSM (если используется)
        """
        user_id = message.from_user.id
        loading_message = None
        
        try:
            # Логируем получение изображения
            logger.info(f"Получено изображение от пользователя {user_id}")
            
            # Отправляем статус "печатает..."
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
            
            # Запускаем анимацию загрузки
            await self._start_loading_animation(message, "🤖 AI: Анализирую изображение")
            logger.info(f"Запущена анимация анализа изображения для пользователя {user_id}")
            
            try:
                # Получаем фото в максимальном разрешении
                photo = message.photo[-1]
                file = await message.bot.get_file(photo.file_id)
                file_content = await message.bot.download_file(file.file_path)
                
                # Сохраняем фото
                photo_data = file_content.read()
                logger.info(f"Получены данные изображения размером {len(photo_data)} байт")
                
                # Анализируем изображение
                prompt = "Опиши, что изображено на этом фото."
                if message.caption:
                    prompt = f"Опиши, что изображено на этом фото. Пользователь добавил: {message.caption}"
                
                # Получаем результат анализа
                logger.info(f"Отправляем изображение на анализ")
                result = await self.gemini_service.analyze_image(photo_data, prompt=prompt)
                logger.info(f"Получен результат анализа изображения для пользователя {user_id}")
                
                # Останавливаем анимацию загрузки и получаем сообщение
                loading_message = await self._stop_loading_animation(user_id)
                
                if loading_message:
                    logger.info(f"Начинаем обновление сообщения с результатами анализа для пользователя {user_id}")
                    
                    # Постепенно обновляем текст
                    chunks = re.split(r'(?<=[.!?])\s+(?=[А-ЯA-Z])', result)
                    current_text = "🤖 AI: "
                    
                    for i, chunk in enumerate(chunks):
                        if chunk.strip():
                            # Добавляем пробел перед частью, если это не первая часть
                            if current_text != "🤖 AI: ":
                                current_text += " " + chunk
                            else:
                                current_text += chunk
                            
                            # Обновляем сообщение с новым содержимым
                            try:
                                await update_message_with_retry(loading_message, current_text)
                                logger.info(f"Обновлено сообщение с анализом изображения часть {i+1}/{len(chunks)} для пользователя {user_id}")
                            except Exception as e:
                                logger.error(f"Ошибка при обновлении сообщения с анализом изображения: {str(e)}")
                                # Если не удалось обновить, отправляем новое сообщение
                                loading_message = await send_message_with_retry(message, current_text)
                            
                            # Уменьшаем задержку для более быстрого отображения
                            await asyncio.sleep(0.2)
                    
                    # В конце добавляем клавиатуру
                    try:
                        await update_message_with_retry(
                            loading_message, 
                            current_text, 
                            reply_markup=get_main_keyboard()
                        )
                        logger.info(f"Добавлена клавиатура к сообщению с анализом изображения для пользователя {user_id}")
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении клавиатуры к сообщению с анализом изображения: {str(e)}")
                        # Если не удалось обновить, отправляем новое сообщение с клавиатурой
                        await send_message_with_retry(
                            message, 
                            current_text, 
                            reply_markup=get_main_keyboard()
                        )
                else:
                    logger.error(f"Не удалось получить сообщение с индикатором загрузки для пользователя {user_id}")
                    # Если не получили сообщение с загрузкой, отправляем новое сообщение
                    await send_message_with_retry(
                        message, 
                        f"🤖 AI: {result}", 
                        reply_markup=get_main_keyboard()
                    )
                
                logger.info(f"Отправлен результат анализа изображения пользователю {user_id}")
            except Exception as e:
                # Останавливаем анимацию при ошибке
                if user_id in self._loading_tasks:
                    await self._stop_loading_animation(user_id)
                
                # Обработка ошибок
                logger.error(f"Ошибка при анализе изображения: {str(e)}")
                await send_message_with_retry(
                    message,
                    f"🤖 AI: Извините, не удалось проанализировать изображение. Ошибка: {str(e)}",
                    reply_markup=get_main_keyboard()
                )
            
            # Очищаем состояние
            if state:
                await state.clear()
            
        except Exception as e:
            # Останавливаем анимацию при ошибке, если она запущена
            if user_id in self._loading_tasks:
                await self._stop_loading_animation(user_id)
                
            # Обработка ошибок
            logger.error(f"Критическая ошибка при обработке изображения: {str(e)}")
            await send_message_with_retry(
                message,
                f"🤖 AI: Извините, произошла ошибка при обработке вашего изображения. Ошибка: {str(e)}",
                reply_markup=get_main_keyboard()
            )
            # Очищаем состояние
            if state:
                await state.clear()
                
    async def handle_document(self, message: types.Message, state: FSMContext = None):
        """
        Обработчик документов/файлов
        
        Args:
            message: Сообщение с документом
            state: Состояние FSM (если используется)
        """
        user_id = message.from_user.id
        loading_message = None
        
        try:
            # Проверяем состояние
            if state:
                current_state = await state.get_state()
                if current_state != BotState.WAITING_FOR_FILE.state:
                    # Если состояние не соответствует ожиданию файла, уведомляем пользователя
                    await send_message_with_retry(
                        message,
                        "🤖 AI: Я обрабатываю ваш файл. Подождите, пожалуйста..."
                    )
            
            # Логируем получение файла
            file_name = message.document.file_name or "Безымянный файл"
            logger.info(f"Получен файл от пользователя {user_id}: {file_name}")
            
            # Отправляем статус "печатает..."
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
            
            # Запускаем анимацию загрузки
            await self._start_loading_animation(message, "🤖 AI: Анализирую файл")
            logger.info(f"Запущена анимация анализа файла для пользователя {user_id}")
            
            try:
                # Получаем файл
                file = await message.bot.get_file(message.document.file_id)
                file_content = await message.bot.download_file(file.file_path)
                
                # Сохраняем содержимое файла
                file_data = file_content.read()
                logger.info(f"Получены данные файла размером {len(file_data)} байт")
                
                # Анализируем файл
                logger.info(f"Отправляем файл на анализ")
                result = await self.gemini_service.analyze_file(file_data, file_name)
                logger.info(f"Получен результат анализа файла для пользователя {user_id}")
                
                # Останавливаем анимацию загрузки и получаем сообщение
                loading_message = await self._stop_loading_animation(user_id)
                
                if loading_message:
                    logger.info(f"Начинаем обновление сообщения с результатами анализа файла для пользователя {user_id}")
                    
                    # Постепенно обновляем текст
                    chunks = re.split(r'(?<=[.!?])\s+(?=[А-ЯA-Z])', result)
                    current_text = "🤖 AI: "
                    
                    for i, chunk in enumerate(chunks):
                        if chunk.strip():
                            # Добавляем пробел перед частью, если это не первая часть
                            if current_text != "🤖 AI: ":
                                current_text += " " + chunk
                            else:
                                current_text += chunk
                            
                            # Обновляем сообщение с новым содержимым
                            try:
                                await update_message_with_retry(loading_message, current_text)
                                logger.info(f"Обновлено сообщение с анализом файла часть {i+1}/{len(chunks)} для пользователя {user_id}")
                            except Exception as e:
                                logger.error(f"Ошибка при обновлении сообщения с анализом файла: {str(e)}")
                                # Если не удалось обновить, отправляем новое сообщение
                                loading_message = await send_message_with_retry(message, current_text)
                            
                            # Уменьшаем задержку для более быстрого отображения
                            await asyncio.sleep(0.2)
                    
                    # В конце добавляем клавиатуру
                    try:
                        await update_message_with_retry(
                            loading_message, 
                            current_text, 
                            reply_markup=get_main_keyboard()
                        )
                        logger.info(f"Добавлена клавиатура к сообщению с анализом файла для пользователя {user_id}")
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении клавиатуры к сообщению с анализом файла: {str(e)}")
                        # Если не удалось обновить, отправляем новое сообщение с клавиатурой
                        await send_message_with_retry(
                            message, 
                            current_text, 
                            reply_markup=get_main_keyboard()
                        )
                else:
                    logger.error(f"Не удалось получить сообщение с индикатором загрузки для пользователя {user_id}")
                    # Если не получили сообщение с загрузкой, отправляем новое сообщение
                    await send_message_with_retry(
                        message, 
                        f"🤖 AI: {result}", 
                        reply_markup=get_main_keyboard()
                    )
                
                logger.info(f"Отправлен результат анализа файла пользователю {user_id}")
            except Exception as e:
                # Останавливаем анимацию при ошибке
                if user_id in self._loading_tasks:
                    await self._stop_loading_animation(user_id)
                
                # Обработка ошибок
                logger.error(f"Ошибка при анализе файла: {str(e)}")
                await send_message_with_retry(
                    message,
                    f"🤖 AI: Извините, не удалось проанализировать файл. Ошибка: {str(e)}",
                    reply_markup=get_main_keyboard()
                )
            
            # Очищаем состояние
            if state:
                await state.clear()
            
        except Exception as e:
            # Останавливаем анимацию при ошибке, если она запущена
            if user_id in self._loading_tasks:
                await self._stop_loading_animation(user_id)
                
            # Обработка ошибок
            logger.error(f"Критическая ошибка при обработке файла: {str(e)}")
            await send_message_with_retry(
                message,
                f"🤖 AI: Извините, произошла ошибка при обработке вашего файла. Ошибка: {str(e)}",
                reply_markup=get_main_keyboard()
            )
            # Очищаем состояние
            if state:
                await state.clear() 