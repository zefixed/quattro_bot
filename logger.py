import os
from datetime import datetime


def log_message_info(message):
    # Директория для логов
    log_directory = "logs"

    # Создание директории, если она не существует
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    # Получаем дату для названия файла
    log_filename = os.path.join(
        log_directory, f"log_{datetime.now().strftime('%d.%m.%Y')}.log"
    )

    # Информация о пользователе
    user_data = {
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name,
        "language_code": message.from_user.language_code,
    }

    # Информация о чате
    chat_data = {
        "chat_id": message.chat.id,
        "chat_type": message.chat.type,
        "chat_title": message.chat.title if message.chat.title else "Личный чат",
    }

    # Информация о сообщении
    message_text = message.text if message.content_type == "text" else None
    file_id = None

    # Получаем ID файла, если сообщение содержит медиафайл
    if message.content_type == "photo":
        file_id = message.photo[-1].file_id  # Фото с наивысшим разрешением
    elif message.content_type == "document":
        file_id = message.document.file_id
    elif message.content_type == "audio":
        file_id = message.audio.file_id
    elif message.content_type == "video":  # Видео с наивысшим разрешением
        file_id = message.video.file_id
    elif message.content_type == "voice":
        file_id = message.voice.file_id
    elif message.content_type == "sticker":
        file_id = message.sticker.file_id

    # Формируем строку для записи в лог-файл
    log_entry = (
        f"Timestamp: {datetime.utcnow().isoformat()}\n"
        f"User ID: {user_data['user_id']}\n"
        f"Username: {user_data['username']}\n"
        f"First Name: {user_data['first_name']}\n"
        f"Last Name: {user_data['last_name']}\n"
        f"Language Code: {user_data['language_code']}\n"
        f"Chat ID: {chat_data['chat_id']}\n"
        f"Chat Type: {chat_data['chat_type']}\n"
        f"Chat Title: {chat_data['chat_title']}\n"
        f"Message Type: {message.content_type}\n"
        f"Message Text: {message_text if message_text else 'Не текстовое сообщение'}\n"
        f"File ID: {file_id if file_id else 'Нет файла'}\n"
        f"{'-'*40}\n"  # Разделитель между записями
    )

    # Запись лога в файл с кодировкой UTF-8
    with open(log_filename, "a", encoding="utf-8") as file:
        file.write(log_entry)
