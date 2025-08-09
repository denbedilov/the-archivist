import os
import asyncio
import logging
from dotenv import load_dotenv

# общая логика
from commands import handle_message, handle_photo_command
from db import init_db

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Не найден токен бота. Проверь .env и переменную BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

# --- попытка запустить на aiogram v3 ---
try:
    import aiogram
    from aiogram import Bot, Dispatcher, F
    from aiogram.types import Message
    from aiogram.router import Router

    bot = Bot(token=TOKEN)  # parse_mode можно добавить при желании
    dp = Dispatcher()
    router = Router()

    @router.message(F.photo & F.caption)
    async def on_photo(message: Message):
        await handle_photo_command(message)

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

# --- если это aiogram v2, используем совместимый путь ---
except ModuleNotFoundError:
    # v2: нет aiogram.router, подключаем другой API
    import aiogram  # noqa: F401
    from aiogram import Bot, Dispatcher, types
    from aiogram.utils import executor

    bot = Bot(token=TOKEN)
    dp = Dispatcher(bot)

    @dp.message_handler(content_types=types.ContentTypes.ANY)
    async def fallback_handler(message: types.Message):
        # Поведение как в твоём раннем варианте:
        if message.photo and message.caption:
            await handle_photo_command(message)
        elif message.text:
            await handle_message(message)

    async def on_startup(_):
        await init_db()

    if __name__ == "__main__":
        executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
