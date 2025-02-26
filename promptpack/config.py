"""
Loads configuration from .env.

Returns a dict with:
- folders_to_scan
- folder_deny_list
- folder_accept_list
- file_deny_list
- file_accept_list
- lang_mapping
- max_file_size
- write_base_folder
- copy_template_file (for Jinja2)
- openai_model (used by parse/write)
"""

import os
from dotenv import load_dotenv

def load_config(env_path: str) -> dict:
    if not os.path.exists(env_path):
        raise FileNotFoundError(f"Configuration file '{env_path}' not found")

    if not load_dotenv(env_path):
        raise Exception(f"Failed to load environment variables from '{env_path}'")

    folders_str = os.getenv("FOLDERS_TO_SCAN", "")
    folders_to_scan = [f.strip() for f in folders_str.split(",") if f.strip()]

    folder_deny_list = []
    folder_accept_list = []
    file_deny_list = []
    file_accept_list = []

    for key, value in os.environ.items():
        val = value.strip()
        if key.startswith("FOLDER_DENY_REGEX_"):
            folder_deny_list.append(val)
        if key.startswith("FOLDER_ACCEPT_REGEX_"):
            folder_accept_list.append(val)
        if key.startswith("FILE_DENY_REGEX_"):
            file_deny_list.append(val)
        if key.startswith("FILE_ACCEPT_REGEX_"):
            file_accept_list.append(val)

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

    max_file_size_str = os.getenv("MAX_FILE_SIZE", "").strip()
    if max_file_size_str.isdigit():
        max_file_size = int(max_file_size_str)
    else:
        max_file_size = None

    write_base_folder = os.getenv("WRITE_BASE_FOLDER", ".").strip()
    copy_template_file = os.getenv("COPY_TEMPLATE_FILE", "").strip()

    openai_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo").strip()
    # you might also want OPENAI_API_KEY, etc.

    return {
        "folders_to_scan": folders_to_scan,
        "folder_deny_list": folder_deny_list,
        "folder_accept_list": folder_accept_list,
        "file_deny_list": file_deny_list,
        "file_accept_list": file_accept_list,
        "lang_mapping": lang_mapping,
        "max_file_size": max_file_size,
        "write_base_folder": write_base_folder,
        "copy_template_file": copy_template_file,
        "openai_model": openai_model,
    }
