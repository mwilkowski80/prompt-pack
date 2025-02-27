# Prompt Pack: Streamlined Code-Sharing for ChatGPT

**Quick Summary**  
`prompt-pack` is a Python CLI tool that **recursively scans your project files**, applies flexible accept/deny filters, and bundles the selected files into a well-formatted text block which is **copied to your clipboard**. This text block can then be **pasted** directly into ChatGPT (or other AI platforms) when you want the AI to review or modify your code.

## 1. Why Use Prompt-Pack?

### 1.1. Automate Code Sharing with ChatGPT
If you’ve ever tried to share multiple files with ChatGPT for debugging or refactoring, you know how **tedious** it can be to manually copy dozens of files, rename them, and ensure proper formatting with backticks. `prompt-pack` **automates** this process:

- **Recursively** crawls your project directories,
- **Filters out** files or folders you don’t want (e.g., logs, temporary folders, large files),
- **Generates** a single text block with the selected files neatly labeled,
- **Copies** the entire block to your clipboard with proper triple-backtick formatting.

With one command, you can **paste** a clean, organized codebase into ChatGPT for review or suggestions.

### 1.2. Save Time & Reduce Errors
Manually copying file contents is prone to **mistakes** and **inconsistencies** (missing files, wrong versions, or forgetting a bracket). Using `prompt-pack`:

- Ensures **consistent** naming and structure,
- Prevents accidental inclusion of sensitive or irrelevant files,
- Keeps your prompt well-structured so ChatGPT can parse each file correctly.

### 1.3. Flexible Configuration
`prompt-pack` is controlled by a `.env` file, where you can define:
- Which **folders** to scan,
- Which **files** to accept or deny with **regex** patterns,
- **Language mappings** for syntax highlighting (e.g., `.py` → `python`),
- **Maximum file size** to avoid copying huge binaries.

By adjusting these settings, you can **finely tune** exactly what code gets packaged each time.

## 2. Key Features

- **Recursive Filtering**: Skip entire folder subtrees if they don’t match your folder accept/deny regex.  
- **File-Level Filtering**: Include/exclude files by extension, name patterns, or other regex rules.  
- **Clipboard Integration**: Automatically copy the final text to your system’s clipboard.  
- **Language Mappings**: Insert the right triple-backtick language hint (e.g., ```python) for ChatGPT code formatting.  
- **Easy Setup**: Install via `setup.py` or use `requirements.txt`.  
- **Cross-Platform**: Works on Linux, macOS, Windows (Python 3.7+ required; may need `xclip` on Linux).

## 3. Installation

### Option A: Using `setup.py`

1. Make sure you have Python 3.7+ installed.  
2. In the project directory (where `setup.py` is located), run:
   ```bash
   pip install .
   ```
3. Now you can use the command `prompt-pack` from anywhere in this environment.

### Option B: Using `requirements.txt`

1. (Optional) create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the CLI directly:
   ```bash
   python promptpack/main.py --env .env --mode list
   ```
   or
   ```bash
   python promptpack/main.py --env .env --mode copy
   ```

## 4. Configuration

`prompt-pack` reads a `.env` file, for example:

```bash
FOLDERS_TO_SCAN="/my/codebase,/another/folder"

FOLDER_DENY_REGEX_1="^temp.*"
FOLDER_ACCEPT_REGEX_1=".*"

FILE_DENY_REGEX_1=".*\\.log$"
FILE_ACCEPT_REGEX_1=".*\\.py$"
FILE_ACCEPT_REGEX_2=".*\\.txt$"

LANG_MAPPING="py=python,js=javascript"
MAX_FILE_SIZE="500000"
```

- **FOLDERS_TO_SCAN**: comma-separated list of base folders.  
- **FOLDER_DENY_REGEX_*** / **FOLDER_ACCEPT_REGEX_***: which folders to skip or include.  
- **FILE_DENY_REGEX_*** / **FILE_ACCEPT_REGEX_***: which files to skip or include.  
- **LANG_MAPPING**: associate file extensions with code languages (`py=python`).  
- **MAX_FILE_SIZE**: ignore or limit oversized files.

## 5. Usage

After installing and configuring:

1. **list mode** – enumerates the final set of files:
   ```bash
   prompt-pack --env .env --mode list
   ```
   Output might look like:
   ```
   main.py
   utils/helpers.py
   ...
   ```
2. **copy mode** – copies all accepted files into a single prompt-friendly text block:
   ```bash
   prompt-pack --env .env --mode copy
   ```
   - Each file is labeled and wrapped in triple backticks:
     ```
     main.py:

     ```python
     # content of main.py
     ```
     
     ```
   - The entire block is placed on your clipboard.

## 6. Typical Workflow with ChatGPT

1. **Configure** your `.env` once (indicate which folders & files you want to share).  
2. **Run** `prompt-pack --mode copy`.  
3. **Go to ChatGPT** (or another AI tool), paste the resulting prompt:
   - Your files each have their own fenced code block, making it easy for GPT to parse them.  
4. **Ask** ChatGPT for improvements, fixes, or refactoring.  
5. **Profit** from GPT’s suggestions without manual copy/paste hassles!

## 7. Example Scenarios

- **Refactoring a Python Project**: Accept all `.py` files, ignore logs, large data, or virtual environment folders.  
- **Sharing Partial Code**: Deny certain sensitive files or large binaries via deny regex.  
- **Multi-Language Repos**: Use `LANG_MAPPING` to properly highlight `.js`, `.py`, `.ts`, etc.

## 8. Troubleshooting

- If copying to clipboard fails on Linux, ensure `xclip` or `xsel` is installed, or check `pyperclip` docs.  
- If a file is too large, a placeholder (`# [File too large, skipping content]`) is inserted.  
- For very large codebases, you might exceed ChatGPT input limits – refine your accept/deny filters accordingly.

## 9. Using Prompt-Pack as an MCP Server

Prompt-Pack can be used as an MCP server, allowing direct integration with MCP-compatible AI clients like Claude Desktop, Cursor, and more.

### 9.1. Setup with MCP

1. Make sure you have `uv` installed (a fast Python package installer and resolver)
2. Configure your MCP client (like Claude Desktop) with the following settings:

```json
{
  "mcpServers": {
      "prompt-pack": {
         "command": "uv",
         "args": ["run", "<local_dir_path>/prompt-pack/mcp-server/mcp_server.py"]
      }
  }
}
```

Replace `<local_dir_path>` with the actual path to your prompt-pack installation.

### 9.2. MCP Tools

When configured, your AI assistant will have access to these tools:

- **bundle_code**: Bundles source code files from a specified directory using the same powerful filtering capabilities as the CLI
- **list_files**: Lists files in a directory using specified filter patterns

### 9.3. Example Usage with Cursor

1. Configure the MCP server in Cursor settings: Settings -> MCP -> Add new MCP Server
2. Select `command` type and provide the following command:

```
uv run <local_dir_path>/prompt-pack/mcp-server/mcp_server.py
```

3. Replace `<local_dir_path>` with the actual path to your prompt-pack installation.

Once configured, you can ask your AI assistant in agent mode to:

1. List files in a directory: "Using prompt pack tool list out all adoc files in the current project"
2. Bundle code for analysis: "Use prompt-pack mcp server tool to review all Rest Controller classes and generate list of available API endpoints"

The AI will use the MCP tools to access your files directly, with the same powerful filtering capabilities as the CLI version.

## 10. License

You can freely use or modify `prompt-pack`. Contributions are welcome!
