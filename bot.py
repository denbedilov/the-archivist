import os
import asyncio
from aiogram import Bot, Dispatcher, types
from dotenv import load_dotenv
from db import init_db
from commands import handle_message

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("Не найден токен бота. Проверь .env и переменную BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message()
async def on_message(message: types.Message):
    try:
        await handle_message(message)
    except Exception as e:
        print(f"Ошибка в обработке сообщения: {e}")
        await message.reply("Что-то пошло не так. Куратор всё видит.")

async def main():
    await init_db()  # Инициализация базы при старте
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        # Если нет текущего event loop — создаём новый и запускаем вручную
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
