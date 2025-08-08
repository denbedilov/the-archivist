import aiosqlite

DB_PATH = "/data/bot_data.sqlite"

# --- Инициализация базы (вызывать при старте бота) ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Создаем таблицы, если их нет
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 0,
            role TEXT,
            key INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS roles (
            user_id INTEGER PRIMARY KEY,
            role_name TEXT,
            role_desc TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            amount INTEGER,
            reason TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Добавляем новый столбец для фото роли, если он отсутствует
    try:
        cursor.execute("ALTER TABLE roles ADD COLUMN role_image TEXT")
    except sqlite3.OperationalError:
        pass  # столбец уже есть

    conn.commit()
    conn.close()


# --- Баланс ---
async def get_balance(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def change_balance(user_id: int, amount: int, reason: str, author_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем есть ли пользователь
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        if row:
            new_balance = row[0] + amount
            await db.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        else:
            new_balance = amount
            await db.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, new_balance))
        await db.execute(
            "INSERT INTO history (user_id, amount, reason, author_id) VALUES (?, ?, ?, ?)",
            (user_id, amount, reason, author_id)
        )
        await db.commit()
# Обнулить баланс конкретного участника
async def reset_user_balance(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
        await db.commit()

# Обнулить балансы всех участников
async def reset_all_balances():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = 0")
        await db.commit()

# --- Роли ---
async def set_role(user_id: int, role: str, description: str):
    async with aiosqlite.connect(DB_PATH) as db:
        # Вставляем или обновляем
        await db.execute("""
            INSERT INTO roles (user_id, role, description) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET role = excluded.role, description = excluded.description
        """, (user_id, role, description))
        await db.commit()

async def get_role(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT role, description FROM roles WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                return {"role": row[0], "description": row[1]}
            else:
                return None

# --- Полномочия (ключи от сейфа) ---
async def grant_key(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        # Добавляем или обновляем ключ
        await db.execute("""
            INSERT INTO users (user_id, has_key) VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET has_key = 1
        """, (user_id,))
        await db.commit()

async def revoke_key(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET has_key = 0 WHERE user_id = ?", (user_id,))
        await db.commit()

async def has_key(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT has_key FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return bool(row and row[0] == 1)

# --- История последних изменений баланса ---
async def get_last_history(limit: int = 5):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT user_id, amount, reason, author_id, timestamp 
            FROM history ORDER BY id DESC LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return rows

async def get_top_users(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT user_id, balance FROM users
            WHERE balance > 0
            ORDER BY balance DESC
            LIMIT ?
        """, (limit,)) as cursor:
            return await cursor.fetchall()

async def get_all_roles():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT user_id, role FROM roles
            WHERE role IS NOT NULL AND TRIM(role) != ''
        """) as cursor:
            return await cursor.fetchall()

async def set_role_image(user_id, image_file_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE roles SET image_file_id = ? WHERE user_id = ?", (image_file_id, user_id))
    conn.commit()
    conn.close()

async def get_role_with_image(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT role_name, role_description, image_file_id FROM roles WHERE user_id = ?", (user_id,))
    role = c.fetchone()
    conn.close()
    return role