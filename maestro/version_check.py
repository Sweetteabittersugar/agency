"""Best-effort GitHub Releases update check with a 24-hour local cache."""

import json
import os
import time
import urllib.request
from pathlib import Path

from maestro.app_config import STATE_DIR

CACHE_FILE = STATE_DIR / "version-cache.json"
CACHE_TTL = 86400  # 24 小时
RELEASES_URL = "https://api.github.com/repos/Sweetteabittersugar/agency/releases/latest"
CHECK_DISABLED = os.environ.get("AGENCY_NO_UPDATE_CHECK", "") == "1"


def _read_cache() -> dict | None:
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text())
        if time.time() - data.get("ts", 0) < CACHE_TTL:
            return data
    except Exception:
        pass
    return None


def _write_cache(current: str, latest: str) -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps({"ts": time.time(), "current": current, "latest": latest}))
    except Exception:
        pass


def _get_installed_version() -> str:
    try:
        from importlib.metadata import version

        return version("agency-kit")
    except Exception:
        pass
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    try:
        return version_file.read_text().strip()
    except Exception:
        return "0.0.0"


def _get_latest_version() -> str | None:
    try:
        req = urllib.request.Request(
            RELEASES_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "agency-kit-update-check",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            tag = str(data.get("tag_name") or "")
            return tag.removeprefix("v") or None
    except Exception:
        return None


def _format_message(current: str, latest: str) -> str:
    cmd = f"git fetch --tags && git switch --detach v{latest}"
    return f"\n  ⚠️  新版可用: {current} → {latest}  升级: {cmd}\n"


def check_version() -> str | None:
    """检查是否有新版本。返回升级提示字符串，无更新返回 None。"""
    if CHECK_DISABLED:
        return None

    current = _get_installed_version()

    cached = _read_cache()
    if cached and cached.get("current") == current:
        latest = cached.get("latest")
        if latest and latest != current:
            return _format_message(current, latest)
        return None

    latest = _get_latest_version()
    if not latest:
        return None

    _write_cache(current, latest)

    if latest != current:
        return _format_message(current, latest)
    return None
