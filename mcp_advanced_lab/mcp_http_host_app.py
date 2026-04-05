import sys
import json
import asyncio
import os
import gradio as gr
from typing import List, Dict, Any, Optional
from openai import OpenAI
from mcp_http_client_base import MCPHTTPClient

class MCPHTTPHostApp(MCPHTTPClient):
    """
    Advanced AI Host Orchestrator using OpenAI LLM and MCP HTTP Server.
    Provides a professional messaging interface with full tool-calling capabilities.
    """
    
    def __init__(self, server_url: str, roots_dir: str):
        super().__init__(server_url, roots_dir)
        self.conversation_history: List[Dict[str, Any]] = []
        
        # Security: Validate API Key availability
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("⚠️ WARNING: OPENAI_API_KEY not found in environment. Chat functionality will be disabled.")
        
        self.llm_client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"

    async def _mcp_to_openai_tool(self, tool: Any) -> Dict[str, Any]:
        """Converts an MCP tool definition to OpenAI Function Calling format."""
        openai_tool = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or f"Execute {tool.name}",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        if hasattr(tool, 'inputSchema') and tool.inputSchema:
            schema = tool.inputSchema
            if isinstance(schema, dict):
                openai_tool["function"]["parameters"]["properties"] = schema.get("properties", {})
                openai_tool["function"]["parameters"]["required"] = schema.get("required", [])
        
        return openai_tool

    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Discovers all server tools and supplements them with synthetic protocol helpers."""
        await self.connect()
        mcp_tools = await self.list_tools()
        tools = [await self._mcp_to_openai_tool(t) for t in mcp_tools]
        
        # Protocol Helpers: Resources
        tools.append({
            "type": "function",
            "function": {
                "name": "mcp_list_resources",
                "description": "List all available resources from the MCP server workspace.",
                "parameters": {"type": "object", "properties": {}}
            }
        })
        tools.append({
            "type": "function",
            "function": {
                "name": "mcp_read_resource",
                "description": "Read a specific resource by URI (e.g., file://workspace/test.txt).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "uri": {"type": "string", "description": "The unique resource URI."}
                    },
                    "required": ["uri"]
                }
            }
        })
        
        # Protocol Helpers: Prompts
        tools.append({
            "type": "function",
            "function": {
                "name": "mcp_list_prompts",
                "description": "List all available prompt templates from the server.",
                "parameters": {"type": "object", "properties": {}}
            }
        })
        
        return tools

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Central dispatcher for both real MCP tools and synthetic protocol helpers."""
        await self.connect()
        
        try:
            # Handle synthetic helpers
            if tool_name == "mcp_list_resources":
                resources = await self.list_resources()
                return "Resources:\n" + "\n".join(f"- {r.uriTemplate} ({r.name})" for r in resources)
            
            if tool_name == "mcp_read_resource":
                result = await self.read_resource(arguments.get("uri", ""))
                return "\n".join(c.text for c in result.contents if hasattr(c, 'text'))
                
            if tool_name == "mcp_list_prompts":
                prompts = await self.list_prompts()
                return "Prompts:\n" + "\n".join(f"- {p.name}: {p.description}" for p in prompts)

            # Handle standard MCP tools
            result = await self.call_tool(tool_name, arguments)
            if hasattr(result, 'content') and isinstance(result.content, list):
                return "\n".join(c.text for c in result.content if hasattr(c, 'text'))
            return str(result)
            
        except Exception as e:
            return f"❌ Error executing {tool_name}: {str(e)}"

    async def chat(self, user_message: str):
        """Asynchronous conversation loop with recursive tool handling."""
        if not os.getenv("OPENAI_API_KEY"):
            return "❌ Model Error: OPENAI_API_KEY is not set. Please check your .env file."
            
        await self.connect()
        self.conversation_history.append({"role": "user", "content": user_message})
        
        tools = await self.get_available_tools()
        
        # Round 1: Let the model decide if tools are needed
        response = self.llm_client.chat.completions.create(
            model=self.model,
            messages=self.conversation_history,
            tools=tools,
            tool_choice="auto"
        )
        
        assistant_message = response.choices[0].message
        
        if assistant_message.tool_calls:
            # Prepare history structure for OpenAI's expected tool-call format
            history_tool_calls = []
            for tc in assistant_message.tool_calls:
                history_tool_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                })
            
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message.content or "Let me check that for you...",
                "tool_calls": history_tool_calls
            })
            
            # Execute all requested tools
            for tool_call in assistant_message.tool_calls:
                gr.Info(f"AI using tool: {tool_call.function.name}")
                tool_result = await self.execute_tool(
                    tool_call.function.name, 
                    json.loads(tool_call.function.arguments)
                )
                
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(tool_result)
                })
            
            # Round 2: Final synthesis
            final_response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history
            )
            final_content = final_response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": final_content})
            return final_content
            
        else:
            self.conversation_history.append({"role": "assistant", "content": assistant_message.content})
            return assistant_message.content

    def create_interface(self):
        """Builds the premium AI Host interface."""
        custom_css = """
        .chat-container { border-radius: 15px; overflow: hidden; border: 1px solid #e5e7eb; }
        .mcp-host-header { background: linear-gradient(135deg, #1e1b4b, #312e81); padding: 25px; color: white; border-radius: 15px 15px 0 0; }
        .mcp-host-header h1 { color: white !important; font-size: 24px; margin: 0; }
        """
        
        with gr.Blocks(theme=gr.themes.Soft(), css=custom_css, title="MCP AI Host") as interface:
            with gr.Div(elem_classes="mcp-host-header"):
                gr.Markdown("# 🧠 MCP Intelligence | AI Host")
                gr.Markdown(f"Status: `Connected` | Server: `{self.server_url}` | Model: `{self.model}`")
            
            chatbot = gr.Chatbot(
                label="Conversation Flow",
                height=550,
                type="messages",
                elem_classes="chat-container",
                avatar_images=(None, "https://api.dicebear.com/7.x/bottts-neutral/svg?seed=MCP")
            )
            
            with gr.Row():
                msg = gr.Textbox(
                    label="Message the Orchestrator",
                    placeholder="e.g. 'List all files in the workspace and give me a security brief on README.md'",
                    scale=7,
                    container=True
                )
                submit_btn = gr.Button("Send", variant="primary", scale=1)
                clear = gr.Button("Reset Session", variant="stop", scale=1)
            
            # Event Handlers
            async def user_wrapper(message: str, history: List):
                if not message.strip(): return history, ""
                bot_response = await self.chat(message)
                # Gradio 'messages' type handles role/content structure
                history.append({"role": "user", "content": message})
                history.append({"role": "assistant", "content": bot_response})
                return history, ""

            async def reset_wrapper():
                self.conversation_history = []
                return []

            msg.submit(fn=user_wrapper, inputs=[msg, chatbot], outputs=[chatbot, msg])
            submit_btn.click(fn=user_wrapper, inputs=[msg, chatbot], outputs=[chatbot, msg])
            clear.click(fn=reset_wrapper, outputs=[chatbot])

        return interface

def main():
    if len(sys.argv) < 3:
        print("Usage: python mcp_http_host_app.py <server_url> <roots_dir>")
        sys.exit(1)
        
    server_url, roots_dir = sys.argv[1], sys.argv[2]
    host = MCPHTTPHostApp(server_url, roots_dir)
    interface = host.create_interface()
    interface.queue().launch(server_name="127.0.0.1", server_port=7862, show_api=False)

if __name__ == "__main__":
    main()
