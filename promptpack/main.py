#!/usr/bin/env python3
"""
Main script for the PromptPack CLI application.

Existing modes:
- --mode list : lists filtered files
- --mode copy : copies them into one text block for ChatGPT
New modes:
- --mode parse : parse XML-like <files> structure from the clipboard, display discovered files
- --mode write : parse the same structure and write files to disk
"""

import os
import sys
import re
import argparse
import pyperclip
from pathlib import Path
import json

from promptpack.config import load_config
import openai

##############################
# Existing scanning logic
##############################
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="PromptPack CLI: Automate code blocks for ChatGPT, plus parse them back into files."
    )
    parser.add_argument(
        "--env",
        default=".env",
        help="Path to the .env file (default .env in current directory)."
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=["list", "copy", "parse", "write"],
        help="Run mode: 'list', 'copy', 'parse', or 'write'. NOTE: 'parse' and 'write' modes are experimental."
    )
    return parser.parse_args()


def match_any(patterns, text):
    """Returns True if 'text' matches at least one of the given regex patterns."""
    return any(re.search(p, text) for p in patterns)


def is_accepted_folder(basename, deny_list, accept_list):
    if match_any(deny_list, basename):
        return False
    return match_any(accept_list, basename)


def is_accepted_file(basename, deny_list, accept_list):
    if match_any(deny_list, basename):
        return False
    return match_any(accept_list, basename)


def walk_and_filter(folder_path, folder_deny_list, folder_accept_list, file_deny_list, file_accept_list):
    folder_basename = folder_path.name
    if not is_accepted_folder(folder_basename, folder_deny_list, folder_accept_list):
        return []

    result_files = []
    try:
        with os.scandir(folder_path) as entries:
            for entry in entries:
                if entry.is_dir():
                    sub_path = Path(entry.path)
                    result_files.extend(
                        walk_and_filter(
                            sub_path,
                            folder_deny_list,
                            folder_accept_list,
                            file_deny_list,
                            file_accept_list
                        )
                    )
                elif entry.is_file():
                    if is_accepted_file(entry.name, file_deny_list, file_accept_list):
                        result_files.append(Path(entry.path))
    except PermissionError:
        print(f"[WARN] Permission denied: {folder_path}", file=sys.stderr)

    return result_files


def scan_folders_recursively(
    folders,
    folder_deny_list,
    folder_accept_list,
    file_deny_list,
    file_accept_list
):
    accepted_files = []
    for folder in folders:
        root_path = Path(folder).resolve()
        if not root_path.is_dir():
            print(f"[WARN] Path '{folder}' is not a directory. Skipping.", file=sys.stderr)
            continue

        files_in_this_root = walk_and_filter(
            root_path,
            folder_deny_list,
            folder_accept_list,
            file_deny_list,
            file_accept_list
        )
        for fpath in files_in_this_root:
            accepted_files.append((root_path, fpath))
    return accepted_files


def build_copy_output(accepted_file_tuples, max_file_size, lang_mapping):
    output_lines = []
    for root_folder, file_path in accepted_file_tuples:
        try:
            rel_path = file_path.relative_to(root_folder)
        except ValueError:
            rel_path = file_path

        rel_str = rel_path.as_posix()

        output_lines.append(f"{rel_str}:")
        output_lines.append("")

        extension = file_path.suffix.lstrip(".").lower()
        lang = lang_mapping.get(extension, "")

        if lang:
            output_lines.append(f"```{lang}")
        else:
            output_lines.append("```")

        try:
            file_size = file_path.stat().st_size
            if max_file_size is not None and file_size > max_file_size:
                output_lines.append("# [File too large, skipping content]")
            else:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                output_lines.append(content)
        except Exception as e:
            output_lines.append(f"# [Error reading file: {e}]")

        output_lines.append("```")
        output_lines.append("")

    return "\n".join(output_lines)


##############################
# New "parse" + "write" logic
##############################

PARSE_FILES_FROM_CLIPBOARD_PROMPT = """Task:

1. Analyze the entire text provided (it may include markdown snippets, directory trees, code blocks, file descriptions, etc.).
2. Identify all files mentioned (along with any subfolders). If any files are nested within folders, include the folder hierarchy in their paths (for example, "promptpack/main.py", "promptpack/config.py", etc.).
3. Try to discover all files mentioned in the text.
4. For each discovered file, determine:
   - **the full path** (relative path from the base directory, as shown in the project structure)
   - **the file content** (the code or text found within the ```...``` blocks or relevant sections)
5. Return all this information in **one JSON object**, containing:
   - a `"files"` key with an **array** of objects,
   - each object in that array having the keys `"path"` and `"content"`.
6. Remove formatting characters such as triple backticks (```) from the beginning and end of the file contents; ensure the content is an exact copy of the text in the corresponding block.
7. Do not provide any additional information beyond the JSON output. Do not include explanations, summaries, or any text outside the `"files"` key.
8. If you cannot find any files, return an empty array.

### Example JSON Structure

```json
{{
  "files": [
    {{
      "path": "promptpack/__init__.py",
      "content": "# This file can remain empty or contain package-wide imports.\n"
    }},
    {{
      "path": "README.md",
      "content": "# PromptPack (Enhanced Parsing & Optional HTML Decode)\n..."
    }}
  ]
}}
```

(This is just an example structure; the actual number of files and values should match your analysis.)

Return the result **exactly in this JSON format**—with no extra text before or after it.

Here is the text to analyze:
{text_to_analyze}
"""


def parse_files_from_clipboard() -> list[tuple[str, str]]:
    text = pyperclip.paste().strip()
    if not text:
        raise ValueError("Clipboard is empty")
    
    prompt = PARSE_FILES_FROM_CLIPBOARD_PROMPT.format(text_to_analyze=text)
    response = openai.chat.completions.create(
        model=os.environ["OPENAI_MODEL"],
        messages=[
            {"role": "user", "content": prompt}
        ],
    )
    json_str = response.choices[0].message.content.strip()
    if json_str.startswith("```json"):
        json_str = json_str[len("```json"):].strip()
    if json_str.endswith("```"):
        json_str = json_str[:-len("```")].strip()
    if json_str.startswith("```"):
        json_str = json_str[len("```"):].strip()
    print(json_str)
    json_obj = json.loads(json_str)
    return [(f["path"], f["content"]) for f in json_obj["files"]]


def mode_parse():
    """
    1. parse clipboard
    2. show discovered files (paths + partial preview of content)
    """
    file_entries = parse_files_from_clipboard()
    if not file_entries:
        print("[INFO] No file entries found or parsing error.")
        return

    print("[INFO] Found the following files in clipboard structure:\n")
    for idx, (path_str, content_str) in enumerate(file_entries, start=1):
        preview = content_str.splitlines()[:3]  # take first 3 lines as a preview
        preview_text = "\n".join(preview)
        print(f"File #{idx}: {path_str}")
        print(f"--- content preview ---\n{preview_text}\n-----------------------\n")


def mode_write(write_base_folder):
    """
    1. parse clipboard
    2. write files to `write_base_folder + path_str`
    """
    file_entries = parse_files_from_clipboard()
    if not file_entries:
        print("[INFO] No file entries found or parsing error.")
        return

    base_path = Path(write_base_folder).resolve()
    print(f"[INFO] Writing files under: {base_path}")

    for idx, (path_str, content_str) in enumerate(file_entries, start=1):
        target = base_path / Path(path_str)
        # ensure parent dirs exist
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(target, "w", encoding="utf-8", errors="replace") as f:
                f.write(content_str)
            print(f"[INFO] Wrote File #{idx}: {target}")
        except Exception as e:
            print(f"[ERROR] Failed to write {target}: {e}", file=sys.stderr)


##############################
# main()
##############################
def main():
    args = parse_arguments()
    config = {}
    try:
        config = load_config(args.env)
    except Exception as e:
        print(f"[ERROR] Failed to load configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Unpack needed settings
    folders_to_scan = config["folders_to_scan"]
    folder_deny_list = config["folder_deny_list"]
    folder_accept_list = config["folder_accept_list"]
    file_deny_list = config["file_deny_list"]
    file_accept_list = config["file_accept_list"]
    lang_mapping = config["lang_mapping"]
    max_file_size = config["max_file_size"]
    write_base_folder = config["write_base_folder"]

    mode = args.mode

    if mode == "list":
        # existing logic
        accepted_files = scan_folders_recursively(
            folders_to_scan,
            folder_deny_list,
            folder_accept_list,
            file_deny_list,
            file_accept_list
        )
        for (root_folder, file_path) in accepted_files:
            try:
                rel_path = file_path.relative_to(root_folder)
            except ValueError:
                rel_path = file_path
            print(rel_path.as_posix())
        sys.exit(0)

    elif mode == "copy":
        # existing logic
        accepted_files = scan_folders_recursively(
            folders_to_scan,
            folder_deny_list,
            folder_accept_list,
            file_deny_list,
            file_accept_list
        )
        final_output = build_copy_output(accepted_files, max_file_size, lang_mapping)
        try:
            pyperclip.copy(final_output)
            print("[INFO] The result block has been copied to the clipboard.")
        except Exception as e:
            print(f"[ERROR] Failed to copy to clipboard: {e}", file=sys.stderr)
            print("[INFO] Printing output to stdout instead:\n")
            print(final_output)
            sys.exit(1)
        sys.exit(0)

    elif mode == "parse":
        # new parse logic
        mode_parse()
        sys.exit(0)

    elif mode == "write":
        # new write logic
        mode_write(write_base_folder)
        sys.exit(0)

    else:
        print(f"[ERROR] Unknown mode: {mode}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
