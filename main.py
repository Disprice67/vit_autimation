from src.settings import OUTLOOK_EMAIL, OUTLOOK_PASSWORD, REDIS_HOST, TELEGRAM_TOKEN
from src import AlertManager, AlertMonitor, RedisCache, EmailHandler
from src.telegram_bot import router
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
import asyncio
from src.settings import setup_logger

logger = setup_logger(__name__)


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="auth", description="Авторизоваться в боте")
    ]
    await bot.set_my_commands(commands)


async def start_services():
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    await set_bot_commands(bot)

    email_handler = await EmailHandler.create(bot, OUTLOOK_EMAIL, OUTLOOK_PASSWORD)
    redis_cache = await RedisCache.create(REDIS_HOST)
    alert_manager = AlertManager(email_handler, redis_cache)
    alert_monitor = AlertMonitor(alert_manager, email_handler)

    asyncio.create_task(alert_monitor.start())
    await dp.start_polling(bot, skip_updates=True)


async def main():
    try:
        await start_services()
    except Exception as e:
        logger.error(f"Ошибка при запуске сервиса: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
