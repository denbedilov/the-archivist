import re
from aiogram import types
from db import (
    get_balance, change_balance, set_role, get_role,
    grant_key, revoke_key, has_key, get_last_history
)

KURATOR_ID = 164059195

async def handle_message(message: types.Message):
    text = message.text.lower().strip()
    author_id = message.from_user.id

    # Игнорируем сообщения от самого бота
    if author_id == (await message.bot.get_me()).id:
        return

    # Проверяем, есть ли у автора ключ (полномочия)
    has_key = (author_id == KURATOR_ID) or await has_key(author_id)

    # Команды, доступные только куратору и обладателям ключа
    if has_key:
        if text.startswith("вручить "):
            await handle_vruchit(message)
            return
        if text.startswith("отнять "):
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
    if text == "карман":
        bal = await get_balance(author_id)
        await message.reply(f"У тебя в кармане {bal} нуаров.")
        return
    if text == "моя роль":
        await handle_moya_rol(message)
        return

    # Неизвестная команда - не отвечает или можно добавить:
    # await message.reply("Неизвестная команда.")


async def handle_vruchit(message: types.Message):
    author_id = message.from_user.id
    if author_id != KURATOR_ID and not await has_key(author_id):
        await message.reply("У вас нет ключа от сейфа.")
        return

    text = message.text.strip()

    # Вручение по ответу на сообщение
    if message.reply_to_message:
        pattern = r"вручить\s+(\d+)"
        m = re.match(pattern, text, re.IGNORECASE)
        if not m:
            await message.reply("Неверный формат. Пример: 'вручить 5'")
            return
        amount = int(m.group(1))
        if amount <= 0:
            await message.reply("Количество должно быть положительным.")
            return
        recipient = message.reply_to_message.from_user
        await change_balance(recipient.id, amount, "без причины", author_id)
        await message.reply(f"Я выдал {amount} нуаров @{recipient.username or recipient.full_name}")
        return

    # Вручение по юзернейму
    pattern = r"вручить\s+@(\w+)\s+(\d+)"
    m = re.match(pattern, text, re.IGNORECASE)
    if not m:
        await message.reply("Неверный формат. Пример: 'вручить @username 5'")
        return
    username, amount_str = m.groups()
    amount = int(amount_str)
    if amount <= 0:
        await message.reply("Количество должно быть положительным.")
        return
    member = await find_member_by_username(message, username)
    if not member:
        await message.reply(f"Я не могу найти @{username}.")
        return
    await change_balance(member.user.id, amount, "без причины", author_id)
    await message.reply(f"Я выдал @{username} {amount} нуаров")


async def handle_otnyat(message: types.Message, text: str, author_id: int):
    if author_id != KURATOR_ID and not await has_key(author_id):
        await message.reply("У вас нет ключа от сейфа.")
        return

    # Отнять по ответу на сообщение
    if message.reply_to_message:
        pattern = r"отнять\s+(\d+)"
        m = re.match(pattern, text, re.IGNORECASE)
        if not m:
            await message.reply("Неверный формат. Пример: 'отнять 3'")
            return
        amount = int(m.group(1))
        if amount <= 0:
            await message.reply("Количество должно быть положительным.")
            return
        recipient = message.reply_to_message.from_user
        await change_balance(recipient.id, -amount, "без причины", author_id)
        await message.reply(f"Я взыскал {amount} нуаров у @{recipient.username or recipient.full_name}")
        return

    # Отнять по юзернейму
    pattern = r"отнять\s+@(\w+)\s+(\d+)"
    m = re.match(pattern, text)
    if not m:
        await message.reply("Неверный формат команды отнять.")
        return
    username, amount_str = m.groups()
    amount = int(amount_str)
    if amount <= 0:
        await message.reply("Количество должно быть положительным.")
        return
    member = await find_member_by_username(message, username)
    if not member:
        await message.reply(f"Я не могу найти @{username}.")
        return
    await change_balance(member.user.id, -amount, "без причины", author_id)
    await message.reply(f"Я взыскал у @{username} {amount} нуаров.")


async def handle_naznachit(message: types.Message):
    author_id = message.from_user.id
    if author_id != KURATOR_ID:
        await message.reply("Только куратор может назначать роли.")
        return

    text = message.text.strip()
    # Формат: назначить "название роли" описание роли
    pattern = r'назначить\s+"([^"]+)"\s+(.+)'
    m = re.match(pattern, text, re.IGNORECASE)
    if not m:
        await message.reply('Неверный формат. Пример: назначить "Роль" описание роли')
        return
    role_name, role_desc = m.groups()

    if not message.reply_to_message:
        await message.reply("Команда должна быть в ответ на сообщение пользователя, которому назначаем роль.")
        return

    user_id = message.reply_to_message.from_user.id
    await set_role(user_id, role_name, role_desc)
    await message.reply(f"Назначена роль '{role_name}' пользователю @{message.reply_to_message.from_user.username or message.reply_to_message.from_user.full_name}")


async def handle_snyat_rol(message: types.Message):
    author_id = message.from_user.id
    if author_id != KURATOR_ID:
        await message.reply("Только куратор может снимать роли.")
        return
    if not message.reply_to_message:
        await message.reply("Команда должна быть в ответ на сообщение пользователя.")
        return
    user_id = message.reply_to_message.from_user.id
    await set_role(user_id, None, None)
    await message.reply(f"Роль снята у @{message.reply_to_message.from_user.username or message.reply_to_message.from_user.full_name}")


async def handle_kluch(message: types.Message):
    author_id = message.from_user.id
    if author_id != KURATOR_ID:
        await message.reply("Только куратор может выдавать ключи.")
        return
    if not message.reply_to_message:
        await message.reply("Команда должна быть в ответ на сообщение пользователя.")
        return
    user_id = message.reply_to_message.from_user.id
    await grant_key(user_id)
    await message.reply(f"Ключ от сейфа выдан @{message.reply_to_message.from_user.username or message.reply_to_message.from_user.full_name}")


async def handle_snyat_kluch(message: types.Message):
    author_id = message.from_user.id
    if author_id != KURATOR_ID:
        await message.reply("Только куратор может снимать ключи.")
        return
    if not message.reply_to_message:
        await message.reply("Команда должна быть в ответ на сообщение пользователя.")
        return
    user_id = message.reply_to_message.from_user.id
    await revoke_key(user_id)
    await message.reply(f"Ключ от сейфа снят у @{message.reply_to_message.from_user.username or message.reply_to_message.from_user.full_name}")


async def handle_moya_rol(message: types.Message):
    user_id = message.from_user.id
    role_info = await get_role(user_id)
    if not role_info:
        await message.reply("У тебя пока нет роли.")
    else:
        await message.reply(f"Твоя роль: {role_info['role']}\nОписание: {role_info['description']}")


async def find_member_by_username(message: types.Message, username: str):
    chat = message.chat
    admins = await message.bot.get_chat_administrators(chat.id)
    for admin in admins:
        if admin.user.username and admin.user.username.lower() == username.lower():
            return admin
    return None
