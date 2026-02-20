import asyncio
import json
import websockets
import socket
import http.server
import socketserver
import threading
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
import ssl


class ServerType(Enum):
    HTTP = "http"
    WEBSOCKET = "websocket"
    TCP = "tcp"


@dataclass
class Route:
    path: str
    method: str
    handler: Callable


class HTTPServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.routes: Dict[str, Dict[str, Callable]] = {}
        self.server = None
        self.thread = None

    def route(self, path: str, method: str = "GET"):
        def decorator(func: Callable):
            if path not in self.routes:
                self.routes[path] = {}
            self.routes[path][method.upper()] = func
            return func

        return decorator

    def _make_handler(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_method(method):
                def handler(self):
                    path = self.path.split("?")[0]
                    if (
                        path in self.server.routes
                        and method in self.server.routes[path]
                    ):
                        handler = self.server.routes[path][method]
                        content_length = int(self.headers.get("Content-Length", 0))
                        body = (
                            self.rfile.read(content_length).decode()
                            if content_length > 0
                            else None
                        )

                        try:
                            result = handler(body)
                            self.send_response(200)
                            self.send_header("Content-Type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps(result).encode())
                        except Exception as e:
                            self.send_response(500)
                            self.send_header("Content-Type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps({"error": str(e)}).encode())
                    else:
                        self.send_response(404)
                        self.end_headers()

                return handler

            do_GET = do_method("GET")
            do_POST = do_method("POST")
            do_PUT = do_method("PUT")
            do_DELETE = do_method("DELETE")

            def log_message(self, format, *args):
                pass

        Handler.server = self
        return Handler

    def start(self, blocking: bool = True):
        self.server = socketserver.TCPServer(
            (self.host, self.port), self._make_handler()
        )
        print(f"HTTP Server started on {self.host}:{self.port}")

        if blocking:
            self.server.serve_forever()
        else:
            self.thread = threading.Thread(target=self.server.serve_forever)
            self.thread.daemon = True
            self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()


class WebSocketServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.clients = set()
        self.handlers: Dict[str, Callable] = {}
        self.server = None

    def on(self, event: str):
        def decorator(func: Callable):
            self.handlers[event] = func
            return func

        return decorator

    async def handle_client(self, websocket, path):
        self.clients.add(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    event = data.get("event", "message")
                    payload = data.get("data", {})

                    if event in self.handlers:
                        result = await self.handlers[event](payload, websocket)
                        if result is not None:
                            await websocket.send(json.dumps(result))
                    else:
                        await websocket.send(
                            json.dumps({"error": f"Unknown event: {event}"})
                        )
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"error": "Invalid JSON"}))
        finally:
            self.clients.remove(websocket)

    async def broadcast(self, message: Dict):
        if self.clients:
            await asyncio.gather(
                *[client.send(json.dumps(message)) for client in self.clients],
                return_exceptions=True,
            )

    async def start(self):
        self.server = await websockets.serve(self.handle_client, self.host, self.port)
        print(f"WebSocket Server started on ws://{self.host}:{self.port}")

    def stop(self):
        if self.server:
            self.server.close()


class TCPServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 9999):
        self.host = host
        self.port = port
        self.clients = []
        self.handler: Optional[Callable] = None
        self.server = None

    def on_message(self, func: Callable):
        self.handler = func
        return func

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info("peername")
        self.clients.append((addr, writer))

        try:
            while True:
                data = await reader.read(100)
                if not data:
                    break
                message = data.decode()
                if self.handler:
                    response = await self.handler(message, addr)
                    if response:
                        writer.write(response.encode())
                        await writer.drain()
        finally:
            self.clients.remove((addr, writer))
            writer.close()

    async def start(self):
        self.server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        print(f"TCP Server started on {self.host}:{self.port}")
        async with self.server:
            await self.server.serve_forever()

    def stop(self):
        if self.server:
            self.server.close()


class WebSocketClient:
    def __init__(self, url: str):
        self.url = url
        self.ws = None
        self.handlers: Dict[str, Callable] = {}

    def on(self, event: str):
        def decorator(func: Callable):
            self.handlers[event] = func
            return func

        return decorator

    async def connect(self):
        self.ws = await websockets.connect(self.url)
        asyncio.create_task(self._receive())

    async def _receive(self):
        async for message in self.ws:
            try:
                data = json.loads(message)
                event = data.get("event", "message")
                if event in self.handlers:
                    await self.handlers[event](data.get("data", {}))
            except:
                pass

    async def send(self, event: str, data: Any = None):
        if self.ws:
            await self.ws.send(json.dumps({"event": event, "data": data}))

    async def close(self):
        if self.ws:
            await self.ws.close()


class TCPClient:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)

    async def send(self, message: str) -> str:
        if not self.writer:
            await self.connect()
        self.writer.write(message.encode())
        await self.writer.drain()
        data = await self.reader.read(100)
        return data.decode()

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()


class JSONRPCClient:
    def __init__(self, url: str):
        self.url = url
        self.request_id = 0

    async def call(self, method: str, params: Dict = None) -> Any:
        import urllib.request
        import urllib.error

        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self.request_id,
        }

        data = json.dumps(request).encode()
        req = urllib.request.Request(
            self.url, data=data, headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req) as resp:
                response = json.loads(resp.read())
                return response.get("result")
        except urllib.error.HTTPError as e:
            error = json.loads(e.read())
            raise Exception(error.get("error", {}).get("message", str(e)))


def create_api_server(host: str = "0.0.0.0", port: int = 8080) -> HTTPServer:
    return HTTPServer(host, port)


def create_ws_server(host: str = "0.0.0.0", port: int = 8765) -> WebSocketServer:
    return WebSocketServer(host, port)


def create_tcp_server(host: str = "0.0.0.0", port: int = 9999) -> TCPServer:
    return TCPServer(host, port)
