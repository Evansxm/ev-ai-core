import json
import asyncio
import aiohttp
import ssl
import certifi
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


class MCPProtocolType(Enum):
    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: Dict
    handler: Callable


@dataclass
class MCPResource:
    uri: str
    name: str
    description: str
    mime_type: str = "text/plain"


@dataclass
class MCPPrompt:
    name: str
    description: str
    arguments: Dict


class MCPBase(ABC):
    def __init__(self, name: str, protocol: MCPProtocolType = MCPProtocolType.STDIO):
        self.name = name
        self.protocol = protocol
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.prompts: Dict[str, MCPPrompt] = {}

    @abstractmethod
    async def initialize(self):
        pass

    @abstractmethod
    async def handle_request(self, method: str, params: Dict) -> Dict:
        pass

    def tool(self, name: str, description: str, input_schema: Dict):
        def decorator(func: Callable):
            self.tools[name] = MCPTool(name, description, input_schema, func)
            return func

        return decorator

    def resource(
        self, uri: str, name: str, description: str, mime_type: str = "text/plain"
    ):
        def decorator(func: Callable):
            self.resources[uri] = MCPResource(uri, name, description, mime_type)
            return func

        return decorator

    def prompt(self, name: str, description: str, arguments: Dict = None):
        def decorator(func: Callable):
            self.prompts[name] = MCPPrompt(name, description, arguments or {})
            return func

        return decorator

    def get_capabilities(self) -> Dict:
        return {
            "tools": {"listChanged": True},
            "resources": {"subscribe": True, "listChanged": True},
            "prompts": {"listChanged": True},
        }

    def get_tools_list(self) -> List[Dict]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
            }
            for tool in self.tools.values()
        ]

    def get_resources_list(self) -> List[Dict]:
        return [
            {
                "uri": res.uri,
                "name": res.name,
                "description": res.description,
                "mimeType": res.mime_type,
            }
            for res in self.resources.values()
        ]

    def get_prompts_list(self) -> List[Dict]:
        return [
            {
                "name": prompt.name,
                "description": prompt.description,
                "arguments": prompt.arguments,
            }
            for prompt in self.prompts.values()
        ]


class MCPStdioServer(MCPBase):
    def __init__(self, name: str):
        super().__init__(name, MCPProtocolType.STDIO)

    async def initialize(self):
        pass

    async def handle_request(self, method: str, params: Dict) -> Dict:
        if method == "initialize":
            return {
                "protocolVersion": "2024-11-05",
                "capabilities": self.get_capabilities(),
                "serverInfo": {"name": self.name, "version": "1.0.0"},
            }
        elif method == "tools/list":
            return {"tools": self.get_tools_list()}
        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})
            if tool_name in self.tools:
                result = await self.tools[tool_name].handler(**args)
                return {"content": [{"type": "text", "text": str(result)}]}
        elif method == "resources/list":
            return {"resources": self.get_resources_list()}
        elif method == "prompts/list":
            return {"prompts": self.get_prompts_list()}
        return {"error": "Unknown method"}


class MCPHttpClient(MCPBase):
    def __init__(self, name: str, server_url: str, api_key: str = None):
        super().__init__(name, MCPProtocolType.HTTP)
        self.server_url = server_url
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self._ssl_context = ssl.create_default_context(cafile=certifi.where())

    async def initialize(self):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        self.session = aiohttp.ClientSession(headers=headers)

    async def call_tool(self, tool_name: str, arguments: Dict) -> Any:
        if not self.session:
            await self.initialize()
        async with self.session.post(
            f"{self.server_url}/tools/{tool_name}",
            json=arguments,
            ssl=self._ssl_context,
        ) as resp:
            return await resp.json()

    async def list_tools(self) -> List[Dict]:
        if not self.session:
            await self.initialize()
        async with self.session.get(
            f"{self.server_url}/tools", ssl=self._ssl_context
        ) as resp:
            return await resp.json()

    async def get_resource(self, uri: str) -> Any:
        if not self.session:
            await self.initialize()
        async with self.session.get(
            f"{self.server_url}/resources/{uri}", ssl=self._ssl_context
        ) as resp:
            return await resp.json()

    async def handle_request(self, method: str, params: Dict) -> Dict:
        return await self.call_tool(method, params)


class MCPManager:
    def __init__(self):
        self.servers: Dict[str, MCPBase] = {}

    def register_server(self, name: str, server: MCPBase):
        self.servers[name] = server

    async def call_tool(self, server_name: str, tool_name: str, **kwargs) -> Any:
        if server_name in self.servers:
            return await self.servers[server_name].tools[tool_name].handler(**kwargs)
        raise ValueError(f"Server {server_name} not found")

    def get_all_tools(self) -> Dict[str, List[Dict]]:
        return {name: server.get_tools_list() for name, server in self.servers.items()}

    async def broadcast(self, message: Dict):
        for server in self.servers.values():
            await server.handle_request(
                message.get("method", ""), message.get("params", {})
            )


mcp_manager = MCPManager()


async def create_stdio_server(name: str) -> MCPStdioServer:
    server = MCPStdioServer(name)
    await server.initialize()
    return server


async def create_http_client(name: str, url: str, api_key: str = None) -> MCPHttpClient:
    client = MCPHttpClient(name, url, api_key)
    await client.initialize()
    return client
