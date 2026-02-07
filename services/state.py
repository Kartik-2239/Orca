from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any


@dataclass
class AppState:
    last_folder_path: str
    last_page: str = "home"
    theme: str = "Light"
    window_size: list[int] | None = None
    window_pos: list[int] | None = None
    filename_template: str = "%(title)s.%(ext)s"
    quality: str = "Best"
    resolution_cap: str = "No cap"
    codec_preference: str = "Any"
    output_container: str = "mp4"
    audio_only: bool = False
    format_selector: str = ""
    volume: int = 60
    muted: bool = False
    multi_files_enabled: bool = False
    multi_files_count: int = 5
    audio_dir: str | None = None
    pdf_open_files: list[str] = field(default_factory=list)
    last_image_open_dir: str | None = None
    last_image_export_dir: str | None = None
    ai_api_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any], default_folder: str) -> "AppState":
        state = cls(last_folder_path=default_folder)
        for key, value in data.items():
            if hasattr(state, key):
                setattr(state, key, value)
        return state


def load_state(path: Path, default_folder: str) -> AppState:
    try:
        if path.exists():
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                return AppState.from_dict(data, default_folder)
    except Exception:
        pass
    return AppState(last_folder_path=default_folder)


def save_state(path: Path, state: AppState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), indent=2))


def ensure_storage(storage_marker: Path, state_path: Path, default_folder: str) -> None:
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        if not state_path.exists():
            save_state(state_path, AppState(last_folder_path=default_folder))
        storage_marker.parent.mkdir(parents=True, exist_ok=True)
        if not storage_marker.exists():
            storage_marker.write_text("orca")
    except Exception:
        pass
