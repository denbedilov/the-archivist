import aiosqlite

DB_PATH = "bot_data.sqlite"

# --- Инициализация базы (вызывать при старте бота) ---
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                role TEXT DEFAULT NULL,
                role_description TEXT DEFAULT NULL,
                has_key INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                reason TEXT,
                author_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Куратор ID хранить можно либо отдельно, либо задавать в коде
        # В этой таблице можно хранить кураторов, если нужно несколько
        await db.commit()

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

# --- Роли ---
async def set_role(user_id: int, role: str, description: str):
    async with aiosqlite.connect(DB_PATH) as db:
        # Вставляем или обновляем
        await db.execute("""
            INSERT INTO users (user_id, role, role_description) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET role = excluded.role, role_description = excluded.role_description
        """, (user_id, role, description))
        await db.commit()

async def get_role(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT role, role_description FROM users WHERE user_id = ?", (user_id,)) as cursor:
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

