import os
import asyncio
from aiogram import Bot, Dispatcher, types
from dotenv import load_dotenv
from commands import handle_message

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message()
async def on_message(message: types.Message):
    await handle_message(message, dp)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
