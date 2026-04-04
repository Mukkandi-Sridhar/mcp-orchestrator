# 🌐 MCP Orchestrator

A professional orchestration suite for the **Model Context Protocol (MCP)**, featuring modular HTTP client/server implementations, advanced sampling workflows, and a modern Gradio-based interface.

![MCP Banner](https://img.shields.io/badge/MCP-Protocol-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/python-v3.10+-blue?style=for-the-badge&logo=python)
![FastMCP](https://img.shields.io/badge/FastMCP-Framework-green?style=for-the-badge)

## 🚀 Overview

The **MCP Orchestrator** is designed to bridge the gap between Large Language Models (LLMs) and local tool execution. By leveraging the Model Context Protocol over HTTP, it allows for secure, bidirectional communication between an AI host and a set of distributed tools.

### Key Components

- **📡 HTTP MCP Server**: A robust file management and code analysis server built with `FastMCP`.
- **🛠️ Base Client Library**: A reusable HTTP client for connecting to any MCP-compliant server.
- **🖥️ Desktop Client**: A high-end Gradio GUI for interacting with the MCP ecosystem.
- **🧠 AI Host Application**: An integrated LLM host (compatible with OpenAI) that utilizes MCP tools for complex reasoning tasks.

## ✨ Features

- **Bidirectional Sampling**: Implements the `sampling/createMessage` pattern for human-in-the-loop tool execution.
- **Secure File Operations**: Scoped workspace access with root-level security checks.
- **Dynamic Tool Discovery**: Automatically lists and invokes tools exposed by the MCP server.
- **Modern UI/UX**: Cinematic Gradio interface for real-time interaction and monitoring.

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Mukkandi-Sridhar/mcp-orchestrator.git
   cd mcp-orchestrator
   ```

2. **Set up a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r mcp_advanced_lab/requirements.txt
   ```

4. **Environment Variables**:
   Create a `.env` file in the root and add your OpenAI API key:
   ```env
   OPENAI_API_KEY=your_api_key_here
   ```

## 📖 Usage

### 1. Start the MCP Server
```bash
python mcp_advanced_lab/mcp_http_server.py
```

### 2. Launch the AI Host / Client
```bash
python mcp_advanced_lab/mcp_http_host_app.py
```

## 💂️ Security

This project implements **Path Traversal Protection**. All file operations are restricted to the `mcp_advanced_lab/workspace/` directory.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
Built with ❤️ for the MCP Community.
