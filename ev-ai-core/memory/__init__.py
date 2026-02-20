import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Optional
from pathlib import Path


class MemorySystem:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.expanduser("~/.ev_ai/memory.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                category TEXT,
                importance INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_input TEXT,
                agent_response TEXT,
                context TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT,
                description TEXT,
                examples TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills_learned (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT,
                skill_data TEXT,
                learned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def store(
        self, key: str, value: Any, category: str = "general", importance: int = 1
    ):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO memories (key, value, category, importance, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
            (key, json.dumps(value), category, importance),
        )
        self.conn.commit()

    def recall(self, key: str) -> Optional[Any]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE memories SET access_count = access_count + 1 WHERE key = ?
        """,
            (key,),
        )
        self.conn.commit()
        cursor.execute("SELECT value FROM memories WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None

    def search(self, query: str, category: str = None, limit: int = 10):
        cursor = self.conn.cursor()
        if category:
            cursor.execute(
                """
                SELECT key, value, category, importance FROM memories 
                WHERE (key LIKE ? OR value LIKE ?) AND category = ?
                ORDER BY importance DESC, access_count DESC LIMIT ?
            """,
                (f"%{query}%", f"%{query}%", category, limit),
            )
        else:
            cursor.execute(
                """
                SELECT key, value, category, importance FROM memories 
                WHERE key LIKE ? OR value LIKE ?
                ORDER BY importance DESC, access_count DESC LIMIT ?
            """,
                (f"%{query}%", f"%{query}%", limit),
            )
        return cursor.fetchall()

    def store_interaction(
        self, user_input: str, agent_response: str, context: str = None
    ):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO interactions (user_input, agent_response, context)
            VALUES (?, ?, ?)
        """,
            (user_input, agent_response, context),
        )
        self.conn.commit()

    def get_recent_interactions(self, limit: int = 20):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT user_input, agent_response, context, timestamp 
            FROM interactions ORDER BY timestamp DESC LIMIT ?
        """,
            (limit,),
        )
        return cursor.fetchall()

    def learn_user_pattern(self, pattern: str, description: str, examples: list):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_patterns (pattern, description, examples)
            VALUES (?, ?, ?)
        """,
            (pattern, description, json.dumps(examples)),
        )
        self.conn.commit()

    def get_user_patterns(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT pattern, description, examples FROM user_patterns")
        rows = cursor.fetchall()
        return [(r[0], r[1], json.loads(r[2])) for r in rows]

    def store_skill(self, skill_name: str, skill_data: dict):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO skills_learned (skill_name, skill_data)
            VALUES (?, ?)
        """,
            (skill_name, json.dumps(skill_data)),
        )
        self.conn.commit()

    def get_skills(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT skill_name, skill_data FROM skills_learned")
        rows = cursor.fetchall()
        return {r[0]: json.loads(r[1]) for r in rows}

    def get_all_memories(self, category: str = None):
        cursor = self.conn.cursor()
        if category:
            cursor.execute(
                "SELECT key, value FROM memories WHERE category = ?", (category,)
            )
        else:
            cursor.execute("SELECT key, value FROM memories")
        return cursor.fetchall()

    def delete(self, key: str):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM memories WHERE key = ?", (key,))
        self.conn.commit()

    def close(self):
        self.conn.close()


memory = MemorySystem()


def remember(key: str, value: Any, category: str = "general", importance: int = 1):
    memory.store(key, value, category, importance)


def recall(key: str) -> Optional[Any]:
    return memory.recall(key)


def search_memories(query: str, category: str = None) -> list:
    return memory.search(query, category)


def learn_from_interaction(user_input: str, agent_response: str, context: str = None):
    memory.store_interaction(user_input, agent_response, context)


def get_user_preferences():
    patterns = memory.get_user_patterns()
    return {"patterns": patterns}


def learn_skill(skill_name: str, skill_data: dict):
    memory.store_skill(skill_name, skill_data)


def get_learned_skills():
    return memory.get_skills()
