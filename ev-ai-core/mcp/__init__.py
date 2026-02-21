# v2026-02 - Advanced MCP capabilities
import json, asyncio, aiohttp, ssl, certifi
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class PT(Enum):
    STDIO = "stdio"
    HTTP = "http"
    WS = "websocket"


class MCPBase:
    def __init__(self, n: str, p: PT = PT.STDIO):
        self.n, self.p = n, p
        self.tools, self.res, self.prompts = {}, {}, {}

    async def init(self):
        return None

    async def handle(self, m: str, params: Dict) -> Dict:
        return {}

    def tool(self, n: str, d: str = "", s: Dict = None):
        s = s or {}

        def dec(f):
            self.tools[n] = {"n": n, "d": d, "s": s, "f": f}
            return f

        return dec

    def resource(self, u: str, n: str, d: str, m: str = "text/plain"):
        self.res[u] = {"u": u, "n": n, "d": d, "m": m}
        return lambda x: x

    def prompt(self, n: str, d: str, a: Dict = None):
        self.prompts[n] = {"n": n, "d": d, "a": a or {}}
        return lambda x: x

    def caps(self):
        return {
            "tools": {"listChanged": True},
            "resources": {"subscribe": True, "listChanged": True},
            "prompts": {"listChanged": True},
        }

    def tools_list(self):
        return [{"n": t["n"], "d": t["d"], "s": t["s"]} for t in self.tools.values()]

    def res_list(self):
        return [
            {"u": r["u"], "n": r["n"], "d": r["d"], "m": r["m"]}
            for r in self.res.values()
        ]

    def prompts_list(self):
        return [{"n": p["n"], "d": p["d"], "a": p["a"]} for p in self.prompts.values()]


class MCPServer(MCPBase):
    def __init__(self, n: str):
        super().__init__(n, PT.STDIO)

    async def handle(self, m: str, params: Dict) -> Dict:
        if m == "initialize":
            return {
                "protocolVersion": "2024-11-05",
                "capabilities": self.caps(),
                "serverInfo": {"name": self.n, "version": "1.0.0"},
            }

        if m == "tools/list":
            return {"tools": self.tools_list()}

        if m == "tools/call":
            t, a = params.get("name"), params.get("arguments", {})
            if t in self.tools:
                r = await self.tools[t]["f"](**a)
                return {"content": [{"type": "text", "text": str(r)}]}

        if m == "resources/list":
            return {"resources": self.res_list()}

        if m == "prompts/list":
            return {"prompts": self.prompts_list()}

        if m == "resources/read":
            uri = params.get("uri", "")
            if uri in self.res:
                return {"contents": [{"uri": uri, "text": "Resource content"}]}

        return {"error": "Unknown method"}


class MCPClient(MCPBase):
    def __init__(self, n: str, url: str, key: str = None):
        super().__init__(n, PT.HTTP)
        self.url, self.key = url, key
        self.sess = None
        self._ssl = ssl.create_default_context(cafile=certifi.where())

    async def init(self):
        h = {"Content-Type": "application/json"}
        if self.key:
            h["Authorization"] = f"Bearer {self.key}"
        self.sess = aiohttp.ClientSession(headers=h)

    async def call(self, t: str, args: Dict) -> Any:
        if not self.sess:
            await self.init()
        async with self.sess.post(
            f"{self.url}/tools/{t}", json=args, ssl=self._ssl
        ) as r:
            return await r.json()

    async def list_tools(self) -> List[Dict]:
        if not self.sess:
            await self.init()
        async with self.sess.get(f"{self.url}/tools", ssl=self._ssl) as r:
            return await r.json()

    async def get_resource(self, u: str) -> Any:
        if not self.sess:
            await self.init()
        async with self.sess.get(f"{self.url}/resources/{u}", ssl=self._ssl) as r:
            return await r.json()

    async def handle(self, m: str, params: Dict) -> Dict:
        return await self.call(m, params)


class MCPMgr:
    def __init__(self):
        self.servers: Dict[str, MCPBase] = {}

    def reg(self, n: str, s: MCPBase):
        self.servers[n] = s

    async def call(self, sn: str, tn: str, **kw) -> Any:
        if sn in self.servers:
            return await self.servers[sn].tools[tn]["f"](**kw)
        raise ValueError(f"Server {sn} not found")

    def all_tools(self):
        return {n: s.tools_list() for n, s in self.servers.items()}


_m = MCPMgr()
create_server = lambda n: MCPServer(n)
create_client = lambda n, u, k=None: MCPClient(n, u, k)
