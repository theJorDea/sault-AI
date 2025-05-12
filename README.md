# Telegram AI Bot

Telegram бот, использующий Google Gemini AI для генерации ответов на сообщения пользователей.

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/theJorDea/sault-AI
cd telegram-ai-bot
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` в корневой директории проекта и добавьте необходимые переменные окружения:
```
TELEGRAM_TOKEN=your_telegram_bot_token
GOOGLE_API_KEY=your_google_api_key
```

## Запуск

```bash
python src/main.py
```

## Структура проекта

```
telegram-ai-bot/
├── src/
│   ├── config/
│   │   └── config.py
│   ├── handlers/
│   │   ├── command_handlers.py
│   │   └── message_handler.py
│   ├── services/
│   │   └── gemini_service.py
│   ├── utils/
│   │   └── message_utils.py
│   └── main.py
├── requirements.txt
└── README.md
```

## Функциональность

- Обработка команд `/start` и `/help`
- Генерация ответов с помощью Google Gemini AI
- Постепенное появление текста для лучшего UX
- Обработка ошибок и повторные попытки при флуд-контроле

## Лицензия

MIT 
