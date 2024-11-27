import configparser
import telebot
from telebot import types
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Client, Card, Transaction, Loan
import re
from datetime import datetime, timedelta
from logger import log_message_info

# Config
config = configparser.ConfigParser()
config.read("config.ini")
API_TOKEN = config["telegram"]["token"]

# Bot initialization
bot = telebot.TeleBot(API_TOKEN)

# DB connection
try:
    alembic = configparser.ConfigParser()
    alembic.read("alembic.ini")
    DATABASE_URL = alembic["alembic"]["sqlalchemy.url"]
    Session = sessionmaker(bind=create_engine(DATABASE_URL))
except Exception as e:
    print("db error", e)
    exit()

# Определение команд для меню
commands = [
    types.BotCommand("start", "Начать работу с ботом"),
    types.BotCommand("help", "Помощь"),
    types.BotCommand("register", "Регистрация"),
    types.BotCommand("account", "Управление аккаунтом"),
    types.BotCommand("create_card", "Создание карты"),
    types.BotCommand("delete_card", "Удаление карты"),
    types.BotCommand("loan_pay", "Погасить кредит"),
    types.BotCommand("top_up", "Пополнить карту"),
    types.BotCommand("transfer", "Перевод с карты на карту"),
]

# Установка команд в меню бота
bot.set_my_commands(commands)


def escape_markdown(text):
    # escape_chars = r"._*[]()~>#+-=|{}!`"
    escape_chars = r"._*[]()~>#+-=|{}`"
    for char in escape_chars:
        text = text.replace(char, f"\\{char}")
    return text


def check_client(session, telegram_id) -> bool:
    client = session.query(Client).filter(Client.telegram_id == telegram_id).first()
    if not client:
        return False
    return True


@bot.message_handler(commands=["start"])
def send_welcome(message):
    log_message_info(message)
    bot.send_message(message.chat.id, "Привет! Я банковский бот.")


@bot.message_handler(commands=["help"])
def send_help(message):
    log_message_info(message)
    help_text = (
        "/start - Запустить бота\n"
        "/help - Получить помощь\n"
        "/register - Зарегистрироваться\n"
        "/account - Посмотреть свой аккаунт\n"
        "/create_card - Создать карту\n"
        "/loan_pay - Погасить кредит\n"
        "/top_up - Пополнить карту\n"
        "/transfer - Перевод с карты на карту"
    )
    bot.send_message(message.chat.id, help_text)


@bot.message_handler(commands=["register"])
def register(message):
    log_message_info(message)
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
    log_message_info(message)
    last_name = message.text
    bot.send_message(message.chat.id, "Введите ваше имя (first name):")
    bot.register_next_step_handler(message, process_first_name, last_name)


def process_first_name(message, last_name):
    log_message_info(message)
    first_name = message.text
    bot.send_message(message.chat.id, "Введите ваше отчество (patronymic, если есть):")
    bot.register_next_step_handler(message, process_patronymic, last_name, first_name)


def process_patronymic(message, first_name, last_name):
    log_message_info(message)
    patronymic = message.text
    bot.send_message(message.chat.id, "Введите ваш email:")
    bot.register_next_step_handler(
        message, process_email, last_name, first_name, patronymic
    )


def process_email(message, last_name, first_name, patronymic):
    log_message_info(message)
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
    log_message_info(message)
    session = Session()
    if not check_client(session, message.from_user.id):
        bot.send_message(message.chat.id, "Вы не зарегистрированы!")
        return

    client_info = (
        session.query(Client).filter(Client.telegram_id == message.from_user.id).one()
    )
    client_loans = (
        session.query(Loan)
        .filter(Loan.client_id == client_info.id, Loan.status == "active")
        .all()
    )
    client_cards = session.query(Card).filter(Card.client_id == client_info.id).all()

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
                f"{card[0] + 1}. Номер карты: <code>{card[1].card_number}</code>, Дата окончания: {card[1].expiration_date}, Баланс: {card[1].balance} ₽, Статус: {card[1].status}\n"
                for card in enumerate(client_cards)
            ]
        ),
        parse_mode="HTML",
    )


@bot.message_handler(commands=["create_card"])
def create_card(message):
    log_message_info(message)
    session = Session()
    client = (
        session.query(Client).filter(Client.telegram_id == message.from_user.id).first()
    )
    if not check_client(session, message.from_user.id):
        bot.send_message(message.chat.id, "Вы не зарегистрированы!")
        return

    last_card = session.query(Card).order_by(Card.id.desc()).first()
    if not last_card:
        last_card = Card(card_number="0000000000000000")

    new_card = Card(
        client_id=client.id,
        card_number=" ".join(
            [
                ("0000000000000000" + str(last_card.id))[-16:][i * 4 : i * 4 + 4]
                for i in range(4)
            ]
        ),
        expiration_date=datetime.now() + timedelta(days=365),
    )

    session.add(new_card)
    session.commit()

    bot.send_message(
        message.chat.id,
        f"Карта с номером <code>{new_card.card_number}</code> создана!",
        parse_mode="HTML",
    )
    session.close()


@bot.message_handler(commands=["delete_card"])
def delete_card(message):
    log_message_info(message)
    session = Session()
    client = (
        session.query(Client).filter(Client.telegram_id == message.from_user.id).first()
    )
    if not check_client(session, message.from_user.id):
        bot.send_message(message.chat.id, "Вы не зарегистрированы!")
        return

    cards = session.query(Card).filter(Card.client_id == client.id).all()

    if not cards:
        bot.send_message(message.chat.id, "У вас нет карт!")
        return

    markup = types.InlineKeyboardMarkup()
    for card in cards:
        markup.add(
            types.InlineKeyboardButton(
                card.card_number, callback_data="delete_card_" + str(card.id)
            )
        )

    bot.send_message(
        message.chat.id, "Выберите карту для удаления", reply_markup=markup
    )
    session.close()


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_card_"))
def callback_query_delete_card(call):
    log_message_info(call.message)
    card_id = int(call.data.split("_")[-1])
    session = Session()
    card = session.query(Card).filter(Card.id == card_id).first()
    if card:
        session.delete(card)
        session.commit()
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Карта успешно удалена!",
        )
    session.close()


@bot.message_handler(commands=["loan_pay"])
def loan_pay(message):
    log_message_info(message)
    session = Session()
    client = (
        session.query(Client).filter(Client.telegram_id == message.from_user.id).first()
    )
    if not check_client(session, message.from_user.id):
        bot.send_message(message.chat.id, "Вы не зарегистрированы!")
        return

    loans = (
        session.query(Loan)
        .filter(Loan.client_id == client.id, Loan.status == "active")
        .all()
    )

    if not loans:
        bot.send_message(message.chat.id, "У вас нет кредитов!")
        return

    markup = types.InlineKeyboardMarkup()
    for loan in loans:
        markup.add(
            types.InlineKeyboardButton(
                f"{loan.amount} ₽, {loan.interest_rate}%, до {loan.due_date}",
                callback_data="loan_pay_" + str(loan.id),
            )
        )

    bot.send_message(
        message.chat.id, "Выберите кредит для погашения кредита", reply_markup=markup
    )
    session.close()


@bot.callback_query_handler(func=lambda call: call.data.startswith("loan_pay_"))
def callback_query_loan_pay(call):
    log_message_info(call.message)
    loan_id = int(call.data.split("_")[-1])
    session = Session()
    loan = session.query(Loan).filter(Loan.id == loan_id).first()
    cards = session.query(Card).filter(Card.client_id == loan.client_id).all()

    markup = types.InlineKeyboardMarkup()
    for card in cards:
        if card.balance >= loan.amount:
            markup.add(
                types.InlineKeyboardButton(
                    f"{card.card_number}, {card.balance} ₽",
                    callback_data=f"loan_card_{loan.id}_{card.id}",
                )
            )
    if not markup.keyboard:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="У вас нет карт с достаточным балансом для погашения кредита!",
        )
        return

    bot.delete_message(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )
    bot.send_message(
        call.message.chat.id,
        f"Выберите карту для погашения кредита {loan.amount} ₽, {loan.interest_rate}%, до {loan.due_date}",
        reply_markup=markup,
    )
    session.close()


@bot.callback_query_handler(func=lambda call: call.data.startswith("loan_card_"))
def callback_query_loan_pay_card(call):
    log_message_info(call.message)
    loan_id = int(call.data.split("_")[-2])
    card_id = int(call.data.split("_")[-1])
    session = Session()
    loan = session.query(Loan).filter(Loan.id == loan_id).first()
    card = session.query(Card).filter(Card.id == card_id).first()
    transaction = Transaction(
        client_id=card.client_id,
        amount=loan.amount,
        transaction_type="loan_pay",
        recipient_id=card.client_id,
    )
    if card:
        if card.balance >= loan.amount:
            card.balance -= loan.amount
            loan.amount = 0
            loan.status = "paid"
            loan.due_date = datetime.now()
            session.commit()
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="Кредит успешно погашен!",
            )
    session.add(transaction)
    session.commit()
    session.close()


@bot.message_handler(commands=["top_up"])
def top_up(message):
    log_message_info(message)
    session = Session()
    client = (
        session.query(Client).filter(Client.telegram_id == message.from_user.id).first()
    )
    if not check_client(session, message.from_user.id):
        bot.send_message(message.chat.id, "Вы не зарегистрированы!")
        return

    markup = types.InlineKeyboardMarkup()
    cards = session.query(Card).filter(Card.client_id == client.id).all()
    for card in cards:
        markup.add(
            types.InlineKeyboardButton(
                f"{card.card_number}, {card.balance} ₽",
                callback_data="top_up_" + str(card.id),
            )
        )
    if not markup.keyboard:
        bot.send_message(message.chat.id, "У вас нет карт!")
        return

    bot.send_message(
        message.chat.id, "Выберите карту для пополнения баланса", reply_markup=markup
    )
    session.close()


@bot.callback_query_handler(func=lambda call: call.data.startswith("top_up_"))
def callback_query_top_up(call):
    log_message_info(call.message)
    card_id = int(call.data.split("_")[-1])
    session = Session()
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Введите сумму пополнения баланса:",
    )
    bot.register_next_step_handler(
        call.message,
        finish_top_up,
        card_id=card_id,
        session=session,
    )


def finish_top_up(message, card_id, session):
    log_message_info(message)
    try:
        amount = int(message.text)
    except ValueError:
        bot.send_message(
            message.chat.id,
            "Сумма пополнения должна быть целым числом!",
        )
        bot.register_next_step_handler(
            message, finish_top_up, card_id=card_id, session=session
        )
        return

    card = session.query(Card).filter(Card.id == card_id).first()
    if card:
        card.balance += amount
        session.commit()
        bot.send_message(
            message.chat.id,
            f"Баланс карты <code>{card.card_number}</code> пополнен на {amount} ₽, текущий баланс: {card.balance} ₽",
            parse_mode="HTML",
        )

    transaction = Transaction(
        client_id=card.client_id,
        amount=amount,
        transaction_type="top_up",
        recipient_id=card.client_id,
    )
    session.add(transaction)
    session.commit()
    session.close()


@bot.message_handler(commands=["transfer"])
def transfer(message):
    log_message_info(message)
    session = Session()
    client = (
        session.query(Client).filter(Client.telegram_id == message.from_user.id).first()
    )

    if not check_client(session, message.from_user.id):
        bot.send_message(message.chat.id, "Вы не зарегистрированы!")
        return

    cards_from = session.query(Card).filter(Card.client_id == client.id).all()
    markup = types.InlineKeyboardMarkup()
    for card in cards_from:
        markup.add(
            types.InlineKeyboardButton(
                f"{card.card_number}, {card.balance} ₽",
                callback_data="transfer_" + str(card.id),
            )
        )
    if not markup.keyboard:
        bot.send_message(message.chat.id, "У вас нет карт!")
        return

    bot.send_message(
        message.chat.id,
        "Выберите карту отправителя:",
        reply_markup=markup,
    )
    session.close()
    # bot.register_next_step_handler(message, process_card_from)


@bot.callback_query_handler(func=lambda call: call.data.startswith("transfer_"))
def process_card_from(call):
    log_message_info(call.message)
    session = Session()
    card_from = (
        session.query(Card).filter(Card.id == int(call.data.split("_")[-1])).first()
    )
    if not card_from:
        bot.send_message(call.message.chat.id, "Карта не найдена!")
        return

    bot.send_message(call.message.chat.id, "Введите номер карты получателя:")
    bot.register_next_step_handler(
        call.message, process_transfer, session=session, card_from=card_from
    )


def process_transfer(message, session, card_from):
    log_message_info(message)
    card_number = message.text

    card_to = session.query(Card).filter(Card.card_number == card_number).first()
    if not card_to:
        bot.send_message(message.chat.id, "Карта не найдена!")
        return

    bot.send_message(message.chat.id, "Введите сумму перевода:")
    bot.register_next_step_handler(
        message, finish_transfer, card_to=card_to, session=session, card_from=card_from
    )


def finish_transfer(message, card_to, session, card_from):
    log_message_info(message)
    try:
        amount = float(message.text)
        if amount <= 0:
            bot.send_message(
                message.chat.id,
                "Сумма перевода должна быть больше нуля!",
            )
            bot.register_next_step_handler(
                message,
                finish_transfer,
                card_to=card_to,
                session=session,
                card_from=card_from,
            )
            return
        if amount > card_from.balance:
            bot.send_message(
                message.chat.id,
                "Недостаточно средств!",
            )
            bot.register_next_step_handler(
                message,
                finish_transfer,
                card_to=card_to,
                session=session,
                card_from=card_from,
            )
            return
    except ValueError:
        bot.send_message(
            message.chat.id,
            "Сумма перевода должна быть целым числом!",
        )
        bot.register_next_step_handler(
            message, finish_transfer, card_to, session, card_from
        )

    card_from.balance -= amount
    card_to.balance += amount
    transaction = Transaction(
        client_id=card_from.client_id,
        amount=amount,
        transaction_type="transfer",
        recipient_id=card_to.client_id,
    )
    session.add(transaction)
    session.commit()
    bot.send_message(
        message.chat.id,
        f"Перевод с карты <code>{card_from.card_number}</code> на карту <code>{card_to.card_number}</code> выполнен, текущий баланс: {card_from.balance} ₽",
        parse_mode="HTML",
    )


@bot.message_handler(
    content_types=[
        "text",
        "photo",
        "document",
        "audio",
        "voice",
        "video",
        "video_note",
        "sticker",
        "location",
        "contact",
        "venue",
        "animation",
        "poll",
        "dice",
    ]
)
def handle_unmatched_message(message):
    if message.content_type == "text":
        bot.send_message(message.chat.id, "Я вас не понимаю, попробуйте ещё раз.")
    else:
        bot.send_message(
            message.chat.id,
            "Я пока не могу обработать этот тип сообщения, попробуйте ещё раз.",
        )
    log_message_info(message)


if __name__ == "__main__":
    bot.polling()
