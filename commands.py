import re
from aiogram import types
from db import (
    get_balance, change_balance, set_role, get_role,
    grant_key, revoke_key, has_key, get_last_history
)

KURATOR_ID = 164059195

async def handle_message(message: types.Message):
    if not message.text:
        return
    text = message.text.lower().strip()
    author_id = message.from_user.id

    # Игнорируем сообщения от самого бота
    if author_id == (await message.bot.get_me()).id:
        return

    # Проверяем, есть ли у автора ключ (полномочия)
    user_has_key = (author_id == KURATOR_ID) or await has_key(author_id)

    # Команды, доступные только куратору и обладателям ключа
    if user_has_key:
        if text.startswith("вручить "):
            await handle_vruchit(message)
            return
        if text.startswith("взыскать "):
            await handle_otnyat(message, text, author_id)
            return

    # Только куратор — команды управления ролями и ключами
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

    # Команды, доступные всем
    if text == "мой карман":
        bal = await get_balance(author_id)
        await message.reply(f"У Вас в кармане {bal} нуаров.")
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
    if text == "список команд":
        await handle_list(message)
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
        await change_balance(recipient.id, amount, "без причины", author_id)
        await message.reply(f"Я выдал {amount} нуаров @{recipient.username or recipient.full_name}")
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

async def handle_snyat_rol(message: types.Message):
    author_id = message.from_user.id
    if not message.reply_to_message:
        await message.reply("Но кого мне лишить роли, Куратор?")
        return
    user_id = message.reply_to_message.from_user.id
    await set_role(user_id, None, None)
    await message.reply(f"Роль снята у @{message.reply_to_message.from_user.username or message.reply_to_message.from_user.full_name}")

async def handle_kluch(message: types.Message):
    author_id = message.from_user.id
    if not message.reply_to_message:
        await message.reply("Кому мне выдать ключ, Куратор?")
        return
    user_id = message.reply_to_message.from_user.id
    await grant_key(user_id)
    await message.reply(f"Ключ от сейфа выдан @{message.reply_to_message.from_user.username or message.reply_to_message.from_user.full_name}")

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
