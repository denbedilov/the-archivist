import re
from aiogram import types

# Простая база данных в памяти (для MVP)
users = {}
history = []
roles = {}  # user_id: {"title": str, "description": str}
permissions = set()  # user_ids, которым выдан "ключ от сейфа"


def get_user_balance(user_id):
    return users.get(user_id, 0)

def change_balance(user_id, amount, reason, author_id):
    old = users.get(user_id, 0)
    users[user_id] = old + amount
    history.append({
        "user_id": user_id,
        "amount": amount,
        "reason": reason,
        "author_id": author_id
    })

async def handle_message(message: types.Message):
    if message.from_user.id == message.bot.id:
        return

    text = message.text.lower().strip()
    author_id = message.from_user.id

    if text.startswith("вручить "):
        await handle_vruchit(message)
    elif text.startswith("отнять "):
        await handle_otnyat(message, text, author_id)
    elif text == "карман":
        bal = get_user_balance(author_id)
        await message.reply(f"У тебя в кармане {bal} нуаров.")
    elif text == "прошлое":
        await show_history(message)
    elif text == "роли":
        await message.reply("Роли пока не реализованы.")
    elif text.startswith("назначить "):
        await handle_assign_role(message)
    elif text == "моя роль":
        await handle_my_role(message)
    elif text == "роль":
        await handle_check_role(message)
    elif text == "ключ от сейфа":
        await handle_grant_permission(message)
    else:
        pass

async def handle_vruchit(message: types.Message):
    if author_id != KURATOR_ID and author_id not in permissions:
        await message.reply("У тебя нет ключа от сейфа.")
        return

    text = message.text.strip()
    author_id = message.from_user.id

    # 1. Ответ на сообщение
    if message.reply_to_message:
        pattern = r"вручить\s+(\d+)"
        m = re.match(pattern, text, re.IGNORECASE)
        if not m:
            await message.reply("Неверный формат. Пример: 'вручить 5'")
            return
        amount_str = m.group(1)
        amount = int(amount_str)
        if amount <= 0:
            await message.reply("Количество должно быть положительным.")
            return
        recipient = message.reply_to_message.from_user
        change_balance(recipient.id, amount, "без причины", author_id)
        await message.reply(f"Я выдал {amount} нуаров @{recipient.username or recipient.full_name}")
        return

    # 2. Вручение по @username
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
    change_balance(member.user.id, amount, "без причины", author_id)
    await message.reply(f"Я выдал @{username} {amount} нуаров")


async def handle_otnyat(message: types.Message, text: str, author_id: int):
    if author_id != KURATOR_ID and author_id not in permissions:
        await message.reply("У тебя нет ключа от сейфа.")
        return

    # 1. Если это ответ на сообщение
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
        change_balance(recipient.id, -amount, "без причины", author_id)
        await message.reply(f"Я взыскал {amount} нуаров у @{recipient.username or recipient.full_name}")
        return

    # 2. Если указан username
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
    change_balance(member.user.id, -amount, "без причины", author_id)
    await message.reply(f"Я взыскал у @{username} {amount} нуаров.")



async def show_history(message: types.Message):
    if not history:
        await message.reply("История пуста.")
        return
    lines = []
    for entry in history[-5:]:
        uid = entry["user_id"]
        amount = entry["amount"]
        reason = entry["reason"]
        author = entry["author_id"]
        lines.append(f"user_id={uid} {'+' if amount>0 else ''}{amount} — {reason} (от {author})")
    await message.reply("\n".join(lines))

KURATOR_ID = 164059195  # Telegram ID куратора

async def handle_assign_role(message: types.Message):
    if message.from_user.id != KURATOR_ID:
        return

    if not message.reply_to_message:
        await message.reply("Но кого именно мне назначить, Куратор?")
        return

    pattern = r'назначить\s+"([^"]+)"\s+(.+)'
    m = re.match(pattern, message.text.strip(), re.IGNORECASE)
    if not m:
        await message.reply('Формат: назначить "название роли" описание')
        return

    title, description = m.groups()
    target_id = message.reply_to_message.from_user.id
    roles[target_id] = {"title": title, "description": description}
    await message.reply(f"Роль назначена: {title} — {description}")

async def handle_my_role(message: types.Message):
    role = roles.get(message.from_user.id)
    if not role:
        await message.reply("Я не узнаю Вас.")
        return
    await message.reply(f"Ваша роль: {role['title']} — {role['description']}")

async def handle_check_role(message: types.Message):
    if message.from_user.id != KURATOR_ID:
        return

    if not message.reply_to_message:
        await message.reply("Чью роль вы хотите узнать, Куратор?")
        return

    target_id = message.reply_to_message.from_user.id
    role = roles.get(target_id)
    if not role:
        await message.reply("Я не знаю кто это, Куратор.")
        return
    await message.reply(f": {role['title']} — {role['description']}")

async def handle_grant_permission(message: types.Message):
    if message.from_user.id != KURATOR_ID:
        return

    if not message.reply_to_message:
        await message.reply("Кому мне выдать ключ, Куратор?")
        return

    target_id = message.reply_to_message.from_user.id
    if target_id == KURATOR_ID:
        await message.reply("У Куратора уже есть ключ от сейфа.")
        return

    permissions.add(target_id)
    await message.reply("Я выдал ключ, Куратор.")


async def find_member_by_username(message: types.Message, username: str):
    """
    Пытаемся найти пользователя в чате по username.
    Telegram API не предоставляет прямого метода get_member_by_username,
    поэтому переберём последних 200 участников (или сколько возможно),
    и найдём совпадение по username.
    """

    chat = message.chat
    # Получаем список участников через get_chat_administrators + get_chat_member для отдельных пользователей нет, 
    # поэтому ограничимся админами, или можно хранить пользователей в базе

    # Попробуем получить администраторов (они всегда в списке)
    admins = await message.bot.get_chat_administrators(chat.id)
    for admin in admins:
        if admin.user.username and admin.user.username.lower() == username.lower():
            return admin

    # Если не нашли среди админов — попробуем получить участника по username
    # Telegram API не даёт метода прямого поиска по username,
    # поэтому рекомендуем хранить в базе или просить юзера подтвердить
    # Для MVP — вернём None
    return None
