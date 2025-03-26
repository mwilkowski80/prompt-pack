#!/usr/bin/env python3
# /// script
# dependencies = [
#   "mcp==1.3.0",
#   "python-dotenv==1.0.0",
#   "pyperclip==1.8.2",
#   "Jinja2==3.1.2",
#   "openai==1.63.2"
# ]
# ///
"""
MCP Server for PromptPack

A lightweight MCP server that wraps around the existing prompt-pack CLI tool.
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Add parent directory to path so we can import promptpack
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from promptpack
from promptpack.main import (
    walk_and_filter,
    prepare_files_list,
    scan_folders_recursively,
)

# Import MCP
from mcp.server.fastmcp import FastMCP

# Default language mappings for syntax highlighting
DEFAULT_LANG_MAPPING = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "jsx": "jsx",
    "tsx": "tsx",
    "java": "java",
    "c": "c",
    "cpp": "cpp", 
    "h": "c",
    "hpp": "cpp",
    "rs": "rust",
    "go": "go",
    "rb": "ruby",
    "php": "php",
    "html": "html",
    "css": "css",
    "md": "markdown",
    "json": "json",
    "yaml": "yaml",
    "yml": "yaml",
    "sh": "bash",
    "bash": "bash",
    "zsh": "bash",
    "sql": "sql",
    "kt": "kotlin",
    "swift": "swift",
    "dart": "dart",
    "cs": "csharp",
    "fs": "fsharp",
    "ex": "elixir",
    "exs": "elixir",
    "erl": "erlang",
    "clj": "clojure",
    "scala": "scala",
    "hs": "haskell",
    "lua": "lua",
    "r": "r",
    "pl": "perl",
    "pm": "perl",
    "groovy": "groovy",
    "gradle": "gradle",
    "xml": "xml",
    "toml": "toml",
    "ini": "ini",
    "cfg": "ini",
    "conf": "ini",
    "dockerfile": "dockerfile",
    "tf": "terraform",
    "vue": "vue",
    "svelte": "svelte",
}

# Create MCP server
mcp = FastMCP("PromptPack MCP Server")

@mcp.tool()
def bundle_code(
    directory: str,
    max_file_size: int = 500000,
    folder_accept: List[str] = [".*"],
    folder_deny: List[str] = [
        r"^\.git$", 
        r"^\.github$", 
        r"^\.vscode$", 
        r"^\.idea$",
        r"^venv$",
        r"^\.venv$",
        r"^virtualenv$",
        r"^env$",
        r"^\.env$", 
        r"^node_modules$", 
        r"^dist$", 
        r"^build$", 
        r"^target$", 
        r"^out$", 
        r"^__pycache__$",
        r"^\.pytest_cache$",
        r"^\.mypy_cache$",
        r"^\.ruff_cache$",
        r"^\.tox$",
        r"^\.eggs$",
        r"^\.coverage$",
        r"^htmlcov$",
        r"^coverage$",
        r"^tmp$",
        r"^temp$",
        r"^logs$",
        r"^\.DS_Store$",
    ],
    file_accept: List[str] = [
        r".*\.(py|js|ts|jsx|tsx|java|c|cpp|h|hpp|rs|go|rb|php|html|css|md|json|yaml|yml|sh|bash|zsh|sql|kt|swift|dart|cs|fs|ex|exs|erl|clj|scala|hs|lua|r|pl|pm|groovy|gradle|xml|toml|ini|cfg|conf|dockerfile|tf|vue|svelte)$",
        r"^README.*$",
        r"^Makefile$",
        r"^Dockerfile$",
        r"^docker-compose\.yml$",
        r"^\.env\.example$",
        r"^requirements\.txt$",
        r"^package\.json$",
        r"^tsconfig\.json$",
        r"^setup\.py$",
        r"^pom\.xml$",
        r"^build\.gradle$",
        r"^Cargo\.toml$",
        r"^go\.mod$",
    ],
    file_deny: List[str] = [
        r".*\.(log|pyc|class|o|so|dll|exe|bin|dat|bak|swp|lock|sqlite|db|jar|war|ear|zip|tar|gz|rar|7z|jpg|jpeg|png|gif|bmp|svg|ico|mp3|mp4|avi|mkv|mov|flv|wmv|pdf|doc|docx|xls|xlsx|ppt|pptx)$",
        r".*\.min\.(js|css)$",
        r".*\.generated\..*$",
        r".*\.test\..*$",
        r".*\.spec\..*$",
    ],
    lang_mapping: Dict[str, str] = None,
) -> Dict[str, Any]:
    """
    Bundle source code files from specified directories into a single text blob for AI analysis.
    
    IMPORTANT: It's recommended to run the list_files tool first to understand what files are available
    and to help fine-tune the parameters for this tool.
    
    Args:
        directory: Absolute path to the directory containing code to analyze. It must be a valid path to a directory.
        max_file_size: Maximum file size in bytes to include (defaults to 500KB)
        folder_accept: Regex patterns for folders to include (a folder must match at least one pattern)
        folder_deny: Regex patterns for folders to exclude (a folder matching any pattern will be skipped)
        file_accept: Regex patterns for files to include (a file must match at least one pattern)
        file_deny: Regex patterns for files to exclude (a file matching any pattern will be skipped)
        lang_mapping: Custom language mappings for file extensions (defaults to a comprehensive set)
    """
    # Use default language mapping if not provided
    if lang_mapping is None:
        lang_mapping = DEFAULT_LANG_MAPPING
    
    # Convert directory to list
    folders_to_scan = [directory]
    
    # Use the existing prompt-pack functionality to scan folders
    accepted_files = scan_folders_recursively(
        folders_to_scan,
        folder_deny,
        folder_accept,
        file_deny,
        file_accept
    )
    
    if not accepted_files:
        return {"files": [], "bundled_text": "No files found matching the criteria."}
    
    # Prepare files list using the existing function
    files_data = prepare_files_list(
        accepted_files,
        lang_mapping,
        max_file_size
    )
    
    # Format the bundled text
    bundled_text = ""
    for file_data in files_data:
        bundled_text += f"File: {file_data['relative_filepath']}\n"
        bundled_text += "```" + (file_data["language"] or "text") + "\n"
        bundled_text += file_data["content"] + "\n"
        bundled_text += "```\n\n"
    
    return {
        "files": files_data,
        "bundled_text": bundled_text
    }

@mcp.tool()
def list_files(
    directory: str,
    folder_accept: List[str] = [".*"],
    folder_deny: List[str] = [
        r"^\.git$", 
        r"^\.github$", 
        r"^\.vscode$", 
        r"^\.idea$",
        r"^venv$",
        r"^\.venv$",
        r"^virtualenv$",
        r"^env$",
        r"^\.env$", 
        r"^node_modules$", 
        r"^dist$", 
        r"^build$", 
        r"^target$", 
        r"^out$", 
        r"^__pycache__$",
        r"^\.pytest_cache$",
        r"^\.mypy_cache$",
        r"^\.ruff_cache$",
        r"^\.tox$",
        r"^\.eggs$",
        r"^\.coverage$",
        r"^htmlcov$",
        r"^coverage$",
        r"^tmp$",
        r"^temp$",
        r"^logs$",
        r"^\.DS_Store$",
    ],
    file_accept: List[str] = [
        r".*\.(py|js|ts|jsx|tsx|java|c|cpp|h|hpp|rs|go|rb|php|html|css|md|json|yaml|yml|sh|bash|zsh|sql|kt|swift|dart|cs|fs|ex|exs|erl|clj|scala|hs|lua|r|pl|pm|groovy|gradle|xml|toml|ini|cfg|conf|dockerfile|tf|vue|svelte)$",
        r"^README.*$",
        r"^LICENSE.*$",
        r"^Makefile$",
        r"^Dockerfile$",
        r"^docker-compose\.yml$",
        r"^\.env\.example$",
        r"^requirements\.txt$",
        r"^package\.json$",
        r"^tsconfig\.json$",
        r"^setup\.py$",
        r"^pom\.xml$",
        r"^build\.gradle$",
        r"^Cargo\.toml$",
        r"^go\.mod$",
    ],
    file_deny: List[str] = [
        r".*\.(log|pyc|class|o|so|dll|exe|bin|dat|bak|swp|lock|sqlite|db|jar|war|ear|zip|tar|gz|rar|7z|jpg|jpeg|png|gif|bmp|svg|ico|mp3|mp4|avi|mkv|mov|flv|wmv|pdf|doc|docx|xls|xlsx|ppt|pptx)$",
        r".*\.min\.(js|css)$",
        r".*\.generated\..*$",
        r".*\.test\..*$",
        r".*\.spec\..*$",
    ],
) -> Dict[str, Any]:
    """
    List files in a directory using specified filter patterns.
    
    This tool is recommended to run FIRST before using bundle_code to understand what files are available
    and to help determine appropriate filter patterns.
    
    Args:
        directory: Absolute path to the directory to list. It must be a valid path to a directory.
        folder_accept: Regex patterns for folders to include (a folder must match at least one pattern)
        folder_deny: Regex patterns for folders to exclude (a folder matching any pattern will be skipped)
        file_accept: Regex patterns for files to include (a file must match at least one pattern)
        file_deny: Regex patterns for files to exclude (a file matching any pattern will be skipped)
    
    Returns:
        Dictionary with a "files" key containing a list of relative file paths that match the criteria
    """
    # Convert directory to list
    folders_to_scan = [directory]
    
    # Use the existing prompt-pack functionality to scan folders
    accepted_files = scan_folders_recursively(
        folders_to_scan,
        folder_deny,
        folder_accept,
        file_deny,
        file_accept
    )
    
    # Format the results
    file_paths = []
    for root_folder, file_path in accepted_files:
        try:
            rel_path = file_path.relative_to(root_folder)
        except ValueError:
            rel_path = file_path
        file_paths.append(rel_path.as_posix())
    
    return {
        "files": file_paths
    }

if __name__ == "__main__":
    mcp.run() 