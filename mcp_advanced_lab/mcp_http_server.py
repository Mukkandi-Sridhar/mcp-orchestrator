from pathlib import Path
import logging
import warnings
from typing import List, Optional

from fastmcp import FastMCP

# Configuration and Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mcp-server")

# Suppress noisy FastMCP internal warnings for a cleaner console
warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger("fastmcp").setLevel(logging.WARNING)

# Initialize MCP Server
mcp = FastMCP("HTTP File Server")

# Workspace Configuration
BASE_DIR = Path(__file__).parent / "workspace"
BASE_DIR.mkdir(exist_ok=True)

def is_within_roots(path: Path) -> bool:
    """
    Security check to ensure file operations remain within the designated workspace.
    
    Args:
        path: The target filesystem path to validate.
        
    Returns:
        bool: True if the path is safely within BASE_DIR, False otherwise.
    """
    try:
        # Ensure we're comparing absolute, resolved paths to prevent directory traversal
        return path.resolve().is_relative_to(BASE_DIR.resolve())
    except (ValueError, RuntimeError):
        return False

@mcp.tool()
def read_file(filepath: str) -> str:
    """
    Reads the content of a specific file from the workspace.
    
    Args:
        filepath: Relative path to the file within the workspace.
        
    Returns:
        str: File content or an error message if access is denied or file missing.
    """
    path = BASE_DIR / filepath
    if not is_within_roots(path):
        logger.warning(f"Unauthorized access attempt: {filepath}")
        return "Error: Access denied - path must be within workspace roots"
    
    if not path.exists():
        return f"Error: File not found: {filepath}"
    
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to read {filepath}: {e}")
        return f"Error reading file: {str(e)}"

@mcp.tool()
def write_file(filepath: str, content: str) -> str:
    """
    Writes or overwrites content to a file within the workspace.
    
    Args:
        filepath: Relative path where the file should be written.
        content: The text content to write.
        
    Returns:
        str: Success message with character count or error message.
    """
    path = BASE_DIR / filepath
    if not is_within_roots(path):
        logger.warning(f"Unauthorized write attempt: {filepath}")
        return "Error: Access denied - path must be within workspace roots"
    
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        logger.info(f"File written successfully: {filepath}")
        return f"Successfully wrote {len(content)} characters to {filepath}"
    except Exception as e:
        logger.error(f"Failed to write {filepath}: {e}")
        return f"Error writing file: {str(e)}"

@mcp.tool()
def list_files(directory: str = ".") -> str:
    """
    Lists all files and directories in a specified workspace subdirectory.
    
    Args:
        directory: Relative path of the directory to list. Defaults to root.
        
    Returns:
        str: Formatted list of items with metadata or error message.
    """
    path = BASE_DIR / directory
    if not is_within_roots(path):
        return "Error: Access denied - path must be within workspace roots"
    
    if not path.exists():
        return f"Error: Directory not found: {directory}"
    if not path.is_dir():
        return f"Error: Path is not a directory: {directory}"
    
    try:
        items = []
        for item in sorted(path.iterdir()):
            rel_path = item.relative_to(BASE_DIR)
            tag = "[DIR] " if item.is_dir() else "[FILE]"
            size = item.stat().st_size if item.is_file() else 0
            items.append(f"{tag} {rel_path} ({size} bytes)")
        
        return "\n".join(items) if items else "Directory is empty"
    except Exception as e:
        logger.error(f"Failed to list directory {directory}: {e}")
        return f"Error listing directory: {str(e)}"

@mcp.tool()
def analyze_code(code: str, focus: str = "quality") -> str:
    """
    Simulates a complex code analysis that would trigger an MCP sampling request.
    
    Note: Full bidirectional sampling requires the low-level MCP SDK. 
    This tool serves as an educational bridge demonstrating the pattern.
    
    Args:
        code: The source code to analyze.
        focus: The primary aspect of analysis (e.g., 'quality', 'security', 'performance').
        
    Returns:
        str: A detailed simulation of the sampling orchestration flow.
    """
    snippet = code[:50].replace('\n', ' ') + "..." if len(code) > 50 else code
    return f"""[MCP SAMPLING ORCHESTRATION]
The server would now initiate a 'sampling/createMessage' request to the host:

{{
  "method": "sampling/createMessage",
  "params": {{
    "messages": [
      {{
        "role": "user",
        "content": {{
          "type": "text",
          "text": "As an expert developer, perform a {focus} analysis on this snippet:\\n\\n{snippet}"
        }}
      }}
    ],
    "maxTokens": 1000,
    "modelPreferences": {{ "hints": [{{ "name": "gpt-4o" }}] }}
  }}
}}

The Host Workflow:
1. User receives a prompt to approve tool-initiated sampling.
2. If approved, the Host forwards the request to its connected LLM.
3. The result is returned to this server tool to complete the final report.
"""

@mcp.resource("file://workspace/{filename}")
def get_workspace_file(filename: str) -> str:
    """
    Exposes workspace files as MCP resources for LLM context injection.
    
    Args:
        filename: Name of the file to retrieve.
        
    Returns:
        str: Raw file content.
    """
    path = BASE_DIR / filename
    if not is_within_roots(path):
        raise ValueError(f"Security error: Path outside workspace bounds")
    if not path.exists():
        raise FileNotFoundError(f"Resource not found: {filename}")
    return path.read_text(encoding="utf-8")

@mcp.prompt()
def review_code(filename: str) -> str:
    """
    Creates a standardized code review prompt template.
    
    Args:
        filename: The file targeted for review.
    """
    return f"""You are a Senior Principal Engineer. Review '{filename}' for:
1. Architectural soundness and pattern consistency.
2. Logic bugs and edge-case handling.
3. Security vulnerabilities (OWASP Top 10).
4. Performance bottlenecks.
5. Documentation completeness.

Provide a structured report with 'Immediate Actions' and 'Long-term Improvements'."""

@mcp.prompt()
def analyze_security(filename: str) -> str:
    """
    Creates a specialized security audit prompt template.
    
    Args:
        filename: The file targeted for security analysis.
    """
    return f"""Perform an intensive security audit on '{filename}'. 
Identify:
- Injection points (SQL, OS, Command).
- Broken Access Control.
- Cryptographic failures.
- Insecure design patterns.

Format your output as a vulnerability table with Severity, Description, and Remediation."""

if __name__ == "__main__":
    logger.info(f"Initializing MCP Server on http://127.0.0.1:8000")
    logger.info(f"Workspace path: {BASE_DIR}")
    mcp.run(transport="http", host="127.0.0.1", port=8000)
