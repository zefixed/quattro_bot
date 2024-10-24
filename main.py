import configparser
import telebot
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models import Base, Client, Card, Transaction, Loan
import re
from collections import namedtuple

# Config
config = configparser.ConfigParser()
config.read("config.ini")
API_TOKEN = config["telegram"]["token"]

# Bot initialization
bot = telebot.TeleBot(API_TOKEN)

# DB connection
alembic = configparser.ConfigParser()
alembic.read("alembic.ini")
DATABASE_URL = alembic["alembic"]["sqlalchemy.url"]
Session = sessionmaker(bind=create_engine(DATABASE_URL))


def escape_markdown(text):
    escape_chars = r"._*[]()~>#+-=|{}!`"
    for char in escape_chars:
        text = text.replace(char, f"\\{char}")
    return text


@bot.message_handler(commands=["start"])
def send_welcome(message):
    session = Session()
    data = session.query(Client).all()
    bot.send_message(message.chat.id, f"Привет! Я ваш Telegram-бот. {data}")


@bot.message_handler(commands=["help"])
def send_help(message):
    help_text = (
        "/start - Запустить бота\n"
        "/help - Получить помощь\n"
        "/register - Зарегистрироваться\n"
        "/account - Посмотреть свой аккаунт\n"
    )
    bot.send_message(message.chat.id, help_text)


@bot.message_handler(commands=["register"])
def register(message):
    session = Session()
    client = (
        session.query(Client).filter(Client.telegram_id == message.from_user.id).first()
    )
    if client:
        bot.send_message(
            message.chat.id, f"{client.first_name}, Вы уже зарегистрированы!"
        )
        return

    bot.send_message(message.chat.id, "Пожалуйста, введите вашу фамилию (last name):")
    bot.register_next_step_handler(message, process_last_name)


def process_last_name(message):
    last_name = message.text
    bot.send_message(message.chat.id, "Введите ваше имя (first name):")
    bot.register_next_step_handler(message, process_first_name, last_name)


def process_first_name(message, last_name):
    first_name = message.text
    bot.send_message(message.chat.id, "Введите ваше отчество (patronymic, если есть):")
    bot.register_next_step_handler(message, process_patronymic, last_name, first_name)


def process_patronymic(message, first_name, last_name):
    patronymic = message.text
    bot.send_message(message.chat.id, "Введите ваш email:")
    bot.register_next_step_handler(
        message, process_email, last_name, first_name, patronymic
    )


def process_email(message, last_name, first_name, patronymic):
    email = message.text
    # Checking email correctness using a regular expression
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_regex, email):
        bot.send_message(
            message.chat.id, "Некорректный email. Пожалуйста, попробуйте еще раз."
        )
        bot.register_next_step_handler(
            message, process_email, first_name, last_name, patronymic
        )
        return

    # Saving data to a database
    session = Session()
    new_client = Client(
        first_name=first_name,
        last_name=last_name,
        patronymic=patronymic,
        email=email,
        telegram_id=message.from_user.id,
    )

    session.add(new_client)
    session.commit()
    session.close()

    bot.send_message(message.chat.id, "Регистрация завершена! Спасибо!")


@bot.message_handler(commands=["account"])
def account(message):
    session = Session()

    client_info = (
        session.query(Client).filter(Client.telegram_id == message.from_user.id).one()
    )
    client_loans = session.query(Loan).filter(Loan.client_id == client_info.id).all()
    client_cards = session.query(Card).filter(Card.client_id == client_info.id).all()

    if not client_info:
        bot.send_message(message.chat.id, "Вы не зарегистрированы!")
        return

    bot.send_message(
        message.chat.id,
        f"Ваш аккаунт:\n"
        f"ФИО: {client_info.last_name} {client_info.first_name} {client_info.patronymic}\n"
        f"Email: {client_info.email}\n"
        f"Кредиты:\n"
        + "".join(
            [
                f"{loan[0] + 1}. Сумма: {loan[1].amount}, Процентная ставка: {loan[1].interest_rate}%, статус: {loan[1].status}\n"
                for loan in enumerate(client_loans)
            ]
        )
        + "Карты:\n"
        + "".join(
            [
                f"{card[0] + 1}. Номер карты: <code>{card[1].card_number}</code>, Дата окончания: {card[1].expiration_date}, Статус: {card[1].status}\n"
                for card in enumerate(client_cards)
            ]
        ),
        parse_mode="HTML",
    )


if __name__ == "__main__":
    bot.polling()
