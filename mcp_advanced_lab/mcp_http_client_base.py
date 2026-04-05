import asyncio
import logging
from contextlib import AsyncExitStack
from typing import List, Optional, Any, Dict

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import Tool, ResourceTemplate, Prompt

# Configure protocol-level logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mcp-client-base")

class MCPHTTPClient:
    """
    A professional, protocol-first MCP HTTP client.
    
    This class handles the core JSON-RPC over Streamable HTTP logic, 
    abstracting the complexity of session management and resource cleanup.
    """
    
    def __init__(self, server_url: str, roots_dir: str):
        """
        Initialize the client.
        
        Args:
            server_url: The base URL of the MCP server (e.g., http://127.0.0.1:8000).
            roots_dir: The local workspace directory for reference.
        """
        self.server_url = server_url.rstrip("/")
        self.roots_dir = roots_dir
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self._connected = False

    async def connect(self) -> None:
        """
        Establishes a connection to the MCP server.
        
        Safe to call multiple times; ignores requests if already connected.
        Uses AsyncExitStack to ensure all streams and sessions are cleaned up later.
        """
        if self._connected:
            return
            
        # FastMCP standardizes the MCP endpoint at /mcp
        mcp_url = f"{self.server_url}/mcp"
        logger.info(f"Connecting to MCP server at {mcp_url}...")
        
        try:
            # Step 1: Establish the streamable HTTP transport
            read, write, _ = await self.exit_stack.enter_async_context(
                streamablehttp_client(mcp_url)
            )
            
            # Step 2: Initialize the ClientSession
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            
            # Step 3: Perform protocol handshake
            await self.session.initialize()
            self._connected = True
            logger.info("MCP Session initialized successfully.")
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            await self.cleanup()
            raise

    async def list_tools(self) -> List[Tool]:
        """
        Fetches the list of available tools from the server.
        """
        if not self.session:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        result = await self.session.list_tools()
        logger.debug(f"Discovered {len(result.tools)} tools.")
        return result.tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Invokes a tool on the server with the provided arguments.
        """
        if not self.session:
            raise RuntimeError("Client not connected.")
            
        logger.info(f"Calling tool '{tool_name}' with args: {arguments}")
        result = await self.session.call_tool(tool_name, arguments)
        return result

    async def list_resources(self) -> List[ResourceTemplate]:
        """
        Fetches the list of available resource templates.
        """
        if not self.session:
            raise RuntimeError("Client not connected.")
            
        result = await self.session.list_resource_templates()
        return result.resourceTemplates

    async def read_resource(self, uri: str) -> Any:
        """
        Reads a specific resource by its URI.
        """
        if not self.session:
            raise RuntimeError("Client not connected.")
            
        logger.debug(f"Reading resource: {uri}")
        result = await self.session.read_resource(uri)
        return result

    async def list_prompts(self) -> List[Prompt]:
        """
        Fetches the list of available prompt templates.
        """
        if not self.session:
            raise RuntimeError("Client not connected.")
            
        result = await self.session.list_prompts()
        return result.prompts

    async def get_prompt(self, prompt_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Retrieves a rendered prompt from the server.
        """
        if not self.session:
            raise RuntimeError("Client not connected.")
            
        logger.info(f"Retrieving prompt '{prompt_name}'")
        result = await self.session.get_prompt(prompt_name, arguments)
        return result

    async def cleanup(self) -> None:
        """
        Closes all connections and releases protocol resources.
        """
        logger.info("Cleaning up MCP client resources...")
        await self.exit_stack.aclose()
        self._connected = False
        self.session = None
