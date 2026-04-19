import sqlite3
from app.core.config import settings
from app.models.schemas import ConversationTurn


def init_db() -> None:
    with sqlite3.connect(settings.db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                role    TEXT NOT NULL,
                content TEXT NOT NULL,
                ts      TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        conn.commit()


def save(user_msg: str, ai_msg: str) -> None:
    with sqlite3.connect(settings.db_path) as conn:
        conn.execute("INSERT INTO conversations (role,content) VALUES (?,?)", ("user", user_msg))
        conn.execute("INSERT INTO conversations (role,content) VALUES (?,?)", ("assistant", ai_msg))
        conn.commit()


def load(limit: int = 10) -> list[ConversationTurn]:
    with sqlite3.connect(settings.db_path) as conn:
        rows = conn.execute(
            "SELECT role,content FROM conversations ORDER BY id DESC LIMIT ?",
            (limit * 2,),
        ).fetchall()

    rows = list(reversed(rows))
    history: list[ConversationTurn] = []
    i = 0
    while i < len(rows) - 1:
        if rows[i][0] == "user" and rows[i + 1][0] == "assistant":
            history.append(ConversationTurn(user=rows[i][1], assistant=rows[i + 1][1]))
            i += 2
        else:
            i += 1
    return history


def clear() -> None:
    with sqlite3.connect(settings.db_path) as conn:
        conn.execute("DELETE FROM conversations")
        conn.commit()
