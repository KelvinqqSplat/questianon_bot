import aiosqlite
from contextlib import asynccontextmanager
from .config import DB_PATH

@asynccontextmanager
async def db_conn():
    conn = await aiosqlite.connect(DB_PATH)
    try:
        await conn.execute("""            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("""            CREATE TABLE IF NOT EXISTS tokens (
                user_id INTEGER PRIMARY KEY,
                token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("""            CREATE TABLE IF NOT EXISTS pending_questions (
                asker_id INTEGER PRIMARY KEY,
                target_user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("""            CREATE TABLE IF NOT EXISTS threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_user_id INTEGER NOT NULL,
                asker_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                reply_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                replied_at TIMESTAMP
            )
        """)
        await conn.execute("""            CREATE TABLE IF NOT EXISTS pending_replies (
                recipient_id INTEGER PRIMARY KEY,
                thread_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("""            CREATE TABLE IF NOT EXISTS blocks (
                target_user_id INTEGER NOT NULL,
                blocked_user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (target_user_id, blocked_user_id)
            )
        """)
        await conn.execute("""            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER NOT NULL,
                thread_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("""            CREATE TABLE IF NOT EXISTS rate_events (
                user_id INTEGER NOT NULL,
                ts REAL NOT NULL
            )
        """)
        await conn.execute("""            CREATE TABLE IF NOT EXISTS global_bans (
                user_id INTEGER PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.commit()
        yield conn
    finally:
        await conn.close()

# --- helpers ---
async def upsert_user(message, admin_ids):
    async with db_conn() as conn:
        is_admin = 1 if message.from_user and message.from_user.id in admin_ids else 0
        await conn.execute(
            """            INSERT INTO users (user_id, username, first_name, last_name, is_admin)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                is_admin=excluded.is_admin
            """ ,
            (
                message.from_user.id,
                message.from_user.username,
                message.from_user.first_name,
                message.from_user.last_name,
                is_admin,
            ),
        )
        await conn.commit()

async def get_or_create_token(user_id: int, token: str):
    async with db_conn() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO tokens (user_id, token) VALUES (?, ?)",
            (user_id, token),
        )
        await conn.commit()

async def fetch_token(user_id: int):
    async with db_conn() as conn:
        async with conn.execute("SELECT token FROM tokens WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def resolve_user_by_token(token: str):
    async with db_conn() as conn:
        async with conn.execute("SELECT user_id FROM tokens WHERE token=?", (token,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def set_pending_question(asker_id: int, target_user_id: int):
    async with db_conn() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO pending_questions (asker_id, target_user_id) VALUES (?, ?)",
            (asker_id, target_user_id),
        )
        await conn.commit()

async def pop_pending_question(asker_id: int):
    async with db_conn() as conn:
        async with conn.execute("SELECT target_user_id FROM pending_questions WHERE asker_id=?", (asker_id,)) as cur:
            row = await cur.fetchone()
        await conn.execute("DELETE FROM pending_questions WHERE asker_id=?", (asker_id,))
        await conn.commit()
        return row[0] if row else None

async def set_pending_reply(recipient_id: int, thread_id: int):
    async with db_conn() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO pending_replies (recipient_id, thread_id) VALUES (?, ?)",
            (recipient_id, thread_id),
        )
        await conn.commit()

async def pop_pending_reply(recipient_id: int):
    async with db_conn() as conn:
        async with conn.execute("SELECT thread_id FROM pending_replies WHERE recipient_id=?", (recipient_id,)) as cur:
            row = await cur.fetchone()
        await conn.execute("DELETE FROM pending_replies WHERE recipient_id=?", (recipient_id,))
        await conn.commit()
        return row[0] if row else None

async def create_thread(target_user_id: int, asker_id: int, question_text: str):
    async with db_conn() as conn:
        cur = await conn.execute(
            "INSERT INTO threads (target_user_id, asker_id, question_text) VALUES (?, ?, ?)",
            (target_user_id, asker_id, question_text),
        )
        await conn.commit()
        return cur.lastrowid

async def save_reply(thread_id: int, reply_text: str):
    async with db_conn() as conn:
        await conn.execute(
            "UPDATE threads SET reply_text=?, replied_at=CURRENT_TIMESTAMP WHERE id=?",
            (reply_text, thread_id),
        )
        await conn.commit()

async def get_asker_by_thread(thread_id: int):
    async with db_conn() as conn:
        async with conn.execute("SELECT asker_id FROM threads WHERE id=?", (thread_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def block_user(target_user_id: int, blocked_user_id: int):
    async with db_conn() as conn:
        await conn.execute(
            "INSERT OR IGNORE INTO blocks (target_user_id, blocked_user_id) VALUES (?, ?)",
            (target_user_id, blocked_user_id),
        )
        await conn.commit()

async def is_blocked(target_user_id: int, blocked_user_id: int) -> bool:
    async with db_conn() as conn:
        async with conn.execute(
            "SELECT 1 FROM blocks WHERE target_user_id=? AND blocked_user_id=?",
            (target_user_id, blocked_user_id),
        ) as cur:
            return await cur.fetchone() is not None

async def add_report(reporter_id: int, thread_id: int):
    async with db_conn() as conn:
        await conn.execute(
            "INSERT INTO reports (reporter_id, thread_id) VALUES (?, ?)",
            (reporter_id, thread_id),
        )
        await conn.commit()

async def add_rate_event(user_id: int, ts: float):
    async with db_conn() as conn:
        await conn.execute("INSERT INTO rate_events (user_id, ts) VALUES (?, ?)", (user_id, ts))
        await conn.commit()

async def count_recent_rate_events(user_id: int, since_ts: float) -> int:
    async with db_conn() as conn:
        async with conn.execute(
            "SELECT COUNT(*) FROM rate_events WHERE user_id=? AND ts>=?",
            (user_id, since_ts),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

async def prune_rate_events(before_ts: float):
    async with db_conn() as conn:
        await conn.execute("DELETE FROM rate_events WHERE ts<?", (before_ts,))
        await conn.commit()

async def stats_for_user(user_id: int):
    async with db_conn() as conn:
        async with conn.execute(
            "SELECT COUNT(*) FROM threads WHERE target_user_id=?", (user_id,)
        ) as cur:
            total = (await cur.fetchone())[0]
        async with conn.execute(
            "SELECT COUNT(*) FROM threads WHERE target_user_id=? AND reply_text IS NULL",
            (user_id,)
        ) as cur:
            pending = (await cur.fetchone())[0]
        async with conn.execute(
            "SELECT COUNT(*) FROM threads WHERE target_user_id=? AND reply_text IS NOT NULL",
            (user_id,)
        ) as cur:
            answered = (await cur.fetchone())[0]
    return total, pending, answered

async def global_stats():
    async with db_conn() as conn:
        async with conn.execute("SELECT COUNT(*) FROM users") as cur:
            users = (await cur.fetchone())[0]
        async with conn.execute("SELECT COUNT(*) FROM threads") as cur:
            threads = (await cur.fetchone())[0]
        async with conn.execute("SELECT COUNT(*) FROM reports") as cur:
            reports = (await cur.fetchone())[0]
    return users, threads, reports

async def cleanup_old_threads(retention_days: int):
    async with db_conn() as conn:
        await conn.execute(
            "DELETE FROM threads WHERE created_at < DATETIME('now', ?)",
            (f"-{retention_days} days",)
        )
        await conn.commit()

# --- admin helpers ---
async def add_global_ban(user_id: int):
    async with db_conn() as conn:
        await conn.execute("INSERT OR REPLACE INTO global_bans (user_id) VALUES (?)", (user_id,))
        await conn.commit()

async def remove_global_ban(user_id: int):
    async with db_conn() as conn:
        await conn.execute("DELETE FROM global_bans WHERE user_id=?", (user_id,))
        await conn.commit()

async def is_globally_banned(user_id: int) -> bool:
    async with db_conn() as conn:
        async with conn.execute("SELECT 1 FROM global_bans WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone() is not None

async def list_users(limit: int = 20, offset: int = 0):
    async with db_conn() as conn:
        async with conn.execute(
            "SELECT user_id, username, first_name, last_name, is_admin, created_at FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ) as cur:
            return await cur.fetchall()

async def get_user_profile(user_id: int):
    async with db_conn() as conn:
        async with conn.execute("SELECT user_id, username, first_name, last_name, is_admin, created_at FROM users WHERE user_id=?", (user_id,)) as cur:
            user = await cur.fetchone()
        async with conn.execute("SELECT COUNT(*) FROM threads WHERE target_user_id=?", (user_id,)) as cur:
            total = (await cur.fetchone())[0]
        async with conn.execute("SELECT COUNT(*) FROM threads WHERE target_user_id=? AND reply_text IS NULL", (user_id,)) as cur:
            pending = (await cur.fetchone())[0]
        async with conn.execute("SELECT COUNT(*) FROM threads WHERE target_user_id=? AND reply_text IS NOT NULL", (user_id,)) as cur:
            answered = (await cur.fetchone())[0]
        return user, total, pending, answered

async def recent_reports(limit: int = 20, offset: int = 0):
    async with db_conn() as conn:
        async with conn.execute(
            "SELECT r.id, r.reporter_id, r.thread_id, r.created_at, t.target_user_id, t.asker_id, t.question_text, t.reply_text "
            "FROM reports r JOIN threads t ON t.id = r.thread_id "
            "ORDER BY r.id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ) as cur:
            return await cur.fetchall()

async def export_users_csv(path: str):
    import csv
    async with db_conn() as conn:
        async with conn.execute("SELECT user_id, username, first_name, last_name, is_admin, created_at FROM users ORDER BY created_at DESC") as cur:
            rows = await cur.fetchall()
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["user_id","username","first_name","last_name","is_admin","created_at"])
        for r in rows:
            w.writerow(r)

async def search_users(query: str, limit: int = 20, offset: int = 0):
    q = query.strip()
    sql = "SELECT user_id, username, first_name, last_name, is_admin, created_at FROM users WHERE 1=1 "
    params = []
    if q.isdigit():
        sql += "AND user_id=? "
        params.append(int(q))
    else:
        sql += "AND (COALESCE(username,'') LIKE ? OR COALESCE(first_name,'') LIKE ? OR COALESCE(last_name,'') LIKE ?) "
        like = f"%{q}%"
        params.extend([like, like, like])
    sql += "ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    async with db_conn() as conn:
        async with conn.execute(sql, tuple(params)) as cur:
            return await cur.fetchall()

async def fetch_threads_for_user(target_user_id: int, status: str = "all", days: int | None = None, limit: int = 20, offset: int = 0):
    conds = ["target_user_id=?"]
    params = [target_user_id]
    if status == "pending":
        conds.append("reply_text IS NULL")
    elif status == "answered":
        conds.append("reply_text IS NOT NULL")
    if days:
        conds.append("created_at >= DATETIME('now', ?)")
        params.append(f"-{days} days")
    where = " AND ".join(conds)
    sql = f"SELECT id, asker_id, question_text, reply_text, created_at, replied_at FROM threads WHERE {where} ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    async with db_conn() as conn:
        async with conn.execute(sql, tuple(params)) as cur:
            return await cur.fetchall()

async def export_threads_csv(target_user_id: int, status: str = "all", days: int | None = None, path: str = "threads_export.csv"):
    import csv
    rows = await fetch_threads_for_user(target_user_id, status=status, days=days, limit=100000, offset=0)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id","asker_id","question_text","reply_text","created_at","replied_at"])
        for r in rows:
            w.writerow(r)

async def fetch_threads_global(status: str = "all", days: int | None = None, limit: int = 20, offset: int = 0):
    conds = ["1=1"]
    params = []
    if status == "pending":
        conds.append("reply_text IS NULL")
    elif status == "answered":
        conds.append("reply_text IS NOT NULL")
    if days:
        conds.append("created_at >= DATETIME('now', ?)")
        params.append(f"-{days} days")
    where = " AND ".join(conds)
    sql = f"SELECT id, target_user_id, asker_id, question_text, reply_text, created_at, replied_at FROM threads WHERE {where} ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    async with db_conn() as conn:
        async with conn.execute(sql, tuple(params)) as cur:
            return await cur.fetchall()

async def get_thread(thread_id: int):
    async with db_conn() as conn:
        async with conn.execute(
            "SELECT id, target_user_id, asker_id, question_text, reply_text, created_at, replied_at FROM threads WHERE id=?",
            (thread_id,)
        ) as cur:
            return await cur.fetchone()
