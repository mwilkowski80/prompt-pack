#!/usr/bin/env python3
"""
Main script for the CLI application.

Example usage:
  prompt-pack --env .env --mode list
  prompt-pack --env .env --mode copy
"""

import os
import sys
import re
import argparse
import pyperclip
from pathlib import Path

# Import load_config from the config module within the same package
from promptpack.config import load_config

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="CLI application to recursively scan folders/files, using separate folder/file regex filters."
    )
    parser.add_argument(
        "--env",
        default=".env",
        help="Path to the .env file (default: .env in the current directory)."
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=["list", "copy"],
        help="Run mode: 'list' (print accepted files) or 'copy' (copy them in a single block to the clipboard)."
    )
    return parser.parse_args()


def match_any(patterns, text):
    """Returns True if 'text' matches at least one of the given regex patterns."""
    return any(re.search(p, text) for p in patterns)


def is_accepted_folder(basename, deny_list, accept_list):
    """
    Returns True if:
      1) The folder name does NOT match any folder-deny pattern,
      2) The folder name DOES match at least one folder-accept pattern.
    """
    if match_any(deny_list, basename):
        return False
    return match_any(accept_list, basename)


def is_accepted_file(basename, deny_list, accept_list):
    """
    Returns True if:
      1) The file name does NOT match any file-deny pattern,
      2) The file name DOES match at least one file-accept pattern.
    """
    if match_any(deny_list, basename):
        return False
    return match_any(accept_list, basename)


def walk_and_filter(
    folder_path,
    folder_deny_list,
    folder_accept_list,
    file_deny_list,
    file_accept_list
):
    """
    Recursively scans the given folder:
      - First, check if the folder is accepted (folder basename).
        * If denied or not accepted, return an empty list (do not descend).
      - If the folder is accepted, iterate over its entries:
        * For each subfolder: call walk_and_filter(...) recursively.
        * For each file: check file-level filters. If accepted, add to results.

    Returns a list of Paths to accepted files (no directories).
    """
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
                # if it's a symlink or something else, skip or handle differently
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
    """
    For each path in 'folders':
      - it must be a directory,
      - we recursively scan it (if the folder passes folder-level filters).

    We return a list of (root_folder, file_path) tuples, so we can later strip
    the root folder name from the displayed path.
    """
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
            # Store (root_path, fpath)
            accepted_files.append((root_path, fpath))

    return accepted_files


def build_copy_output(accepted_file_tuples, max_file_size, lang_mapping):
    """
    Build a single text block. 'accepted_file_tuples' is a list of (root_folder, file_path).

    The displayed path: we strip the root_folder from file_path using .relative_to(root_folder).
    Example:
      root_folder = /storage/forensics
      file_path   = /storage/forensics/requirements.txt
      => displayed path is 'requirements.txt'

    If the file is deeper, e.g. /storage/forensics/s8forensics/__init__.py
    => displayed path is 's8forensics/__init__.py'
    """
    output_lines = []
    for root_folder, file_path in accepted_file_tuples:
        try:
            rel_path = file_path.relative_to(root_folder)
        except ValueError:
            # Fallback if it fails
            rel_path = file_path

        rel_str = rel_path.as_posix()

        # Print the file name line, then a blank line
        output_lines.append(f"{rel_str}:")
        output_lines.append("")

        # Determine language from extension
        extension = file_path.suffix.lstrip(".").lower()
        lang = lang_mapping.get(extension, "")

        if lang:
            output_lines.append(f"```{lang}")
        else:
            output_lines.append("```")

        # Check file size / read content
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
        output_lines.append("")  # blank line after block

    return "\n".join(output_lines)


def main():
    args = parse_arguments()

    # 1. Load configuration
    try:
        config = load_config(args.env)
    except Exception as e:
        print(f"[ERROR] Failed to load configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Unpack settings
    folders_to_scan = config["folders_to_scan"]
    folder_deny_list = config["folder_deny_list"]
    folder_accept_list = config["folder_accept_list"]
    file_deny_list = config["file_deny_list"]
    file_accept_list = config["file_accept_list"]
    lang_mapping = config["lang_mapping"]
    max_file_size = config["max_file_size"]

    # 2. Recursively scan
    accepted_files = scan_folders_recursively(
        folders_to_scan,
        folder_deny_list,
        folder_accept_list,
        file_deny_list,
        file_accept_list
    )
    # accepted_files => list of (root_folder, file_path)

    # 3. Mode
    if args.mode == "list":
        for (root_folder, file_path) in accepted_files:
            try:
                rel_path = file_path.relative_to(root_folder)
            except ValueError:
                rel_path = file_path
            print(rel_path.as_posix())
        sys.exit(0)

    elif args.mode == "copy":
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


if __name__ == "__main__":
    main()
