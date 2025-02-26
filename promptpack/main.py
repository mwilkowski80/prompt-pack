#!/usr/bin/env python3
"""
Main script for the PromptPack CLI application.

Modes:
- list   : lists filtered files
- copy   : copies them into a single text block via Jinja2
- parse  : uses OpenAI to parse a snippet from the clipboard, extracting files
- write  : writes those parsed files to disk
"""

import os
import sys
import re
import json
import argparse
import pyperclip
import openai
from pathlib import Path
from importlib import resources

from jinja2 import Template

from promptpack.config import load_config

#########################
# Step 1: parse arguments
#########################
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="PromptPack CLI: Filtered code listing & Jinja2 copy, plus parse/write from OpenAI snippet."
    )
    parser.add_argument(
        "--env",
        default=".env",
        help="Path to the .env file (default: .env in the current directory)."
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=["list", "copy", "parse", "write"],
        help="Which mode to run: list, copy, parse, or write."
    )
    return parser.parse_args()

#########################
# Step 2: Filter logic (list/copy)
#########################
def match_any(patterns, text):
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

#########################
# Step 3: Jinja2-based 'copy' mode
#########################
def prepare_files_list(accepted_file_tuples, lang_mapping, max_file_size):
    """
    Convert accepted_file_tuples -> list of dicts for Jinja2.
    Each dict: index, absolute_filepath, relative_filepath, filename, language, content
    """
    files_data = []
    for i, (root_folder, file_path) in enumerate(accepted_file_tuples, start=1):
        try:
            rel_path = file_path.relative_to(root_folder)
        except ValueError:
            rel_path = file_path

        relative_str = rel_path.as_posix()
        absolute_str = str(file_path.resolve())
        filename = file_path.name

        extension = file_path.suffix.lstrip(".").lower()
        language = lang_mapping.get(extension, "")

        # read content or placeholder
        content = ""
        try:
            file_size = file_path.stat().st_size
            if max_file_size is not None and file_size > max_file_size:
                content = "# [File too large, skipping content]"
            else:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
        except Exception as e:
            content = f"# [Error reading file: {e}]"

        files_data.append({
            "index": i,
            "absolute_filepath": absolute_str,
            "relative_filepath": relative_str,
            "filename": filename,
            "language": language,
            "content": content,
        })
    return files_data

def run_copy_mode(accepted_files, config):
    files_data = prepare_files_list(
        accepted_files,
        config["lang_mapping"],
        config["max_file_size"]
    )

    template_path = config["copy_template_file"]
    template_str = ""
    if template_path:
        # If user specified a path, try to load
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                template_str = f.read()
        else:
            print(f"[WARN] Template file '{template_path}' not found. Using default.")
    if not template_str:
        # Use default template from package resources
        template_str = resources.read_text('promptpack', 'default_copy_template.j2')

    jinja_template = Template(template_str)
    context = {
        "files": files_data
    }
    output_text = jinja_template.render(context)
    pyperclip.copy(output_text)
    print("[INFO] The Jinja2-rendered text block has been copied to the clipboard.")

#########################
# Step 4: parse/write (OpenAI-based)
#########################

# 4.1) Prompt for parse
PARSE_FILES_FROM_CLIPBOARD_PROMPT = """Task:

1. Analyze the entire text provided (it may include markdown, code blocks, file paths, etc.).
2. Identify all files mentioned. For each file, determine:
   - "path" => relative path
   - "content" => content of the file
3. Return everything in one JSON with a "files" key (an array), each entry = {"path": "...", "content": "..."}.
4. No extra text outside the JSON. 
5. If none found, return {"files": []}.

Here is the text to analyze:
{text_to_analyze}
"""

def parse_files_from_clipboard(openai_model: str) -> list[tuple[str, str]]:
    """
    1. Grab text from clipboard
    2. Send to OpenAI with instructions to produce JSON
    3. Parse JSON => list of (path, content)
    """
    import pyperclip
    text = pyperclip.paste().strip()
    if not text:
        print("[ERROR] Clipboard is empty.")
        return []

    prompt = PARSE_FILES_FROM_CLIPBOARD_PROMPT.format(text_to_analyze=text)
    try:
        openai.api_key = os.environ["OPENAI_API_KEY"]  # or from config if needed
    except KeyError:
        print("[ERROR] Please set OPENAI_API_KEY in environment to use parse/write.")
        return []

    # Call the Chat Completion endpoint
    response = openai.ChatCompletion.create(
        model=openai_model,
        messages=[{"role": "user", "content": prompt}],
    )
    json_str = response.choices[0].message.content.strip()

    # Remove any possible triple backticks around json
    if json_str.startswith("```"):
        json_str = json_str.lstrip("```").strip()
    if json_str.endswith("```"):
        json_str = json_str[:-3].strip()

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to decode JSON: {e}")
        return []

    results = []
    files_array = data.get("files", [])
    for fobj in files_array:
        path_str = fobj.get("path", "").strip()
        content_str = fobj.get("content", "")
        results.append((path_str, content_str))
    return results

def mode_parse(openai_model: str):
    file_entries = parse_files_from_clipboard(openai_model)
    if not file_entries:
        print("[INFO] No file entries found or parse error.")
        return

    print("[INFO] Found the following files in clipboard structure:\n")
    for idx, (path_str, content_str) in enumerate(file_entries, start=1):
        preview = content_str.splitlines()[:3]
        preview_text = "\n".join(preview)
        print(f"File #{idx}: {path_str}")
        print(f"--- content preview ---\n{preview_text}\n-----------------------\n")

def mode_write(write_base_folder: str, openai_model: str):
    file_entries = parse_files_from_clipboard(openai_model)
    if not file_entries:
        print("[INFO] No file entries found or parse error.")
        return

    base_path = Path(write_base_folder).resolve()
    print(f"[INFO] Writing files under: {base_path}")

    for idx, (path_str, content_str) in enumerate(file_entries, start=1):
        target = base_path / Path(path_str)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(target, "w", encoding="utf-8", errors="replace") as f:
                f.write(content_str)
            print(f"[INFO] Wrote File #{idx}: {target}")
        except Exception as e:
            print(f"[ERROR] Failed to write {target}: {e}", file=sys.stderr)

#########################
# Step 5: main()
#########################
def main():
    args = parse_arguments()
    try:
        config = load_config(args.env)
    except Exception as e:
        print(f"[ERROR] Failed to load config: {e}", file=sys.stderr)
        sys.exit(1)

    folders_to_scan = config["folders_to_scan"]
    folder_deny_list = config["folder_deny_list"]
    folder_accept_list = config["folder_accept_list"]
    file_deny_list = config["file_deny_list"]
    file_accept_list = config["file_accept_list"]
    lang_mapping = config["lang_mapping"]
    max_file_size = config["max_file_size"]
    write_base_folder = config["write_base_folder"]
    copy_template_file = config["copy_template_file"]
    openai_model = config["openai_model"]  # for parse/write

    mode = args.mode

    if mode == "list":
        if not folders_to_scan:
            print("[ERROR] No FOLDERS_TO_SCAN set in .env.")
            sys.exit(1)
        accepted_files = scan_folders_recursively(
            folders_to_scan,
            folder_deny_list,
            folder_accept_list,
            file_deny_list,
            file_accept_list
        )
        if not accepted_files:
            print("[WARN] No files found matching filters.")
            sys.exit(0)
        for (root_folder, file_path) in accepted_files:
            try:
                rel_path = file_path.relative_to(root_folder)
            except ValueError:
                rel_path = file_path
            print(rel_path.as_posix())
        sys.exit(0)

    elif mode == "copy":
        if not folders_to_scan:
            print("[ERROR] No FOLDERS_TO_SCAN set in .env.")
            sys.exit(1)
        accepted_files = scan_folders_recursively(
            folders_to_scan,
            folder_deny_list,
            folder_accept_list,
            file_deny_list,
            file_accept_list
        )
        if not accepted_files:
            print("[WARN] No files found. Exiting.")
            sys.exit(0)
        run_copy_mode(accepted_files, config)
        sys.exit(0)

    elif mode == "parse":
        mode_parse(openai_model)
        sys.exit(0)

    elif mode == "write":
        mode_write(write_base_folder, openai_model)
        sys.exit(0)

    else:
        print(f"[ERROR] Unknown mode: {mode}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
