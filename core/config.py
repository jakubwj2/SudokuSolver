from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

# Project root (parent of core/)
_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = _ROOT / "config.json"
_URL_SCHEMES = frozenset({"http", "https", "rtsp"})


@dataclass(frozen=True)
class CameraConfig:
    ip_webcam_url: str


@dataclass(frozen=True)
class PathsConfig:
    model: Path
    photos_dir: Path
    photos_dir_android: Path


@dataclass(frozen=True)
class AppConfig:
    camera: CameraConfig
    paths: PathsConfig


def _require_mapping(data: object, name: str) -> dict:
    if not isinstance(data, dict):
        raise ValueError(f"{CONFIG_PATH.name}: {name} must be an object")
    return data


def _require_str(data: dict, key: str, name: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{CONFIG_PATH.name}: {name}.{key} must be a non-empty string")
    return value.strip()


def _resolve_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = _ROOT / path
    return path


def _parse_camera(data: dict) -> CameraConfig:
    url = _require_str(data, "ip_webcam_url", "camera")
    parsed = urlparse(url)
    if parsed.scheme not in _URL_SCHEMES or not parsed.netloc:
        raise ValueError(
            f"{CONFIG_PATH.name}: camera.ip_webcam_url must be an http(s)/rtsp URL, "
            f"got {url!r}"
        )
    return CameraConfig(ip_webcam_url=url)


def _parse_paths(data: dict) -> PathsConfig:
    return PathsConfig(
        model=_resolve_path(_require_str(data, "model", "paths")),
        photos_dir=_resolve_path(_require_str(data, "photos_dir", "paths")),
        photos_dir_android=Path(_require_str(data, "photos_dir_android", "paths")),
    )


def get_config() -> AppConfig:
    """Load and validate config.json from the project root."""
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(f"Missing config file: {CONFIG_PATH}")

    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    data = _require_mapping(raw, "root")
    return AppConfig(
        camera=_parse_camera(_require_mapping(data.get("camera"), "camera")),
        paths=_parse_paths(_require_mapping(data.get("paths"), "paths")),
    )
