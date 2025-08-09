import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.router import Router
from dotenv import load_dotenv

from db import init_db
from commands import handle_message, handle_photo_command

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Не найден токен бота. Проверь .env и переменную BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)  # при необходимости: parse_mode="HTML"
dp = Dispatcher()
router = Router()

# Фото с подписью (команда "фото роли" в ответ на сообщение)
@router.message(F.photo & F.caption)
async def on_photo(message: Message):
    await handle_photo_command(message)

# Любой текст
@router.message(F.text & ~F.from_user.is_bot)
async def on_text(message: Message):
    await handle_message(message)

async def main():
    await init_db()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
