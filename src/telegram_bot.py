import sqlite3
from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode
from .settings import setup_logger
from exchangelib import Message as EmailMessage
from html import escape

logger = setup_logger(__name__)

ACCESS_PASSWORD = "CROCViT@"
DB_PATH = "authorized_users.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS authorized_users (
            user_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

init_db()

router = Router()

def is_user_authorized(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM authorized_users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def add_user_to_db(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO authorized_users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

@router.message(Command("start"))
async def start_command(message: Message):
    if is_user_authorized(message.from_user.id):
        await message.reply("Вы уже авторизованы! Вы будете получать алерты.")
    else:
        await message.reply("Привет! Для доступа к боту введите команду /auth и следуйте инструкциям.")

@router.message(Command("auth"))
async def auth_command(message: Message):
    if is_user_authorized(message.from_user.id):
        await message.reply("Вы уже авторизованы! Вы будете получать алерты.")
    else:
        await message.reply("Введите пароль для доступа к боту:")

@router.message(F.text)
async def handle_password(message: Message):
    if is_user_authorized(message.from_user.id):
        await message.reply("Вы уже авторизованы! Вы будете получать алерты.")
        return

    if message.text == ACCESS_PASSWORD:
        add_user_to_db(message.from_user.id)
        await message.reply("Вы успешно авторизованы! Теперь вы будете получать алерты.")
        logger.info(f"Пользователь {message.from_user.id} авторизован.")
    else:
        await message.reply("Неверный пароль. Попробуйте снова.")
        logger.warning(f"Пользователь {message.from_user.id} ввел неверный пароль.")


async def send_alert_to_telegram(bot: Bot, email_message: EmailMessage, subject: str, body: str, alert_type: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM authorized_users")
    # authorized_users = [row[0] for row in cursor.fetchall()]
    conn.close()

    try:
        host = escape(email_message.text_body.split('Host:')[1].split('Groups:')[0].strip())
        time = escape(email_message.text_body.split('Time:')[1].split('Operational data:')[0].strip())
        if alert_type == "Problem":
            group = escape(email_message.text_body.split('Groups:')[1].split('IP-adress:')[0].strip())
            severity = escape(email_message.text_body.split('Severity:')[1].split('Time:')[0].strip())
        if "Resolved" in subject:
            alert_message = (
                f"{escape(subject)}\n"
                f"🖥️ <b>Хост:</b> <u>{host}</u>\n"
                f"⏰ <b>Время:</b> <u>{time}</u>\n\n"
                f"{escape(body.strip())}"
            )
        else:
            alert_message = (
                f"{escape(subject)}\n"
                f"🖥️ <b>Хост:</b> <u>{host}</u>\n"
                f"📂 <b>Группа:</b> <u>{group}</u>\n"
                f"⚠️ <b>Severity:</b> <u>{severity}</u>\n"
                f"⏰ <b>Время:</b> <u>{time}</u>\n\n"
                f"{escape(body.strip())}"
            )
        await bot.send_message(chat_id='-1002555605837', text=alert_message, parse_mode=ParseMode.HTML)
        logger.info(f"Алерт отправлен в группу -1002555605837.")
    except Exception as e:
        logger.error(f"Ошибка при отправке алерта в группу -1002555605837: {e}", exc_info=True)