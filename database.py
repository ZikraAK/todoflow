"""
Database handler for the To-Do app.
Uses SQLite — file-based, zero setup, ships with Python.
"""
import sqlite3
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "todo.db"


class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # access columns by name
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()
        self._seed_defaults()

    def _create_tables(self):
        cur = self.conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                color_hex TEXT NOT NULL DEFAULT '#3B82F6',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                category_id INTEGER,
                energy_level TEXT CHECK(energy_level IN ('High','Medium','Low')) DEFAULT 'Medium',
                priority TEXT CHECK(priority IN ('High','Medium','Low')) DEFAULT 'Medium',
                due_date TEXT NOT NULL,
                original_date TEXT NOT NULL,
                status TEXT CHECK(status IN ('pending','completed','deleted')) DEFAULT 'pending',
                rollover_count INTEGER DEFAULT 0,
                is_procrastinated INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS rollover_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                from_date TEXT NOT NULL,
                to_date TEXT NOT NULL,
                rolled_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS completion_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                completion_date TEXT NOT NULL,
                completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                stat_date TEXT PRIMARY KEY,
                tasks_total INTEGER DEFAULT 0,
                tasks_completed INTEGER DEFAULT 0,
                tasks_rolled INTEGER DEFAULT 0,
                completion_rate REAL DEFAULT 0.0
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS streaks (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                last_active_date TEXT,
                comeback_count INTEGER DEFAULT 0
            )
        """)

        # ensure single streak row exists
        cur.execute("INSERT OR IGNORE INTO streaks (id) VALUES (1)")
        self.conn.commit()

    def _seed_defaults(self):
        """Seed default categories on first run only."""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM categories")
        if cur.fetchone()[0] == 0:
            defaults = [
                ('Work',     '#3B82F6'),  # blue
                ('Personal', '#10B981'),  # green
                ('Study',    '#8B5CF6'),  # purple
                ('Health',   '#EF4444'),  # red
                ('Other',    '#6B7280'),  # gray
            ]
            cur.executemany(
                "INSERT INTO categories (name, color_hex) VALUES (?, ?)",
                defaults,
            )
            self.conn.commit()

    # ---------- TASKS ----------
    def add_task(self, title, description, category_id, energy_level,
                 priority, due_date):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO tasks (title, description, category_id, energy_level,
                               priority, due_date, original_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, description, category_id, energy_level,
              priority, due_date, due_date))
        self.conn.commit()
        return cur.lastrowid

    def get_tasks_for_date(self, target_date, include_completed=True):
        cur = self.conn.cursor()
        if include_completed:
            cur.execute("""
                SELECT t.*, c.name AS category_name, c.color_hex
                FROM tasks t
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.due_date = ? AND t.status != 'deleted'
                ORDER BY
                    CASE t.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
                    t.created_at
            """, (target_date,))
        else:
            cur.execute("""
                SELECT t.*, c.name AS category_name, c.color_hex
                FROM tasks t
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.due_date = ? AND t.status = 'pending'
                ORDER BY
                    CASE t.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
                    t.created_at
            """, (target_date,))
        return [dict(r) for r in cur.fetchall()]

    def get_task(self, task_id):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT t.*, c.name AS category_name, c.color_hex
            FROM tasks t LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.id = ?
        """, (task_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def update_task(self, task_id, **fields):
        if not fields:
            return
        keys = ", ".join(f"{k} = ?" for k in fields.keys())
        values = list(fields.values()) + [task_id]
        cur = self.conn.cursor()
        cur.execute(f"UPDATE tasks SET {keys} WHERE id = ?", values)
        self.conn.commit()

    def complete_task(self, task_id):
        today = date.today().isoformat()
        now = datetime.now().isoformat()
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE tasks SET status = 'completed', completed_at = ?
            WHERE id = ?
        """, (now, task_id))
        cur.execute("""
            INSERT INTO completion_log (task_id, completion_date)
            VALUES (?, ?)
        """, (task_id, today))
        self.conn.commit()

    def uncomplete_task(self, task_id):
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE tasks SET status = 'pending', completed_at = NULL
            WHERE id = ?
        """, (task_id,))
        cur.execute("DELETE FROM completion_log WHERE task_id = ?", (task_id,))
        self.conn.commit()

    def delete_task(self, task_id):
        cur = self.conn.cursor()
        cur.execute("UPDATE tasks SET status = 'deleted' WHERE id = ?",
                    (task_id,))
        self.conn.commit()

    def get_pending_tasks_before(self, target_date):
        """All non-completed tasks with due_date < target_date."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT * FROM tasks
            WHERE status = 'pending' AND due_date < ?
        """, (target_date,))
        return [dict(r) for r in cur.fetchall()]

    def log_rollover(self, task_id, from_date, to_date):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO rollover_log (task_id, from_date, to_date)
            VALUES (?, ?, ?)
        """, (task_id, from_date, to_date))
        cur.execute("""
            UPDATE tasks
            SET due_date = ?,
                rollover_count = rollover_count + 1,
                is_procrastinated = CASE
                    WHEN rollover_count + 1 >= 3 THEN 1 ELSE is_procrastinated
                END
            WHERE id = ?
        """, (to_date, task_id))
        self.conn.commit()

    # ---------- CATEGORIES ----------
    def get_categories(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM categories ORDER BY name")
        return [dict(r) for r in cur.fetchall()]

    def add_category(self, name, color_hex='#3B82F6'):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO categories (name, color_hex) VALUES (?, ?)",
            (name, color_hex),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_category(self, cat_id, name=None, color_hex=None):
        fields = {}
        if name is not None:
            fields['name'] = name
        if color_hex is not None:
            fields['color_hex'] = color_hex
        if not fields:
            return
        keys = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [cat_id]
        cur = self.conn.cursor()
        cur.execute(f"UPDATE categories SET {keys} WHERE id = ?", values)
        self.conn.commit()

    def delete_category(self, cat_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
        self.conn.commit()

    # ---------- STATS / STREAKS ----------
    def get_streak(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM streaks WHERE id = 1")
        return dict(cur.fetchone())

    def update_streak(self, current, longest, last_date, comebacks=None):
        cur = self.conn.cursor()
        if comebacks is not None:
            cur.execute("""
                UPDATE streaks SET current_streak = ?, longest_streak = ?,
                                   last_active_date = ?, comeback_count = ?
                WHERE id = 1
            """, (current, longest, last_date, comebacks))
        else:
            cur.execute("""
                UPDATE streaks SET current_streak = ?, longest_streak = ?,
                                   last_active_date = ?
                WHERE id = 1
            """, (current, longest, last_date))
        self.conn.commit()

    def get_completions_for_date(self, target_date):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM completion_log WHERE completion_date = ?",
            (target_date,),
        )
        return cur.fetchone()[0]

    def get_weekly_stats(self, end_date):
        """Last 7 days of stats."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT * FROM daily_stats
            WHERE stat_date <= ?
            ORDER BY stat_date DESC LIMIT 7
        """, (end_date,))
        return [dict(r) for r in cur.fetchall()]

    def upsert_daily_stat(self, stat_date, total, completed, rolled):
        rate = (completed / total) if total > 0 else 0.0
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO daily_stats (stat_date, tasks_total, tasks_completed,
                                      tasks_rolled, completion_rate)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(stat_date) DO UPDATE SET
                tasks_total = excluded.tasks_total,
                tasks_completed = excluded.tasks_completed,
                tasks_rolled = excluded.tasks_rolled,
                completion_rate = excluded.completion_rate
        """, (stat_date, total, completed, rolled, rate))
        self.conn.commit()

    def get_procrastinated_tasks(self):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT t.*, c.name AS category_name, c.color_hex
            FROM tasks t LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.is_procrastinated = 1 AND t.status = 'pending'
            ORDER BY t.rollover_count DESC
        """)
        return [dict(r) for r in cur.fetchall()]

    def close(self):
        self.conn.close()
