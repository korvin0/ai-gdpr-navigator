"""
AI GDPR Navigator - точка сборки бота.

FSM-бот с 4 фазами:
- Фаза 0: Логический квест GDPR (определение применимости)
- Фаза 1: Профилирование (триггеры)
- Фаза 2: Интерактивный чек-лист мер
- Фаза 3: Финальный отчет
"""
import logging
import os

from aiogram import Bot, Dispatcher

from .handlers import setup_routers

logging.basicConfig(level=logging.INFO)


def create_bot() -> tuple[Bot, Dispatcher]:
    """Создать бота и диспетчер."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Укажите TELEGRAM_BOT_TOKEN в .env")

    bot = Bot(token=token)
    dp = Dispatcher()
    setup_routers(dp)
    return bot, dp


async def run_polling() -> None:
    """Запустить бота в режиме polling."""
    bot, dp = create_bot()
    await dp.start_polling(bot)
