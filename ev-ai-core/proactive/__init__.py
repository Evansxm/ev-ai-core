# v2026-02-efficient-r1 - Proactive action engine
import re, time, threading
from typing import Any, Callable, Dict, List
from enum import Enum


class TT(Enum):
    KEYWORD = "keyword"
    PATTERN = "pattern"
    TIME = "time"


class AP(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class Trigger:
    def __init__(self, t: TT, p: str):
        self.t, self.p = t, p
        self.rx = re.compile(p, re.I) if t in (TT.KEYWORD, TT.PATTERN) else None

    def m(self, txt: str) -> bool:
        if self.t == TT.KEYWORD:
            return self.p.lower() in txt.lower()
        if self.t == TT.PATTERN:
            return bool(self.rx.search(txt))
        return False


class Action:
    def __init__(
        self, n: str, h: Callable, d: str = "", p: AP = AP.NORMAL, cd: int = 0
    ):
        self.n, self.h, self.d, self.p, self.cd = n, h, d, p, cd
        self.lr = 0.0


class PE:
    def __init__(self):
        self.T: List[Trigger] = []
        self.A: Dict[str, Action] = {}
        self.AT: Dict[str, List[Trigger]] = {}
        self.L: Dict[str, List[str]] = {}
        self.C: Dict[str, Any] = {}
        self._m, self._mt = False, None

    def reg(self, a: Action):
        self.A[a.n] = a

    def on_kw(self, kw: str, an: str):
        t = Trigger(TT.KEYWORD, kw)
        self.T.append(t)
        self.AT.setdefault(an, []).append(t)

    def on_pat(self, pat: str, an: str):
        t = Trigger(TT.PATTERN, pat)
        self.T.append(t)
        self.AT.setdefault(an, []).append(t)

    def trig(self, n: str, d: str = "", p: AP = AP.NORMAL):
        def dec(f: Callable):
            self.reg(Action(n, f, d, p))
            return f

        return dec

    def analyze(self, txt: str) -> List[Action]:
        r = []
        for an, ts in self.AT.items():
            a = self.A.get(an)
            if not a:
                continue
            for t in ts:
                if t.m(txt):
                    if a.cd > 0:
                        now = time.time()
                        if now - a.lr < a.cd:
                            continue
                        a.lr = now
                    r.append(a)
                    break
        r.sort(key=lambda x: x.p.value, reverse=True)
        return r

    def exec_act(self, acts: List[Action], ctx: Dict = None) -> List[Dict]:
        res = []
        for a in acts:
            try:
                res.append({"a": a.n, "r": a.h({**self.C, **(ctx or {})})})
            except Exception as e:
                res.append({"a": a.n, "e": str(e)})
        return res

    def learn(self, pat: str, ctx: str):
        self.L.setdefault(ctx, []).append(pat)

    def set_ctx(self, k: str, v: Any):
        self.C[k] = v

    def en(self, n: str):
        if n in self.A:
            self.A[n].p = AP.HIGH

    def dis(self, n: str):
        if n in self.A:
            self.A[n].p = AP.LOW

    def list_act(self) -> List[Dict]:
        return [{"n": a.n, "d": a.d, "p": a.p.name} for a in self.A.values()]

    def start_mon(self, cb: Callable):
        self._m = True

        def m():
            while self._m:
                acts = self.analyze("")
                if acts:
                    cb(acts)
                time.sleep(1)

        self._mt = threading.Thread(target=m, daemon=True)
        self._mt.start()

    def stop_mon(self):
        self._m = False


pe = PE()


@pe.trig("auto_save", "Auto-save", AP.HIGH)
def auto_save(c):
    return "Auto-save triggered"


@pe.trig("suggest_improvements", "Suggest", AP.NORMAL)
def suggest_improvements(c):
    return "Suggestions ready"


trigger_action = lambda n, **c: pe.A.get(n).h(c) if n in pe.A else None
analyze_and_act = lambda t, c=None: pe.exec_act(pe.analyze(t), c)
learn_user_behavior = lambda i, a: (pe.learn(i, "u"), pe.learn(a, "a"))
set_user_context = lambda **kw: [pe.set_ctx(k, v) for k, v in kw.items()]
