#!/usr/bin/env python3
"""
COMMUNICATION PROTOCOLS - Multiple connection modes
WebSocket, TCP, GraphQL, Telegram, Slack, Discord, Email, MQTT, gRPC, Webhooks
"""

import asyncio
import json
import os
import socket
import ssl
import smtplib
import sqlite3
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
import subprocess

# Setup path
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)
os.chdir(_script_dir)

# Import core modules
from memory import MemorySystem
from datetime import datetime

# Try importing optional dependencies
try:
    import websockets
except:
    websockets = None

try:
    from paho.mqtt import client as mqtt_client
except:
    mqtt_client = None


class MultiProtocolAgent:
    """Agent with multiple connection protocols"""

    def __init__(self):
        self.name = "MultiProtocolAgent"
        self.memory = MemorySystem()
        self.ws_servers = []
        self.tcp_servers = []
        self.mqtt_clients = []
        self.servers_running = {}

    # ==================== HTTP SERVER ====================

    def start_http(self, port: int = 8080, agent_instance=None):
        """Start HTTP server with full API"""
        from server import HTTPServer

        server = HTTPServer("0.0.0.0", port)

        @server.route("/health", "GET")
        def health(path):
            return {"status": "healthy", "protocols": list(self.servers_running.keys())}

        @server.route("/execute", "POST")
        def execute(body):
            if not agent_instance:
                return {"error": "No agent instance"}
            data = json.loads(body) if body else {}
            result = agent_instance.execute_sync(
                data.get("command", ""), **data.get("params", {})
            )
            return {"result": str(result)}

        @server.route("/memory/store", "POST")
        def mem_store(body):
            data = json.loads(body) if body else {}
            self.memory.store(
                data.get("key"), data.get("value"), data.get("category", "general")
            )
            return {"status": "stored"}

        @server.route("/memory/recall", "GET")
        def mem_recall(path):
            from urllib.parse import parse_qs

            params = parse_qs(path)
            key = params.get("key", [None])[0]
            return {"result": self.memory.recall(key)}

        @server.route("/graphql", "POST")
        def graphql(body):
            return self._handle_graphql(body)

        @server.route("/telegram/webhook", "POST")
        def telegram_webhook(body):
            return self._handle_telegram(body)

        @server.route("/slack/webhook", "POST")
        def slack_webhook(body):
            return self._handle_slack(body)

        @server.route("/discord/webhook", "POST")
        def discord_webhook(body):
            return self._handle_discord(body)

        @server.route("/webhook/generic", "POST")
        def generic_webhook(body):
            return self._handle_generic_webhook(body)

        server.start(block=False)
        self.servers_running[f"http_{port}"] = server
        print(f"HTTP server started on port {port}")
        return server

    def _handle_graphql(self, body: str) -> Dict:
        """Handle GraphQL queries"""
        try:
            data = json.loads(body) if body else {}
            query = data.get("query", "")
            variables = data.get("variables", {})

            # Simple GraphQL resolver
            if "health" in query.lower():
                return {"data": {"health": "ok"}}
            if "memory" in query.lower():
                if "recall" in query.lower():
                    key = variables.get("key", "")
                    return {"data": {"memory": self.memory.recall(key)}}
                return {"data": {"memory": "store"}}
            if "system" in query.lower():
                return {"data": {"system": "info"}}

            return {"data": {"result": "Query executed"}}
        except Exception as e:
            return {"errors": [{"message": str(e)}]}

    # ==================== WEBSOCKET SERVER ====================

    def start_websocket(self, port: int = 8765, agent_instance=None):
        """Start WebSocket server"""
        if not websockets:
            return {"error": "websockets not installed"}

        import websockets

        clients = set()

        async def handler(ws, path):
            clients.add(ws)
            try:
                async for msg in ws:
                    try:
                        data = json.loads(msg)
                        command = data.get("command", "")
                        params = data.get("params", {})

                        if agent_instance:
                            result = agent_instance.execute_sync(command, **params)
                        else:
                            result = "No agent"

                        await ws.send(json.dumps({"result": str(result)}))
                    except:
                        await ws.send(json.dumps({"error": "Invalid message"}))
            finally:
                clients.discard(ws)

        async def run_ws():
            async with websockets.serve(handler, "0.0.0.0", port):
                print(f"WebSocket server on ws://0.0.0.0:{port}")
                await asyncio.Future()

        asyncio.run(run_ws())

    # ==================== TCP SERVER ====================

    def start_tcp(self, port: int = 9999, agent_instance=None):
        """Start raw TCP server"""

        async def handle_client(reader, writer):
            addr = writer.get_extra_info("peername")
            print(f"TCP client connected: {addr}")

            try:
                while True:
                    data = await reader.read(100)
                    if not data:
                        break

                    message = data.decode().strip()
                    print(f"Received: {message}")

                    # Execute command
                    if agent_instance:
                        result = agent_instance.execute_sync(message)
                    else:
                        result = "No agent"

                    writer.write((str(result) + "\n").encode())
                    await writer.drain()
            except Exception as e:
                print(f"Error: {e}")
            finally:
                writer.close()

        async def run_tcp():
            server = await asyncio.start_server(handle_client, "0.0.0.0", port)
            print(f"TCP server on 0.0.0.0:{port}")
            async with server:
                await server.serve_forever()

        asyncio.run(run_tcp())

    # ==================== TELEGRAM ====================

    def _handle_telegram(self, body: str) -> Dict:
        """Handle Telegram webhook"""
        try:
            data = json.loads(body) if body else {}
            message = data.get("message", {})
            text = message.get("text", "")
            chat_id = message.get("chat", {}).get("id")

            # Store message
            self.memory.store(f"telegram_{chat_id}", text, "telegram")

            return {"ok": True, "chat_id": chat_id}
        except Exception as e:
            return {"error": str(e)}

    def send_telegram(self, token: str, chat_id: str, text: str) -> Dict:
        """Send message via Telegram bot"""
        import urllib.request

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = json.dumps({"chat_id": chat_id, "text": text}).encode()

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            return {"error": str(e)}

    # ==================== SLACK ====================

    def _handle_slack(self, body: str) -> Dict:
        """Handle Slack webhook"""
        try:
            from urllib.parse import parse_qs

            data = parse_qs(body)
            text = data.get("text", [""])[0]
            user = data.get("user_name", ["user"])[0]

            self.memory.store(f"slack_{user}", text, "slack")

            return {"response_type": "in_channel", "text": f"Received: {text}"}
        except Exception as e:
            return {"error": str(e)}

    def send_slack(self, webhook_url: str, text: str) -> Dict:
        """Send message via Slack webhook"""
        import urllib.request

        data = json.dumps({"text": text}).encode()
        req = urllib.request.Request(webhook_url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req) as r:
                return {"status": "sent"}
        except Exception as e:
            return {"error": str(e)}

    # ==================== DISCORD ====================

    def _handle_discord(self, body: str) -> Dict:
        """Handle Discord webhook"""
        try:
            data = json.loads(body) if body else {}
            content = data.get("content", "")
            username = data.get("username", "user")

            self.memory.store(f"discord_{username}", content, "discord")

            return {"status": "received"}
        except Exception as e:
            return {"error": str(e)}

    def send_discord(
        self, webhook_url: str, content: str, username: str = "Agent"
    ) -> Dict:
        """Send message via Discord webhook"""
        import urllib.request

        data = json.dumps({"content": content, "username": username}).encode()
        req = urllib.request.Request(webhook_url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req) as r:
                return {"status": "sent"}
        except Exception as e:
            return {"error": str(e)}

    # ==================== EMAIL (SMTP) ====================

    def send_email(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        to: str,
        subject: str,
        body: str,
        use_tls: bool = True,
    ) -> Dict:
        """Send email via SMTP"""
        try:
            msg = MIMEMultipart()
            msg["From"] = username
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            if use_tls:
                server = smtplib.SMTP(smtp_host, smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(smtp_host, smtp_port)

            server.login(username, password)
            server.send_message(msg)
            server.quit()

            return {"status": "sent", "to": to}
        except Exception as e:
            return {"error": str(e)}

    # ==================== MQTT ====================

    def start_mqtt(
        self,
        broker: str,
        port: int,
        topic: str,
        client_id: str = "agent",
        username: str = None,
        password: str = None,
        agent_instance=None,
    ):
        """Start MQTT client"""
        if not mqtt_client:
            return {"error": "paho-mqtt not installed"}

        import paho.mqtt.client as mqtt

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print(f"Connected to MQTT broker {broker}")
                client.subscribe(topic)
            else:
                print(f"MQTT connection failed: {rc}")

        def on_message(client, userdata, msg):
            payload = msg.payload.decode()
            print(f"MQTT received: {payload}")

            # Execute command if agent available
            if agent_instance:
                result = agent_instance.execute_sync(payload)
                # Publish result
                client.publish(topic + "/response", result)

        client = mqtt.Client(client_id)
        if username and password:
            client.username_pw_set(username, password)

        client.on_connect = on_connect
        client.on_message = on_message

        client.connect(broker, port, 60)
        client.loop_forever()

    def publish_mqtt(
        self,
        broker: str,
        port: int,
        topic: str,
        message: str,
        client_id: str = "agent_pub",
        username: str = None,
        password: str = None,
    ) -> Dict:
        """Publish to MQTT topic"""
        if not mqtt_client:
            return {"error": "paho-mqtt not installed"}

        import paho.mqtt.client as mqtt

        client = mqtt.Client(client_id)
        if username and password:
            client.username_pw_set(username, password)

        try:
            client.connect(broker, port, 60)
            client.publish(topic, message)
            client.disconnect()
            return {"status": "published", "topic": topic}
        except Exception as e:
            return {"error": str(e)}

    # ==================== GENERIC WEBHOOK ====================

    def _handle_generic_webhook(self, body: str) -> Dict:
        """Handle generic webhook"""
        try:
            data = json.loads(body) if body else {}

            # Store webhook data
            timestamp = datetime.now().isoformat()
            self.memory.store(f"webhook_{timestamp}", data, "webhook")

            return {"status": "received", "timestamp": timestamp}
        except Exception as e:
            return {"error": str(e)}

    def call_webhook(
        self, url: str, method: str = "POST", data: Dict = None, headers: Dict = None
    ) -> Dict:
        """Call external webhook"""
        import urllib.request

        req = urllib.request.Request(url, method=method)

        if headers:
            for k, v in headers.items():
                req.add_header(k, v)

        if data:
            req.data = json.dumps(data).encode()
            req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req) as r:
                return {"status": r.status, "body": r.read().decode()}
        except Exception as e:
            return {"error": str(e)}

    # ==================== WEBSOCKET CLIENT ====================

    async def ws_connect(self, url: str, message: str = None) -> Dict:
        """Connect to external WebSocket and optionally send message"""
        if not websockets:
            return {"error": "websockets not installed"}

        try:
            async with websockets.connect(url) as ws:
                if message:
                    await ws.send(message)
                    response = await ws.recv()
                    return {"status": "sent", "response": response}
                return {"status": "connected"}
        except Exception as e:
            return {"error": str(e)}

    # ==================== TCP CLIENT ====================

    def tcp_connect(self, host: str, port: int, message: str) -> Dict:
        """Send raw TCP message"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            sock.send((message + "\n").encode())

            response = sock.recv(4096).decode()
            sock.close()

            return {"status": "sent", "response": response}
        except Exception as e:
            return {"error": str(e)}

    # ==================== UDP ====================

    def udp_send(self, host: str, port: int, message: str) -> Dict:
        """Send UDP packet"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(message.encode(), (host, port))
            sock.close()
            return {"status": "sent", "host": host, "port": port}
        except Exception as e:
            return {"error": str(e)}

    # ==================== GRPC ====================

    def start_grpc(self, port: int = 50051):
        """Start gRPC server (simple version)"""
        # Simple gRPC-like over HTTP
        from server import HTTPServer

        server = HTTPServer("0.0.0.0", port)

        @server.route("/grpc", "POST")
        def grpc_handler(body):
            data = json.loads(body) if body else {}
            return {
                "service": "agent",
                "method": data.get("method", ""),
                "status": "ok",
            }

        server.start(block=False)
        print(f"gRPC server on port {port}")
        return server

    # ==================== SUMMARY ====================

    def get_status(self) -> Dict:
        """Get status of all protocols"""
        return {
            "name": self.name,
            "running_servers": list(self.servers_running.keys()),
            "memory_items": len(self.memory.search("")),
        }


# Standalone protocol functions for easy import
def http_request(
    url: str, method: str = "GET", data: Dict = None, headers: Dict = None
) -> Dict:
    """Make HTTP request"""
    import urllib.request

    req = urllib.request.Request(url, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if data:
        req.data = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            return {"status": r.status, "body": r.read().decode()}
    except Exception as e:
        return {"error": str(e)}


def ws_client(url: str, message: str = None) -> Dict:
    """WebSocket client"""
    if not websockets:
        return {"error": "websockets not installed"}
    import asyncio

    mp = MultiProtocolAgent()
    return asyncio.run(mp.ws_connect(url, message))


def mqtt_publish(broker: str, port: int, topic: str, message: str) -> Dict:
    """Publish to MQTT"""
    mp = MultiProtocolAgent()
    return mp.publish_mqtt(broker, port, topic, message)


def send_telegram_message(token: str, chat_id: str, text: str) -> Dict:
    """Send Telegram message"""
    mp = MultiProtocolAgent()
    return mp.send_telegram(token, chat_id, text)


def send_slack_message(webhook_url: str, text: str) -> Dict:
    """Send Slack message"""
    mp = MultiProtocolAgent()
    return mp.send_slack(webhook_url, text)


def send_discord_message(webhook_url: str, content: str) -> Dict:
    """Send Discord message"""
    mp = MultiProtocolAgent()
    return mp.send_discord(webhook_url, content)


def send_email(
    smtp_host: str,
    smtp_port: int,
    username: str,
    password: str,
    to: str,
    subject: str,
    body: str,
) -> Dict:
    """Send email"""
    mp = MultiProtocolAgent()
    return mp.send_email(smtp_host, smtp_port, username, password, to, subject, body)


def tcp_client(host: str, port: int, message: str) -> Dict:
    """TCP client"""
    mp = MultiProtocolAgent()
    return mp.tcp_connect(host, port, message)


def udp_client(host: str, port: int, message: str) -> Dict:
    """UDP client"""
    mp = MultiProtocolAgent()
    return mp.udp_send(host, port, message)


__all__ = [
    "MultiProtocolAgent",
    "http_request",
    "ws_client",
    "mqtt_publish",
    "send_telegram_message",
    "send_slack_message",
    "send_discord_message",
    "send_email",
    "tcp_client",
    "udp_client",
]
