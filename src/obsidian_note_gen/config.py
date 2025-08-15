"""Simple config loader/saver."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .core import DEFAULT_API_URL, DEFAULT_NOTES_DIR, Delays


CONFIG_PATH = Path("~/.config/obsidian-note-gen/config.json").expanduser()


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text("utf-8"))
            return {
                "api_url": data.get("api_url", DEFAULT_API_URL),
                "notes_dir": data.get("notes_dir", DEFAULT_NOTES_DIR),
                "delay_meta_content": int(data.get("delay_meta_content", Delays().meta_to_content)),
                "delay_between_rows": int(data.get("delay_between_rows", Delays().between_rows)),
            }
        except Exception:
            pass
    return {
        "api_url": DEFAULT_API_URL,
        "notes_dir": DEFAULT_NOTES_DIR,
        "delay_meta_content": Delays().meta_to_content,
        "delay_between_rows": Delays().between_rows,
    }


def save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), "utf-8")


__all__ = ["load_config", "save_config", "CONFIG_PATH"]

