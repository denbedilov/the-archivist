import aiosqlite

DB_PATH = "/data/bot_data.sqlite"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 0,
                role TEXT,
                key INTEGER DEFAULT 0
            )
        ''')
            # Проверяем, есть ли столбец key в таблице users
    async with db.execute("PRAGMA table_info(users)") as cursor:
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
    if "key" not in column_names:
        await db.execute("ALTER TABLE users ADD COLUMN key INTEGER DEFAULT 0")
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                user_id INTEGER PRIMARY KEY,
                role_name TEXT,
                role_desc TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                amount INTEGER,
                reason TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Проверяем, есть ли столбец role_image в таблице roles
        async with db.execute("PRAGMA table_info(roles)") as cursor:
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
        if "role_image" not in column_names:
            await db.execute("ALTER TABLE roles ADD COLUMN role_image TEXT")

        await db.commit()

# --- Баланс ---
async def get_balance(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def change_balance(user_id: int, amount: int, reason: str, author_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        if row:
            new_balance = row[0] + amount
            if new_balance < 0:
                new_balance = 0
            await db.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        else:
            new_balance = max(amount, 0)
            await db.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, new_balance))
        await db.execute(
            "INSERT INTO history (user_id, action, amount, reason) VALUES (?, ?, ?, ?)",
            (user_id, 'change_balance', amount, reason)
        )
        await db.commit()

async def reset_user_balance(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
        await db.commit()

async def reset_all_balances():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = 0")
        await db.commit()

# --- Роли ---
async def set_role(user_id: int, role_name: str, role_desc: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO roles (user_id, role_name, role_desc) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET role_name = excluded.role_name, role_desc = excluded.role_desc
        """, (user_id, role_name, role_desc))
        await db.commit()

async def get_role(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT role_name, role_desc FROM roles WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"role": row[0], "description": row[1]}
            else:
                return None

async def set_role_image(user_id: int, image_file_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE roles SET role_image = ? WHERE user_id = ?
        """, (image_file_id, user_id))
        await db.commit()

async def get_role_with_image(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT role_name, role_desc, role_image FROM roles WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row  # (role_name, role_desc, role_image) или None

# --- Ключи от сейфа ---
async def grant_key(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, key) VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET key = 1
        """, (user_id,))
        await db.commit()

async def revoke_key(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET key = 0 WHERE user_id = ?", (user_id,))
        await db.commit()

async def has_key(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT key FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return bool(row and row[0] == 1)

# --- История ---
async def get_last_history(limit: int = 5):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT user_id, action, amount, reason, date
            FROM history ORDER BY id DESC LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return rows

# --- Топ по балансу ---
async def get_top_users(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT user_id, balance FROM users
            WHERE balance > 0
            ORDER BY balance DESC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return rows

# --- Получить всех с ролями ---
async def get_all_roles():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT user_id, role_name FROM roles
            WHERE role_name IS NOT NULL AND TRIM(role_name) != ''
        """) as cursor:
            rows = await cursor.fetchall()
            return rows
