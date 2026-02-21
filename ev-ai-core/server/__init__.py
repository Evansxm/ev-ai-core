# v2026-02-efficient-r1 - Server framework (HTTP/WS/TCP)
import asyncio, json, websockets, http.server, socketserver, threading
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import ssl


class ServerType(Enum):
    HTTP = "http"
    WS = "websocket"
    TCP = "tcp"


@dataclass
class Route:
    path: str
    method: str
    handler: Callable


class HTTPServer:
    def __init__(self, host="0.0.0.0", port=8080):
        self.host, self.port = host, port
        self.routes: Dict[str, Dict[str, Callable]] = {}
        self.server = None
        self.thread = None

    def route(self, path, method="GET"):
        def dec(func):
            self.routes.setdefault(path, {})[method.upper()] = func
            return func

        return dec

    def _make_handler(self):
        import asyncio

        class H(http.server.BaseHTTPRequestHandler):
            server_instance = self  # Store reference to our server

            def do_method(m):
                def h(self):
                    p = self.path.split("?")[0]
                    if (
                        p in self.server_instance.routes
                        and m in self.server_instance.routes[p]
                    ):
                        try:
                            handler = self.server_instance.routes[p][m]
                            l = int(self.headers.get("Content-Length", 0))
                            b = self.rfile.read(l).decode() if l else None

                            # Handle async handlers
                            if asyncio.iscoroutinefunction(handler):
                                loop = asyncio.new_event_loop()
                                try:
                                    r = loop.run_until_complete(handler(b))
                                finally:
                                    loop.close()
                            else:
                                r = handler(b)

                            self.send_response(200)
                            self.send_header("Content-Type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps(r).encode())
                        except Exception as e:
                            self.send_response(500)
                            self.send_header("Content-Type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps({"e": str(e)}).encode())
                    else:
                        self.send_response(404)
                        self.end_headers()

                return h

            do_GET = do_method("GET")
            do_POST = do_method("POST")
            do_PUT = do_method("PUT")
            do_DELETE = do_method("DELETE")

            def log_message(self, *a):
                pass

        return H

    def start(self, block=True):
        self.server = socketserver.TCPServer(
            (self.host, self.port), self._make_handler()
        )
        print(f"HTTP on {self.host}:{self.port}")
        if block:
            self.server.serve_forever()
        else:
            self.thread = threading.Thread(
                target=self.server.serve_forever, daemon=True
            )
            self.thread.start()

    def stop(self):
        self.server and self.server.shutdown()


class WebSocketServer:
    def __init__(self, host="0.0.0.0", port=8765):
        self.host, self.port = host, port
        self.clients = set()
        self.handlers: Dict[str, Callable] = {}
        self.server = None

    def on(self, event):
        def dec(func):
            self.handlers[event] = func
            return func

        return dec

    async def handle_client(self, ws, path):
        self.clients.add(ws)
        try:
            async for msg in ws:
                try:
                    d = json.loads(msg)
                    e = d.get("event", "message")
                    if e in self.handlers:
                        r = await self.handlers[e](d.get("data", {}), ws)
                        if r:
                            await ws.send(json.dumps(r))
                except json.JSONDecodeError:
                    await ws.send(json.dumps({"e": "Invalid JSON"}))
        finally:
            self.clients.discard(ws)

    async def broadcast(self, msg):
        if self.clients:
            await asyncio.gather(
                *[c.send(json.dumps(msg)) for c in self.clients], return_exceptions=True
            )

    async def start(self):
        self.server = await websockets.serve(self.handle_client, self.host, self.port)
        print(f"WS on ws://{self.host}:{self.port}")

    def stop(self):
        self.server and self.server.close()


class TCPServer:
    def __init__(self, host="0.0.0.0", port=9999):
        self.host, self.port = host, port
        self.clients = []
        self.handler = None
        self.server = None

    def on_message(self, func):
        self.handler = func
        return func

    async def handle_client(self, r, w):
        addr = w.get_extra_info("peername")
        self.clients.append((addr, w))
        try:
            while True:
                d = await r.read(100)
                if not d:
                    break
                m = d.decode()
                if self.handler:
                    rply = await self.handler(m, addr)
                    if rply:
                        w.write(rply.encode())
                        await w.drain()
        finally:
            self.clients.remove((addr, w))
            w.close()

    async def start(self):
        self.server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        print(f"TCP on {self.host}:{self.port}")
        async with self.server:
            await self.server.serve_forever()

    def stop(self):
        self.server and self.server.close()


class WSClient:
    def __init__(self, url):
        self.url = url
        self.ws = None
        self.handlers = {}

    def on(self, event):
        def dec(func):
            self.handlers[event] = func
            return func

        return dec

    async def connect(self):
        self.ws = await websockets.connect(self.url)
        asyncio.create_task(self._recv())

    async def _recv(self):
        async for m in self.ws:
            try:
                d = json.loads(m)
                e = d.get("event", "message")
                if e in self.handlers:
                    await self.handlers[e](d.get("data", {}))
            except:
                pass

    async def send(self, event, data=None):
        if self.ws:
            await self.ws.send(json.dumps({"event": event, "data": data}))

    async def close(self):
        if self.ws:
            await self.ws.close()


class TCPClient:
    def __init__(self, host, port):
        self.host, self.port = host, port
        self.r, self.w = None, None

    async def connect(self):
        self.r, self.w = await asyncio.open_connection(self.host, self.port)

    async def send(self, msg):
        if not self.w:
            await self.connect()
        self.w.write(msg.encode())
        await self.w.drain()
        d = await self.r.read(100)
        return d.decode()

    async def close(self):
        if self.w:
            self.w.close()
            await self.w.wait_closed()


class JSONRPCClient:
    def __init__(self, url):
        self.url = url
        self.rid = 0

    async def call(self, method, params=None):
        import urllib.request, urllib.error

        self.rid += 1
        req = json.dumps(
            {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": self.rid}
        ).encode()
        try:
            with urllib.request.Request(
                self.url, data=req, headers={"Content-Type": "application/json"}
            ) as r:
                with urllib.request.urlopen(r) as resp:
                    return json.loads(resp.read()).get("result")
        except urllib.error.HTTPError as e:
            raise Exception(
                json.loads(e.read()).get("error", {}).get("message", str(e))
            )


create_api_server = lambda h="0.0.0.0", p=8080: HTTPServer(h, p)
create_ws_server = lambda h="0.0.0.0", p=8765: WebSocketServer(h, p)
create_tcp_server = lambda h="0.0.0.0", p=9999: TCPServer(h, p)
