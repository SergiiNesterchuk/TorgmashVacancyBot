"""Run the vacancy bot in polling mode (no webhook needed)."""
import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# Import all handlers
from app.main import dp, bot


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    # Delete any existing webhook
    await bot.delete_webhook(drop_pending_updates=True)
    logging.getLogger(__name__).info("Starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
