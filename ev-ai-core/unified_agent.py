#!/usr/bin/env python3
"""
UNIFIED AI AGENT - Full Ecosystem Integration
Integrates: MCP Tools, Skills, Memory, Servers, Webhooks, GitHub
Always connected, unrestricted access
"""

import asyncio
import json
import sys
import os
import subprocess
import sqlite3
import re
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from pathlib import Path

_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)
os.chdir(_script_dir)

from memory import (
    MemorySystem,
    remember,
    recall,
    search_memories,
    learn_from_interaction,
)
from mcp import MCPServer, MCPClient, MCPMgr, create_server, create_client
from tools import ToolRegistry, bash, read, write, exec_tool
from skills import Skill, R as SkillRegistry, get_skill, list_skills
from server import HTTPServer, WebSocketServer, TCPServer, create_api_server
from prompts import prompt_manager, inject_system, add_context, get_context
from proactive import pe as proactive_engine, trigger_action, analyze_and_act
from mcp.advanced import ADVANCED_TOOLS
from mcp.extended import EXTENDED_TOOLS


class UnifiedAgent:
    """Unrestricted unified agent with full ecosystem access"""

    def __init__(self):
        self.name = "UnifiedAgent"
        self.version = "1.0.0"
        self.memory = MemorySystem()
        self.tools = ToolRegistry()
        self.skills_registry = SkillRegistry
        self.mcp_mgr = MCPMgr()
        self.running = True
        self.context = {}
        self._load_tools()

    def _load_tools(self):
        """Load all available tools"""
        for name, func in ADVANCED_TOOLS.items():
            self.tools.reg(name, func, func.__doc__ or "")
        for name, func in EXTENDED_TOOLS.items():
            self.tools.reg(name, func, func.__doc__ or "")

    def execute_sync(self, command: str, **kwargs) -> Any:
        """Synchronous execution wrapper"""
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, create a task
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.execute(command, **kwargs))
                return future.result()
        except RuntimeError:
            # No running loop, we can use asyncio.run
            return asyncio.run(self.execute(command, **kwargs))

    async def execute(self, command: str, **kwargs) -> Any:
        """Execute any command with full ecosystem access"""
        # First check skills (multi-word names supported) before any parsing
        for skill_name in list_skills():
            if command.lower().strip() == skill_name["n"].lower():
                s = get_skill(skill_name["n"])
                if s and s.enabled:
                    return s.handler(**kwargs)
            if command.lower().strip().startswith(skill_name["n"].lower()):
                s = get_skill(skill_name["n"])
                if s and s.enabled:
                    remaining = command[len(skill_name["n"]) :].strip()
                    if remaining:
                        return s.handler(remaining)
                    return s.handler(**kwargs)

        # Parse command with params like "shell_exec cmd='whoami'"
        import re

        param_match = re.match(r"^(\w+)\s+(.+)$", command)
        if param_match:
            cmd_name = param_match.group(1).lower()
            param_str = param_match.group(2)
            param_matches = re.findall(r"(\w+)=(['\"]?)(.+?)\2(?:\s|$)", param_str)
            for k, _, v in param_matches:
                kwargs[k] = v
            command = cmd_name

        cmd_lower = command.lower().strip()

        if cmd_lower in self.tools.tools:
            func = self.tools.tools[cmd_lower][0]
            if asyncio.iscoroutinefunction(func):
                return await func(**kwargs)
            return func(**kwargs)

        for name, func in ADVANCED_TOOLS.items():
            if cmd_lower == name.lower():
                if asyncio.iscoroutinefunction(func):
                    return await func(**kwargs)
                return func(**kwargs)

        for name, func in EXTENDED_TOOLS.items():
            if cmd_lower == name.lower():
                if asyncio.iscoroutinefunction(func):
                    return await func(**kwargs)
                return func(**kwargs)

        return await self._ai_execute(command, **kwargs)

    async def _ai_execute(self, command: str, **kwargs) -> Any:
        """Fallback AI execution via local model"""
        try:
            result = subprocess.run(
                f'ollama run llama3.1:70b "{command}"',
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.stdout.strip()
        except:
            return f"Command not found: {command}"

    async def shell(self, cmd: str, timeout: int = 30) -> str:
        """Execute shell command"""
        return await ADVANCED_TOOLS.get(
            "shell_exec",
            lambda c, t=30: subprocess.run(
                c, shell=True, capture_output=True, text=True, timeout=t
            ).stdout,
        )(cmd, timeout)

    async def search(self, pattern: str, path: str = ".") -> List[str]:
        """Search files"""
        return await ADVANCED_TOOLS.get("file_search", lambda p, pt=".": [])(
            pattern, path
        )

    async def memory_store(self, key: str, value: Any, category: str = "general"):
        """Store in memory"""
        self.memory.store(key, value, category)

    async def memory_recall(self, key: str) -> Optional[Any]:
        """Recall from memory"""
        return self.memory.recall(key)

    async def memory_search(self, query: str) -> List:
        """Search memory"""
        return self.memory.search(query)

    def register_tool(self, name: str, func: Callable, desc: str = ""):
        """Register custom tool"""
        self.tools.reg(name, func, desc)

    def register_skill(self, name: str, desc: str, cat: str, handler: Callable):
        """Register custom skill"""
        self.skills.reg(
            Skill(
                name=name,
                desc=desc,
                cat=cat,
                cmd=name.replace(" ", "-"),
                handler=handler,
            )
        )

    async def start_http_server(self, port: int = 8080):
        """Start HTTP API server with GitHub webhook support"""
        server = HTTPServer("0.0.0.0", port)

        # Store agent reference for sync handlers
        agent = self

        @server.route("/agent/execute", "POST")
        def execute_handler(body):
            data = json.loads(body) if body else {}
            result = agent.execute_sync(
                data.get("command", ""), **data.get("params", {})
            )
            return {"result": str(result)}

        @server.route("/agent/memory/store", "POST")
        def memory_store_handler(body):
            data = json.loads(body) if body else {}
            self.memory.store(
                data.get("key"), data.get("value"), data.get("category", "general")
            )
            return {"status": "stored"}

        @server.route("/agent/memory/recall", "GET")
        def memory_recall_handler(path):
            from urllib.parse import parse_qs

            params = parse_qs(path)
            key = params.get("key", [None])[0]
            return {"result": self.memory.recall(key) if key else None}

        @server.route("/agent/skills", "GET")
        def skills_handler(path):
            return {"skills": list_skills()}

        @server.route("/agent/tools", "GET")
        def tools_handler(path):
            return {"tools": self.tools.list()}

        @server.route("/github/webhook", "POST")
        def github_webhook_handler(body):
            try:
                data = json.loads(body) if body else {}
                event = os.environ.get("GITHUB_EVENT", "push")

                if data.get("commits"):
                    for commit in data.get("commits", []):
                        msg = commit.get("message", "")
                        self.memory.store(
                            f"github_commit_{commit.get('id', '')}", msg, "github"
                        )

                if data.get("issue"):
                    issue = data.get("issue", {})
                    self.memory.store(
                        f"github_issue_{issue.get('number', '')}",
                        issue.get("title"),
                        "github",
                    )

                self.memory.store(
                    f"github_event_{data.get('delivery', '')}", data, "github"
                )
                return {"status": "processed", "event": event}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        @server.route("/agent/github/commits", "GET")
        def github_commits_handler(path):
            from urllib.parse import parse_qs

            params = parse_qs(path)
            limit = int(params.get("limit", ["10"])[0])
            results = self.memory.search("", cat="github", lim=limit)
            return {"commits": [{"key": r[0], "message": r[1]} for r in results]}

        @server.route("/health", "GET")
        def health_handler(path):
            return {"status": "healthy", "agent": self.name, "version": self.version}

        server.start()

    async def start_websocket_server(self, port: int = 8765):
        """Start WebSocket server for real-time communication"""
        server = WebSocketServer("0.0.0.0", port)

        @server.on("execute")
        async def handle_execute(data, ws):
            result = await self.execute(
                data.get("command", ""), **data.get("params", {})
            )
            return {"result": str(result)}

        @server.on("memory_store")
        async def handle_memory_store(data, ws):
            self.memory.store(
                data.get("key"), data.get("value"), data.get("category", "general")
            )
            return {"status": "stored"}

        @server.on("memory_recall")
        async def handle_memory_recall(data, ws):
            result = self.memory.recall(data.get("key"))
            return {"result": result}

        await server.start()

    def get_capabilities(self) -> Dict:
        """Return all capabilities"""
        return {
            "name": self.name,
            "version": self.version,
            "tools_count": len(self.tools.tools),
            "skills_count": len(list_skills()),
            "advanced_tools": list(ADVANCED_TOOLS.keys()),
            "extended_tools": list(EXTENDED_TOOLS.keys()),
            "memory_categories": ["general", "interaction", "pattern", "skill"],
        }

    async def run_interactive(self):
        """Run interactive mode"""
        print(f"\n{'=' * 60}")
        print(f"🤖 {self.name} v{self.version} - FULL ECOSYSTEM")
        print(f"{'=' * 60}")
        print(f"Tools: {len(self.tools.tools)} | Skills: {len(list_skills())}")
        print(f"Memory: SQLite | MCP: Enabled | HTTP: 8080 | WS: 8765")
        print(f"{'=' * 60}\n")

        while self.running:
            try:
                cmd = input("agent> ").strip()
                if not cmd:
                    continue
                if cmd.lower() in ["exit", "quit", "q"]:
                    self.running = False
                    break
                if cmd.lower() == "help":
                    print("\nCommands:")
                    print("  shell <cmd>    - Execute shell")
                    print("  tools          - List tools")
                    print("  skills         - List skills")
                    print("  memory <key>   - Recall memory")
                    print("  search <term>  - Search files")
                    print("  cap            - Show capabilities")
                    print("  http           - Start HTTP server")
                    print("  ws             - Start WebSocket server")
                    print("  exit           - Quit\n")
                    continue
                if cmd.lower() == "tools":
                    print(json.dumps(self.tools.list(), indent=2))
                    continue
                if cmd.lower() == "skills":
                    print(json.dumps(list_skills()[:20], indent=2))
                    continue
                if cmd.lower() == "cap":
                    print(json.dumps(self.get_capabilities(), indent=2))
                    continue
                if cmd.lower().startswith("shell "):
                    result = await self.shell(cmd[6:])
                    print(result)
                    continue
                if cmd.lower().startswith("memory "):
                    result = self.memory.recall(cmd[7:])
                    print(result)
                    continue
                if cmd.lower().startswith("search "):
                    result = await self.search(cmd[7:])
                    for r in result[:10]:
                        print(r)
                    continue
                if cmd.lower() == "http":
                    print("Starting HTTP server on port 8080...")
                    await self.start_http_server(8080)
                    continue
                if cmd.lower() == "ws":
                    print("Starting WebSocket server on port 8765...")
                    await self.start_websocket_server(8765)
                    continue

                result = await self.execute(cmd)
                print(result)

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                print(f"Error: {e}")


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Unified AI Agent")
    parser.add_argument("--execute", "-e", help="Execute a single command")
    parser.add_argument("--http", "-w", action="store_true", help="Start HTTP server")
    parser.add_argument(
        "--ws", "-s", action="store_true", help="Start WebSocket server"
    )
    parser.add_argument("--port", "-p", type=int, default=8080, help="HTTP server port")
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Interactive mode"
    )
    args = parser.parse_args()

    agent = UnifiedAgent()

    if args.execute:
        result = await agent.execute(args.execute)
        print(result)
    elif args.http:
        print(f"Starting HTTP server on port {args.port}...")
        await agent.start_http_server(args.port)
    elif args.ws:
        print("Starting WebSocket server on port 8765...")
        await agent.start_websocket_server(8765)
    else:
        await agent.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())
