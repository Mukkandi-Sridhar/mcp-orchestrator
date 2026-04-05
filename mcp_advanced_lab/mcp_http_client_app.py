import sys
import json
import asyncio
import gradio as gr
from typing import Tuple, List, Any
from mcp_http_client_base import MCPHTTPClient

class MCPHTTPClientApp(MCPHTTPClient):
    """
    State-of-the-art GUI client for the MCP Protocol.
    Extends the base client with a premium Gradio interface.
    """
    
    def __init__(self, server_url: str, roots_dir: str):
        super().__init__(server_url, roots_dir)
        self.tools_cache = []
        self.prompts_cache = []

    async def gui_list_tools(self) -> Tuple[str, Any]:
        """Discovers tools and updates the GUI dropdown."""
        try:
            await self.connect()
            tools = await self.list_tools()
            self.tools_cache = tools
            
            output = "### 🛠️ Discovered Tools\n\n"
            for t in tools:
                output += f"**{t.name}**: {t.description}\n\n"
            
            choices = [t.name for t in tools]
            return output, gr.update(choices=choices)
        except Exception as e:
            return f"### ❌ Connection Error\n{str(e)}", gr.update(choices=[])

    async def gui_call_tool(self, tool_name: str, arguments_json: str) -> str:
        """Executes a tool call and returns the formatted result."""
        if not self.session:
            return "⚠️ Please connect to the server first."
        if not tool_name:
            return "⚠️ Please select a tool from the dropdown."
            
        try:
            args = json.loads(arguments_json) if arguments_json.strip() else {}
            gr.Info(f"Executing {tool_name}...")
            result = await self.call_tool(tool_name, args)
            
            output = ""
            for content in getattr(result, 'content', []):
                if hasattr(content, 'text'):
                    output += content.text + "\n"
            
            return output if output else "✅ Tool executed (no return content)."
        except json.JSONDecodeError:
            return "❌ Error: Invalid JSON arguments. Please check your syntax."
        except Exception as e:
            return f"❌ Execution Error: {str(e)}"

    async def gui_list_resources(self) -> str:
        """Discovers resource templates and formats them for display."""
        try:
            await self.connect()
            resources = await self.list_resources()
            if not resources:
                return "ℹ️ No resources exposed by server."
            
            output = "### 📂 Available Resources\n\n"
            for r in resources:
                name = getattr(r, 'name', 'Untitled')
                uri = getattr(r, 'uriTemplate', getattr(r, 'uri', 'Unknown URI'))
                desc = getattr(r, 'description', 'No description provided.')
                output += f"**{name}**\n- URI: `{uri}`\n- *{desc}*\n\n"
            return output
        except Exception as e:
            return f"❌ Resource Discovery Error: {str(e)}"

    async def gui_read_resource(self, uri: str) -> str:
        """Reads a resource and returns its content."""
        if not self.session:
            return "⚠️ Please connect to the server first."
        if not uri:
            return "⚠️ Please provide a Resource URI."
            
        try:
            gr.Info(f"Reading resource: {uri}")
            result = await self.read_resource(uri)
            output = ""
            for content in getattr(result, 'contents', []):
                if hasattr(content, 'text'):
                    output += content.text + "\n"
            return output if output else "📄 Resource accessed (empty content)."
        except Exception as e:
            return f"❌ Read Error: {str(e)}"

    async def gui_list_prompts(self) -> Tuple[str, Any]:
        """Discovers prompts and updates the GUI dropdown."""
        try:
            await self.connect()
            prompts = await self.list_prompts()
            self.prompts_cache = prompts
            
            output = "### 💡 Available Prompts\n\n"
            choices = []
            for p in prompts:
                args = f"({', '.join(a.name for a in p.arguments)})" if p.arguments else "(no args)"
                output += f"**{p.name}** {args}: {p.description}\n\n"
                choices.append(p.name)
            
            return output, gr.update(choices=choices)
        except Exception as e:
            return f"❌ Prompt Discovery Error: {str(e)}", gr.update(choices=[])

    async def gui_get_prompt(self, prompt_name: str, arguments_json: str) -> str:
        """Retrieves and formats a rendered prompt."""
        if not self.session:
            return "⚠️ Please connect to the server first."
        if not prompt_name:
            return "⚠️ Please select a prompt from the dropdown."
            
        try:
            args = json.loads(arguments_json) if arguments_json.strip() else {}
            gr.Info(f"Fetching prompt: {prompt_name}...")
            result = await self.get_prompt(prompt_name, args)
            
            output = f"### 📝 Rendered Prompt: {prompt_name}\n\n"
            for msg in getattr(result, 'messages', []):
                role = getattr(msg, 'role', 'unknown').upper()
                content = msg.content.text if hasattr(msg.content, 'text') else str(msg.content)
                output += f"**{role}**:\n{content}\n\n---\n\n"
            return output
        except json.JSONDecodeError:
            return "❌ Error: Invalid JSON arguments."
        except Exception as e:
            return f"❌ Retrieval Error: {str(e)}"

    def create_interface(self):
        """Builds the premium Gradio interface."""
        custom_css = """
        .gradio-container { font-family: 'Inter', sans-serif; }
        .mcp-header { background: linear-gradient(90deg, #4f46e5, #9333ea); padding: 20px; border-radius: 12px; color: white; margin-bottom: 20px; }
        .mcp-header h1 { margin: 0; color: white !important; }
        .tab-nav { font-weight: bold; }
        """
        
        with gr.Blocks(theme=gr.themes.Soft(), css=custom_css, title="MCP Desktop Client") as interface:
            with gr.Div(elem_classes="mcp-header"):
                gr.Markdown(f"# 🌐 MCP Orchestrator | Desktop Client")
                gr.Markdown(f"Connected to: `{self.server_url}` | Core: `Remote HTTP` | Security: `Enabled`")
            
            with gr.Tabs(elem_classes="tab-nav"):
                with gr.Tab("🛠️ Tools Orchestration"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            list_tools_btn = gr.Button("🔍 Discover Server Tools", variant="primary")
                            tools_output = gr.Markdown("Click discover to see available tools.")
                        with gr.Column(scale=1):
                            tool_dropdown = gr.Dropdown(label="Select Target Tool")
                            tool_args = gr.Code(
                                label="Execution Arguments (JSON)",
                                language="json",
                                value='{\n  "filepath": "example.txt"\n}',
                                lines=5
                            )
                            call_tool_btn = gr.Button("⚡ Execute Tool Call", variant="secondary")
                            tool_result = gr.Textbox(label="Protocol Return Content", lines=10, show_copy_button=True)
                    
                    list_tools_btn.click(fn=self.gui_list_tools, outputs=[tools_output, tool_dropdown])
                    call_tool_btn.click(fn=self.gui_call_tool, inputs=[tool_dropdown, tool_args], outputs=tool_result)

                with gr.Tab("📂 Resource Management"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            list_resources_btn = gr.Button("📑 Fetch Resource Templates", variant="primary")
                            resources_output = gr.Markdown("Fetch templates to browse workspace data.")
                        with gr.Column(scale=1):
                            resource_uri = gr.Textbox(
                                label="Target Resource URI",
                                placeholder="file://workspace/README.md",
                                lines=1
                            )
                            read_resource_btn = gr.Button("📥 Pull Resource Data", variant="secondary")
                            resource_content = gr.Code(label="Resource Source", language="markdown", lines=15)
                    
                    list_resources_btn.click(fn=self.gui_list_resources, outputs=resources_output)
                    read_resource_btn.click(fn=self.gui_read_resource, inputs=resource_uri, outputs=resource_content)

                with gr.Tab("💡 LLM Prompts"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            list_prompts_btn = gr.Button("🧠 List AI Prompts", variant="primary")
                            prompts_output = gr.Markdown("List prompts to see available workflow templates.")
                        with gr.Column(scale=1):
                            prompt_dropdown = gr.Dropdown(label="Select Template")
                            prompt_args = gr.Code(
                                label="Template Parameters (JSON)",
                                language="json",
                                value='{\n  "filename": "code.py"\n}',
                                lines=5
                            )
                            get_prompt_btn = gr.Button("✨ Render AI Prompt", variant="secondary")
                            prompt_result = gr.Markdown(label="Generated Prompt Sequence")
                    
                    list_prompts_btn.click(fn=self.gui_list_prompts, outputs=[prompts_output, prompt_dropdown])
                    get_prompt_btn.click(fn=self.gui_get_prompt, inputs=[prompt_dropdown, prompt_args], outputs=prompt_result)

        return interface

def main():
    if len(sys.argv) < 3:
        print("Usage: python mcp_http_client_app.py <server_url> <roots_dir>")
        sys.exit(1)
    
    server_url, roots_dir = sys.argv[1], sys.argv[2]
    client = MCPHTTPClientApp(server_url, roots_dir)
    interface = client.create_interface()
    interface.queue().launch(server_name="127.0.0.1", server_port=7861, show_api=False)

if __name__ == "__main__":
    main()
