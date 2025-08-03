import re
import os
import sys
import aiosqlite
import asyncio
from aiogram import types
from db import (
    get_balance, change_balance, set_role, get_role,
    grant_key, revoke_key, has_key, get_last_history,
    get_top_users, get_all_roles, reset_user_balance, 
    reset_all_balances

)

KURATOR_ID = 164059195
DB_PATH = "/data/bot_data.sqlite"

async def handle_message(message: types.Message):
    if not message.text:
        return
    text = message.text.lower().strip()
    author_id = message.from_user.id

    # Игнорируем сообщения от самого бота
    if author_id == (await message.bot.get_me()).id:
        return

    # 🔓 Команды, доступные всем
    if text == "мой карман":
        bal = await get_balance(author_id)
        await message.reply(f"У Вас в кармане 🪙{bal} нуаров.")
        return

    if text == "моя роль":
        role_info = await get_role(author_id)
        if role_info:
            role = role_info.get("role", "Без названия")
            desc = role_info.get("description", "")
            text_response = f"🎭 *{role}*\n\n_{desc}_"
            await message.reply(text_response, parse_mode="Markdown")
        else:
            await message.reply("Я вас не узнаю.")
        return

    if text == "роль" and message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        role_info = await get_role(target_id)
        if role_info:
            role = role_info.get("role", "Без названия")
            desc = role_info.get("description", "")
            text_response = f"🎭 *{role}*\n\n_{desc}_"
            await message.reply(text_response, parse_mode="Markdown")
        else:
            await message.reply("Я не знаю кто это.")
        return

    if text == "список команд":
        await handle_list(message)
        return

    if text == "клуб":
        await message.answer(
            "🎩 <b>Клуб Le Cadeau Noir</b>\n"
            "<i>В переводе с французского — «Чёрный подарок»</i>\n\n"
            "🌑 <b>Концепция:</b>\n"
            "Закрытый элегантный Telegram-клуб для ценителей стиля, таинственности и криптоподарков.\n"
            "Участники клуба обмениваются виртуальными (и иногда реальными) подарками.\n"
            "Каждый подарок — это не просто жест, а символ уважения, флирта или признательности.\n\n"
            "🎓 <b>Этикет:</b>\n"
            "Всё происходит в атмосфере вежливости, загадочности и утончённого шика.\n"
            "Прямые предложения не приветствуются — всё через намёки, ролевую игру и символы.",
            parse_mode="HTML"
        )
        return

    if text == "рейтинг клуба":
        await handle_rating(message)
        return

    # 🔐 Проверяем ключ
    user_has_key = (author_id == KURATOR_ID) or await has_key(author_id)

    # 🔑 Команды с ключом
    if user_has_key:
        if text.startswith("вручить "):
            await handle_vruchit(message)
            return
        if text.startswith("взыскать "):
            await handle_otnyat(message, text, author_id)
            return
        if text == "члены клуба":
            await handle_club_members(message)
            return

    # 👑 Команды только куратора
    if author_id == KURATOR_ID:
        if text.startswith("назначить ") and message.reply_to_message:
            await handle_naznachit(message)
            return
        if text == "снять роль" and message.reply_to_message:
            await handle_snyat_rol(message)
            return
        if text == "ключ от сейфа" and message.reply_to_message:
            await handle_kluch(message)
            return
        if text == "снять ключ" and message.reply_to_message:
            await handle_snyat_kluch(message)
            return
        if text == "обнулить клуб":
            await asyncio.sleep(1)
            await handle_clear_db(message)
            return
        if text.startswith("обнулить балансы"):
            await handle_obnulit_balansy(message)
            return
        if text.startswith("обнулить баланс"):
            await handle_obnulit_balans(message)
            return

    return


async def handle_vruchit(message: types.Message):
    author_id = message.from_user.id
    text = message.text.strip()

    # Вручение по ответу на сообщение
    if message.reply_to_message:
        pattern = r"вручить\s+(-?\d+)"  # Разрешаем и отрицательные числа для проверки
        m = re.match(pattern, text, re.IGNORECASE)
        if not m:
            await message.reply("Обращение не по этикету Клуба. Пример: 'вручить 5'")
            return

        amount = int(m.group(1))
        if amount <= 0:
            await message.reply("Я не могу выдать минус.")
            return
        recipient = message.reply_to_message.from_user
        recipient_name = recipient.username or recipient.full_name or "пользователю"
        await change_balance(recipient.id, amount, "без причины", author_id)
        await message.reply(f"Я выдал {amount} нуаров @{recipient_name}")
        return

async def handle_otnyat(message: types.Message, text: str, author_id: int):

    # Отнять по ответу на сообщение
    if message.reply_to_message:
        pattern = r"взыскать\s+(-?\d+)"
        m = re.match(pattern, text, re.IGNORECASE)
        if not m:
            await message.reply("Обращение не по этикету Клуба. Пример: 'отнять 3'")
            return

        amount = int(m.group(1))
        if amount <= 0:
            await message.reply("Я не могу отнять минус.")
            return

        recipient_id = message.reply_to_message.from_user.id
        recipient_name = message.reply_to_message.from_user.full_name

        current_balance = await get_balance(recipient_id)
        if amount > current_balance:
            await message.reply(f"У {recipient_name} нет такого количества нуаров. Баланс: {current_balance}")
            return

        recipient = message.reply_to_message.from_user
        await change_balance(recipient.id, -amount, "без причины", author_id)
        await message.reply(f"Я взыскал {amount} нуаров у @{recipient.username or recipient.full_name}")
        return

async def handle_naznachit(message: types.Message):
    author_id = message.from_user.id
    text = message.text.strip()
    # Формат: назначить "название роли" описание роли
    pattern = r'назначить\s+"([^"]+)"\s+(.+)'
    m = re.match(pattern, text, re.IGNORECASE)
    if not m:
        await message.reply('Я не совсем понял')
        return
    role_name, role_desc = m.groups()

    if not message.reply_to_message:
        await message.reply("Кому мне выдать роль, Куратор?")
        return

    user_id = message.reply_to_message.from_user.id
    await set_role(user_id, role_name, role_desc)
    await message.reply(f"Назначена роль '{role_name}' пользователю @{message.reply_to_message.from_user.username or message.reply_to_message.from_user.full_name}")
    return

async def handle_snyat_rol(message: types.Message):
    author_id = message.from_user.id
    if not message.reply_to_message:
        await message.reply("Но кого мне лишить роли, Куратор?")
        return
    user_id = message.reply_to_message.from_user.id
    await set_role(user_id, None, None)
    await message.reply(f"Роль снята у @{message.reply_to_message.from_user.username or message.reply_to_message.from_user.full_name}")
    return

async def handle_kluch(message: types.Message):
    author_id = message.from_user.id
    if not message.reply_to_message:
        await message.reply("Кому мне выдать ключ, Куратор?")
        return
    user_id = message.reply_to_message.from_user.id
    await grant_key(user_id)
    await message.reply(f"Ключ от сейфа выдан @{message.reply_to_message.from_user.username or message.reply_to_message.from_user.full_name}")
    return

async def handle_snyat_kluch(message: types.Message):
    author_id = message.from_user.id
    if not message.reply_to_message:
        await message.reply("У кого мне отобрать ключ, Куратор?")
        return
    user_id = message.reply_to_message.from_user.id
    await revoke_key(user_id)
    await message.reply(f"Ключ от сейфа отнят у @{message.reply_to_message.from_user.username or message.reply_to_message.from_user.full_name}")

async def handle_list(message: types.Message):
    try:
        with open("Список команд.txt", "r", encoding="utf-8") as file:
            help_text = file.read()
        await message.reply(help_text)
    except Exception as e:
        print(f"Ошибка при чтении help.txt: {e}")
        await message.reply("Не удалось загрузить список команд.")

async def find_member_by_username(message: types.Message, username: str):
    chat = message.chat
    admins = await message.bot.get_chat_administrators(chat.id)
    for admin in admins:
        if admin.user.username and admin.user.username.lower() == username.lower():
            return admin
    return None

async def handle_rating(message: types.Message):
    rows = await get_top_users(limit=10)
    if not rows:
        await message.reply("Ни у кого в клубе нет нуаров.")
        return

    text = "🏆 Богатейшие члены клуба Le Cadeau Noir:\n\n"
    for i, (user_id, balance) in enumerate(rows, start=1):
        try:
            user = await message.bot.get_chat(user_id)
            name = user.first_name
        except Exception:
            name = "Участник"

        text += f"{i}. <a href='tg://user?id={user_id}'>{name}</a> — {balance} нуаров\n"

    await message.reply(text, parse_mode="HTML")

async def handle_club_members(message: types.Message):
    rows = await get_all_roles()
    if not rows:
        await message.reply("Пока что в клубе пусто.")
        return

    lines = []
    for user_id, role in rows:
        # Получаем username, если он есть
        try:
            user = await message.bot.get_chat_member(message.chat.id, user_id)
            if user.user.username:
                mention = f"@{user.user.username}"
            else:
                mention = f"<a href='tg://user?id={user_id}'>Участник</a>"
        except:
            mention = f"<a href='tg://user?id={user_id}'>Участник</a>"

        lines.append(f"{mention} — <b>{role}</b>")

    text = "🎭 <b>Члены клуба:</b>\n\n" + "\n".join(lines)
    await message.reply(text, parse_mode="HTML")


async def handle_clear_db(message):
    # Только куратор (по ID) может обнулить клуб
    if message.from_user.id != 164059195:
        await message.reply("Только куратор может обнулить клуб.")
        return

    # Удаляем файл базы данных
    try:
        await message.reply("Клуб обнуляется...")

        # Закрываем соединения и удаляем файл
        if os.path.exists("/data/bot_data.sqlite"):
            os.remove("/data/bot_data.sqlite")

        await message.answer("Код Армагедон. Клуб обнулен. Теперь только я и вы, Куратор.")

        # Перезапускаем процесс
        os.execv(sys.executable, [sys.executable] + sys.argv)
        return

    except Exception as e:
        await message.reply(f"Ошибка при обнулении: {e}")

# Обнулить баланс конкретного участника
async def handle_obnulit_balans(message: types.Message):
    if not message.reply_to_message:
        await message.reply("Чтобы обнулить баланс, ответь на сообщение участника.")
        return
    user_id = message.reply_to_message.from_user.id
    await reset_user_balance(user_id)
    await message.reply("Баланс участника обнулён.")

# Обнулить балансы всех участников
async def handle_obnulit_balansy(message: types.Message):
    await reset_all_balances()
    await message.reply("Все балансы обнулены.")