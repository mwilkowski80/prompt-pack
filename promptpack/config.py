"""
Module to load configuration from a .env file.

Returns a dict with:
- folders_to_scan (list[str])  # Used by 'list'/'copy' modes
- folder_deny_list (list[str])
- folder_accept_list (list[str])
- file_deny_list (list[str])
- file_accept_list (list[str])
- lang_mapping (dict[str, str])
- max_file_size (int or None)
- write_base_folder (str) => base folder for 'write' mode
"""

import os
from dotenv import load_dotenv

def load_config(env_path: str) -> dict:
    load_dotenv(env_path)

    # FOLDERS_TO_SCAN (for 'list'/'copy')
    folders_str = os.getenv("FOLDERS_TO_SCAN", "")
    folders_to_scan = [f.strip() for f in folders_str.split(",") if f.strip()]

    # Folder deny/accept
    folder_deny_list = []
    folder_accept_list = []
    for key, value in os.environ.items():
        if key.startswith("FOLDER_DENY_REGEX_"):
            val = value.strip()
            if val:
                folder_deny_list.append(val)
        if key.startswith("FOLDER_ACCEPT_REGEX_"):
            val = value.strip()
            if val:
                folder_accept_list.append(val)

    # File deny/accept
    file_deny_list = []
    file_accept_list = []
    for key, value in os.environ.items():
        if key.startswith("FILE_DENY_REGEX_"):
            val = value.strip()
            if val:
                file_deny_list.append(val)
        if key.startswith("FILE_ACCEPT_REGEX_"):
            val = value.strip()
            if val:
                file_accept_list.append(val)

    # LANG_MAPPING
    lang_mapping_str = os.getenv("LANG_MAPPING", "").strip()
    lang_mapping = {}
    if lang_mapping_str:
        pairs = [p.strip() for p in lang_mapping_str.split(",")]
        for pair in pairs:
            if "=" in pair:
                ext, lang = pair.split("=", 1)
                ext = ext.strip().lower()
                lang = lang.strip()
                lang_mapping[ext] = lang

    # MAX_FILE_SIZE
    max_file_size_str = os.getenv("MAX_FILE_SIZE", "").strip()
    if max_file_size_str.isdigit():
        max_file_size = int(max_file_size_str)
    else:
        max_file_size = None

    # WRITE_BASE_FOLDER
    write_base_folder = os.getenv("WRITE_BASE_FOLDER", ".").strip()

    return {
        "folders_to_scan": folders_to_scan,
        "folder_deny_list": folder_deny_list,
        "folder_accept_list": folder_accept_list,
        "file_deny_list": file_deny_list,
        "file_accept_list": file_accept_list,
        "lang_mapping": lang_mapping,
        "max_file_size": max_file_size,
        "write_base_folder": write_base_folder,
    }
