import pytest
from unittest.mock import Mock, patch
import os
import shutil
from main import (
    # bot,
    escape_markdown,
    check_client,
    send_welcome,
    register,
    account,
    create_card,
)
from logger import log_message_info


@pytest.fixture
def mock_message():
    return Mock(
        chat=Mock(id=12345),
        from_user=Mock(
            id=67890,
            username="test_user",
            first_name="Test",
            last_name="User",
            language_code="en",
        ),
        text="test text",
        content_type="text",
    )


@pytest.fixture
def mock_session():
    session = Mock()
    session.query.return_value.filter.return_value.first.return_value = None
    return session


# ------------------------ Unit-тесты ------------------------


def test_escape_markdown():
    text = "Hello *world*! _Markdown_ test."
    escaped = escape_markdown(text)
    assert escaped == "Hello \\*world\\*\\! \\_Markdown\\_ test\\."


def test_check_client_found(mock_session):
    mock_session.query().filter().first.return_value = Mock()  # Клиент найден
    assert check_client(mock_session, 12345) is True


def test_check_client_not_found(mock_session):
    mock_session.query().filter().first.return_value = None  # Клиент не найден
    assert check_client(mock_session, 12345) is False


@patch("logger.os.makedirs")
@patch("logger.open", create=True)
def test_log_message_info(mock_open, mock_makedirs, mock_message):
    # Удаляем директорию 'logs', если она существует и содержит файлы
    if os.path.exists("logs"):
        shutil.rmtree("logs")  # Рекурсивное удаление директории с содержимым

    # Вызов функции, которая должна создать директорию
    log_message_info(mock_message)

    # Проверка, что директория была создана
    mock_makedirs.assert_called_once_with(
        "logs"
    )  # Убедитесь, что директория 'logs' была создана


# -------------------- Интеграционные тесты --------------------


@patch("main.log_message_info")
@patch("main.bot.send_message")
def test_send_welcome(mock_send_message, mock_log_message, mock_message):
    send_welcome(mock_message)
    mock_log_message.assert_called_once_with(mock_message)
    mock_send_message.assert_called_once_with(
        mock_message.chat.id, "Привет! Я банковский бот."
    )


@patch("main.Session")
@patch("main.bot.send_message")
def test_register_existing_client(mock_send_message, mock_session, mock_message):
    # Мокаем существующего клиента
    mock_client = Mock(first_name="Test")
    mock_session.return_value.query().filter().first.return_value = mock_client
    register(mock_message)

    mock_send_message.assert_called_once_with(
        mock_message.chat.id, "Test, Вы уже зарегистрированы!"
    )


@patch("main.Session")
@patch("main.bot.send_message")
def test_register_new_client(mock_send_message, mock_session, mock_message):
    # Мокаем отсутствие клиента
    mock_session.return_value.query().filter().first.return_value = None
    register(mock_message)

    mock_send_message.assert_called_once_with(
        mock_message.chat.id, "Пожалуйста, введите вашу фамилию (last name):"
    )


@patch("main.Session")
@patch("main.bot.send_message")
def test_account(mock_send_message, mock_session, mock_message):
    # Мокаем клиента и связанные данные
    mock_client = Mock(
        id=1,
        last_name="Doe",
        first_name="John",
        patronymic="",
        email="test@example.com",
    )
    mock_loans = [Mock(amount=10000, interest_rate=5, status="active")]

    # Указываем дату окончания карты
    mock_cards = [
        Mock(
            card_number="1234 5678 9876 5432",
            balance=5000,
            status="active",
            expiration_date=None,
        )
    ]

    mock_session.return_value.query().filter.return_value.one.return_value = mock_client
    mock_session.return_value.query().filter.return_value.all.side_effect = [
        mock_loans,
        mock_cards,
    ]

    account(mock_message)

    # Ожидаемое сообщение
    expected_message = (
        "Ваш аккаунт:\n"
        "ФИО: Doe John \n"
        "Email: test@example.com\n"
        "Кредиты:\n"
        "1. Сумма: 10000, Процентная ставка: 5%, статус: active\n"
        "Карты:\n"
        "1. Номер карты: <code>1234 5678 9876 5432</code>, Дата окончания: None, Баланс: 5000 ₽, Статус: active\n"
    )

    mock_send_message.assert_called_once_with(
        mock_message.chat.id,
        expected_message,
        parse_mode="HTML",
    )


@patch("main.Session")
@patch("main.bot.send_message")
def test_create_card(mock_send_message, mock_session, mock_message):
    # Мокаем клиента и последнюю карту
    mock_client = Mock(id=1)
    mock_last_card = Mock(id=9999, card_number="0000 0000 0000 9999")

    mock_session.return_value.query().filter.return_value.first.return_value = (
        mock_client
    )
    mock_session.return_value.query().order_by().first.return_value = mock_last_card

    create_card(mock_message)

    mock_send_message.assert_called_once_with(
        mock_message.chat.id,
        "Карта с номером <code>0000 0000 0000 9999</code> создана!",
        parse_mode="HTML",
    )
