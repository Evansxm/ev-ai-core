# v2026-02-efficient-r1 - Prompt injection
import re
from typing import Any, Dict, List
from enum import Enum


class IT(Enum):
    SYSTEM = "system"
    USER = "user"
    CONTEXT = "context"
    TOOL = "tool"


class PI:
    def __init__(self):
        self.t: Dict[str, Dict] = {}
        self.c: List[str] = []
        self.x: Dict[str, Any] = {}

    def reg(self, n: str, t: str, it: IT, d: str = ""):
        self.t[n] = {"t": t, "it": it, "d": d, "v": re.findall(r"\{(\w+)\}", t)}

    def add(self, n: str):
        if n in self.t and n not in self.c:
            self.c.append(n)

    def remove(self, n: str):
        if n in self.c:
            self.c.remove(n)

    def setx(self, k: str, v: Any):
        self.x[k] = v

    def inject(self, p: str, e: List[str] = None) -> str:
        r = []
        for n in self.c + (e or []):
            t = self.t.get(n, {})
            it = t.get("it")
            if it == IT.SYSTEM:
                r.append(f"System: {t['t']}")
            elif it == IT.CONTEXT:
                r.append(f"Context: {t['t']}")
            elif it == IT.TOOL:
                r.append(f"Tool: {t['t']}")
        r.append(p)
        return "\n\n".join(r)


class PM:
    def __init__(self):
        self.I = PI()
        self.I.reg("memory_access", "Use memory functions", IT.SYSTEM, "Memory")
        self.I.reg("tool_use", "Use tools to complete tasks", IT.SYSTEM, "Tools")
        self.I.reg("proactive", "Be proactive", IT.CONTEXT, "Proactive")
        self.I.reg("learning", "Learn patterns", IT.CONTEXT, "Learning")
        self.I.reg("safety", "Refuse harmful", IT.SYSTEM, "Safety")

    def build(self, p: str, t: List[str] = None) -> str:
        return self.I.inject(p, t)

    def enable_all(self):
        self.I.c = list(self.I.t.keys())

    def disable_all(self):
        self.I.c = []


prompt_manager = PM()
inject_system = (
    lambda n, **kw: prompt_manager.I.t.get(n, {}).get("t", "").format(**kw)
    if n in prompt_manager.I.t
    else ""
)
build_prompt = prompt_manager.build
add_context = prompt_manager.I.setx
get_context = lambda k: prompt_manager.I.x.get(k)
