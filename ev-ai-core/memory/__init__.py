# v2026-02-efficient-r1 - Memory system
import json, os, sqlite3
from typing import Any, Optional
from pathlib import Path


class MemorySystem:
    def __init__(self, db=None):
        db = db or os.path.expanduser("~/.ev_ai/memory.db")
        Path(db).parent.mkdir(parents=True, exist_ok=True)
        self.c = sqlite3.connect(db, check_same_thread=False)
        self.c.execute(
            """CREATE TABLE IF NOT EXISTS memories(k TEXT UNIQUE,v TEXT,c TEXT,i INT DEFAULT 1,ac INT DEFAULT 0)"""
        )
        self.c.execute(
            """CREATE TABLE IF NOT EXISTS interactions(u TEXT,a TEXT,ctx TEXT)"""
        )
        self.c.execute(
            """CREATE TABLE IF NOT EXISTS user_patterns(p TEXT,d TEXT,x TEXT)"""
        )
        self.c.execute("""CREATE TABLE IF NOT EXISTS skills_learned(s TEXT,d TEXT)""")
        self.c.commit()

    def store(self, k: str, v: Any, c: str = "general", i: int = 1):
        self.c.execute(
            "INSERT OR REPLACE INTO memories(k,v,c,i) VALUES(?,?,?,?)",
            (k, json.dumps(v), c, i),
        )
        self.c.commit()

    def recall(self, k: str) -> Optional[Any]:
        self.c.execute("UPDATE memories SET ac=ac+1 WHERE k=?", (k,))
        self.c.commit()
        r = self.c.execute("SELECT v FROM memories WHERE k=?", (k,)).fetchone()
        return json.loads(r[0]) if r else None

    def search(self, q: str, cat: str = None, lim: int = 10):
        if cat:
            return self.c.execute(
                "SELECT k,v,c,i FROM memories WHERE (k LIKE ? OR v LIKE ?) AND c=? ORDER BY i DESC,ac DESC LIMIT ?",
                (f"%{q}%", f"%{q}%", cat, lim),
            ).fetchall()
        return self.c.execute(
            "SELECT k,v,c,i FROM memories WHERE k LIKE ? OR v LIKE ? ORDER BY i DESC,ac DESC LIMIT ?",
            (f"%{q}%", f"%{q}%", lim),
        ).fetchall()

    def store_interaction(self, u: str, a: str, ctx=None):
        self.c.execute("INSERT INTO interactions(u,a,ctx) VALUES(?,?,?)", (u, a, ctx))
        self.c.commit()

    def get_recent(self, lim=20):
        return self.c.execute(
            "SELECT u,a,ctx FROM interactions ORDER BY ROWID DESC LIMIT ?", (lim,)
        ).fetchall()

    def learn_pattern(self, p: str, d: str, x: list):
        self.c.execute(
            "INSERT INTO user_patterns(p,d,x) VALUES(?,?,?)", (p, d, json.dumps(x))
        )
        self.c.commit()

    def get_patterns(self):
        return [
            (r[0], r[1], json.loads(r[2]))
            for r in self.c.execute("SELECT p,d,x FROM user_patterns").fetchall()
        ]

    def store_skill(self, s: str, d: dict):
        self.c.execute(
            "INSERT OR REPLACE INTO skills_learned(s,d) VALUES(?,?)", (s, json.dumps(d))
        )
        self.c.commit()

    def get_skills(self):
        return {
            r[0]: json.loads(r[1])
            for r in self.c.execute("SELECT s,d FROM skills_learned").fetchall()
        }

    def get_all(self, cat=None):
        return self.c.execute(
            "SELECT k,v FROM memories" + (f" WHERE c='{cat}'" if cat else "")
        ).fetchall()

    def delete(self, k: str):
        self.c.execute("DELETE FROM memories WHERE k=?", (k,))
        self.c.commit()

    def close(self):
        self.c.close()


_m = MemorySystem()
remember = _m.store
recall = _m.recall
search_memories = _m.search
learn_from_interaction = _m.store_interaction
get_user_preferences = lambda: {"patterns": _m.get_patterns()}
learn_skill = _m.store_skill
get_learned_skills = _m.get_skills
