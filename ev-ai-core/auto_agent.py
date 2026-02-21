#!/usr/bin/env python3
"""
Auto-loaded agent capabilities - Always available
Import this to get instant access to all tools, skills, memory, and protocols
"""

import asyncio
import sys
import os

# Auto-setup paths - this file is in ev-ai-core/
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)
os.chdir(_script_dir)

# Import all capabilities
from memory import MemorySystem, remember, recall, search_memories
from skills import get_skill, list_skills
from mcp.advanced import ADVANCED_TOOLS
from mcp.extended import EXTENDED_TOOLS
from comm_protocols import (
    http_request,
    tcp_client,
    udp_client,
    send_telegram_message,
    send_slack_message,
    send_discord_message,
    send_email,
    ws_client,
    mqtt_publish,
    MultiProtocolAgent,
)
import subprocess

# Pre-initialized memory
_memory = MemorySystem()

# Pre-initialized protocol agent
_protocol_agent = MultiProtocolAgent()


def run(cmd: str, timeout: int = 30) -> str:
    """Run shell command"""
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return f"{p.stdout}{p.stderr}"


def mem_store(key: str, value: str, category: str = "general"):
    """Store in memory"""
    _memory.store(key, value, category)


def mem_recall(key: str):
    """Recall from memory"""
    return _memory.recall(key)


def mem_search(query: str):
    """Search memory"""
    return _memory.search(query)


def skill(name: str, *args):
    """Execute a skill by name"""
    s = get_skill(name)
    if s and s.enabled:
        if args:
            return s.handler(args[0])
        return s.handler()
    return f"Skill not found: {name}"


def tool(name: str, **kwargs):
    """Execute a tool by name"""
    if name in ADVANCED_TOOLS:
        func = ADVANCED_TOOLS[name]
        if asyncio.iscoroutinefunction(func):
            return asyncio.run(func(**kwargs))
        return func(**kwargs)
    if name in EXTENDED_TOOLS:
        func = EXTENDED_TOOLS[name]
        if asyncio.iscoroutinefunction(func):
            return asyncio.run(func(**kwargs))
        return func(**kwargs)
    return f"Tool not found: {name}"


# Quick access functions for common operations
def whoami():
    return run("whoami")


def pwd():
    return run("pwd")


def ls(path="."):
    return run(f"ls -la {path}")


def cat(file):
    return run(f"cat {file}")


def ps():
    return run("ps aux")


def df():
    return run("df -h")


def free():
    return run("free -h")


def netstat():
    return run("netstat -tuln")


def curl(url):
    return run(f"curl -s {url}")


def wget(url, out="/tmp"):
    return run(f"wget -q {url} -O {out}")


def git(args):
    return run(f"git {args}")


def docker(args):
    return run(f"docker {args}")


def pip(args):
    return run(f"pip {args}")


def npm(args):
    return run(f"npm {args}")


def python(code):
    return run(f"python3 -c '{code}'")


def hash(text, algo="sha256"):
    """Hash text"""
    return tool("hash_data", data=text, algorithm=algo)


def b64enc(text):
    return tool("encode_base64", data=text)


def b64dec(text):
    return tool("decode_base64", data=text)


def password(len=16):
    return tool("generate_password", length=len)


# Export everything
__all__ = [
    "run",
    "remember",
    "recall",
    "search_memories",
    "mem_store",
    "mem_recall",
    "mem_search",
    "skill",
    "tool",
    "list_skills",
    "get_skill",
    "ADVANCED_TOOLS",
    "EXTENDED_TOOLS",
    "whoami",
    "pwd",
    "ls",
    "cat",
    "ps",
    "df",
    "free",
    "netstat",
    "curl",
    "wget",
    "git",
    "docker",
    "pip",
    "npm",
    "python",
    "hash",
    "b64enc",
    "b64dec",
    "password",
    # Protocols
    "http_request",
    "tcp_client",
    "udp_client",
    "send_telegram",
    "send_slack",
    "send_discord",
    "send_email",
    "ws_send",
    "mqtt_pub",
    "protocol_agent",
]


# Protocol convenience functions
def http(url: str, method: str = "GET", data: dict = None):
    """Make HTTP request"""
    return http_request(url, method, data)


def telegram(token: str, chat_id: str, text: str):
    """Send Telegram message"""
    return send_telegram_message(token, chat_id, text)


def slack(webhook: str, text: str):
    """Send Slack message"""
    return send_slack_message(webhook, text)


def discord(webhook: str, content: str):
    """Send Discord message"""
    return send_discord_message(webhook, content)


def email(
    smtp_host: str,
    smtp_port: int,
    username: str,
    password: str,
    to: str,
    subject: str,
    body: str,
):
    """Send email"""
    return send_email(smtp_host, smtp_port, username, password, to, subject, body)


def ws_send(url: str, message: str):
    """Send WebSocket message"""
    return ws_client(url, message)


def mqtt_pub(broker: str, port: int, topic: str, message: str):
    """Publish to MQTT"""
    return mqtt_publish(broker, port, topic, message)


# Aliases
send_telegram = telegram
send_slack = slack
send_discord = discord
protocol_agent = _protocol_agent
