import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "cadence.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                guild_id    INTEGER NOT NULL,
                joined_at   TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS pomodoro_sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                guild_id    INTEGER NOT NULL,
                started_at  TEXT    NOT NULL,
                ended_at    TEXT,
                duration    INTEGER NOT NULL,
                completed   INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                guild_id    INTEGER NOT NULL,
                title       TEXT    NOT NULL,
                done        INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT    NOT NULL,
                done_at     TEXT
            );

            CREATE TABLE IF NOT EXISTS hydration_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                logged_at   TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS water_reminders (
                user_id     INTEGER PRIMARY KEY,
                interval    INTEGER NOT NULL DEFAULT 30,
                active      INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS weekly_scores (
                user_id     INTEGER NOT NULL,
                guild_id    INTEGER NOT NULL,
                week_start  TEXT    NOT NULL,
                pomodoros   INTEGER NOT NULL DEFAULT 0,
                tasks_done  INTEGER NOT NULL DEFAULT 0,
                water_logs  INTEGER NOT NULL DEFAULT 0,
                score       INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, week_start)
            );
        """)
        await db.commit()


async def add_user(user_id: int, guild_id: int, joined_at: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, guild_id, joined_at) VALUES (?, ?, ?)",
            (user_id, guild_id, joined_at),
        )
        await db.commit()


async def remove_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()


async def is_user_joined(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)) as cur:
            return await cur.fetchone() is not None


async def add_task(user_id: int, guild_id: int, title: str, created_at: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO tasks (user_id, guild_id, title, created_at) VALUES (?, ?, ?, ?)",
            (user_id, guild_id, title, created_at),
        )
        await db.commit()
        return cur.lastrowid


async def get_open_tasks(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, title FROM tasks WHERE user_id = ? AND done = 0 ORDER BY id",
            (user_id,),
        ) as cur:
            return await cur.fetchall()


async def complete_task(task_id: int, user_id: int, done_at: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "UPDATE tasks SET done = 1, done_at = ? WHERE id = ? AND user_id = ? AND done = 0",
            (done_at, task_id, user_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def log_pomodoro(user_id: int, guild_id: int, started_at: str, ended_at: str, duration: int, completed: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO pomodoro_sessions (user_id, guild_id, started_at, ended_at, duration, completed)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, guild_id, started_at, ended_at, duration, int(completed)),
        )
        await db.commit()


async def log_hydration(user_id: int, logged_at: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO hydration_logs (user_id, logged_at) VALUES (?, ?)",
            (user_id, logged_at),
        )
        await db.commit()


async def get_water_reminder(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM water_reminders WHERE user_id = ?", (user_id,)
        ) as cur:
            return await cur.fetchone()


async def set_water_reminder(user_id: int, interval: int, active: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO water_reminders (user_id, interval, active) VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET interval = excluded.interval, active = excluded.active""",
            (user_id, interval, int(active)),
        )
        await db.commit()


async def update_weekly_score(user_id: int, guild_id: int, week_start: str, pomodoros: int = 0, tasks_done: int = 0, water_logs: int = 0):
    score_delta = (pomodoros * 50) + (tasks_done * 20) + (water_logs * 10)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO weekly_scores (user_id, guild_id, week_start, pomodoros, tasks_done, water_logs, score)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, week_start) DO UPDATE SET
                   pomodoros  = pomodoros  + excluded.pomodoros,
                   tasks_done = tasks_done + excluded.tasks_done,
                   water_logs = water_logs + excluded.water_logs,
                   score      = score      + excluded.score""",
            (user_id, guild_id, week_start, pomodoros, tasks_done, water_logs, score_delta),
        )
        await db.commit()


async def get_weekly_stats(user_id: int, week_start: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM weekly_scores WHERE user_id = ? AND week_start = ?",
            (user_id, week_start),
        ) as cur:
            return await cur.fetchone()


async def get_leaderboard(guild_id: int, week_start: str, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT user_id, score, pomodoros, tasks_done, water_logs
               FROM weekly_scores
               WHERE guild_id = ? AND week_start = ?
               ORDER BY score DESC LIMIT ?""",
            (guild_id, week_start, limit),
        ) as cur:
            return await cur.fetchall()
