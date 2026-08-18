from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = "gustaam/SM-AutoLab---Upgrades"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
USER_AGENT = "SM-AutoLab-Updater"


def _version_tuple(value: str) -> tuple[int, ...]:
    value = str(value).strip().lstrip("vV")
    parts = []
    for piece in value.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple((parts + [0, 0, 0])[:3])


def current_version(base: Path | None = None) -> str:
    base = base or Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    try:
        value = (base / "VERSION").read_text(encoding="utf-8").strip()
        if value:
            return value
    except OSError:
        pass
    return "2.66"


def fetch_latest_release(timeout: int = 8) -> dict:
    request = urllib.request.Request(
        API_LATEST,
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _asset_version(name: str) -> tuple[int, ...] | None:
    """Extract the semantic version from an SM AutoLab application asset."""
    name = str(name)
    if not name.lower().endswith(".exe") or "updater" in name.lower():
        return None

    match = re.search(r"(?:^|[^0-9])v(\d+(?:\.\d+){1,2})(?:[^0-9]|$)", name, re.IGNORECASE)
    if not match:
        match = re.search(r"SM[ _-]*AutoLab[^0-9]*(\d+(?:\.\d+){1,2})(?:[^0-9]|$)", name, re.IGNORECASE)
    if not match:
        return None
    return _version_tuple(match.group(1))


def _select_release_executable(release: dict, latest: str) -> dict | None:
    expected = _version_tuple(latest)
    assets = release.get("assets") or []

    candidates = []
    for asset in assets:
        name = str(asset.get("name", ""))
        version = _asset_version(name)
        if version == expected:
            candidates.append(asset)

    if len(candidates) == 1:
        return candidates[0]

    # If the release has exactly one non-updater EXE, accept it as a
    # compatibility fallback. Otherwise refuse to guess between binaries.
    exe_assets = [
        asset for asset in assets
        if str(asset.get("name", "")).lower().endswith(".exe")
        and "updater" not in str(asset.get("name", "")).lower()
    ]
    if len(exe_assets) == 1:
        return exe_assets[0]
    return None


def find_update(timeout: int = 8) -> dict | None:
    release = fetch_latest_release(timeout)
    latest = str(release.get("tag_name", "")).lstrip("vV")
    current = current_version()
    if not latest or _version_tuple(latest) <= _version_tuple(current):
        return None

    asset = _select_release_executable(release, latest)
    if asset is None:
        return {
            "version": latest,
            "current": current,
            "name": release.get("name") or f"SM AutoLab v{latest}",
            "download_url": "",
            "sha256": "",
            "release_url": release.get("html_url") or "",
            "error": "A release possui mais de um executável e nenhum corresponde de forma inequívoca à versão publicada.",
        }

    digest = str(asset.get("digest") or "")
    if digest.lower().startswith("sha256:"):
        digest = digest.split(":", 1)[1]

    return {
        "version": latest,
        "current": current,
        "name": release.get("name") or f"SM AutoLab v{latest}",
        "download_url": asset.get("browser_download_url") or "",
        "sha256": digest,
        "asset_name": asset.get("name") or "",
        "release_url": release.get("html_url") or "",
    }


def download_file(url: str, destination: Path, expected_sha256: str = "") -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    hasher = hashlib.sha256()
    with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            hasher.update(chunk)
    if expected_sha256 and hasher.hexdigest().lower() != expected_sha256.lower():
        try:
            destination.unlink()
        except OSError:
            pass
        raise RuntimeError("A verificação SHA-256 da atualização falhou.")


def launch_updater(update: dict) -> tuple[bool, str]:
    target = Path(sys.executable).resolve()
    app_dir = target.parent
    updater_exe = app_dir / "SM AutoLab Updater.exe"
    if not updater_exe.exists():
        return False, "O componente SM AutoLab Updater não foi encontrado."
    if not update.get("download_url"):
        return False, update.get("error") or "A release encontrada não possui um executável correspondente à versão."
    command = [
        str(updater_exe),
        "--target", str(target),
        "--url", str(update["download_url"]),
        "--sha256", str(update.get("sha256") or ""),
        "--restart",
    ]
    try:
        subprocess.Popen(command, close_fds=True)
        return True, ""
    except OSError as exc:
        return False, str(exc)


def _cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target")
    parser.add_argument("--url")
    parser.add_argument("--sha256", default="")
    parser.add_argument("--restart", action="store_true")
    args = parser.parse_args()
    if not args.target or not args.url:
        print("SM AutoLab Updater pronto.")
        return 0

    target = Path(args.target).resolve()
    temp_dir = Path(tempfile.mkdtemp(prefix="sm_autolab_update_"))
    temp_file = temp_dir / target.name
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            test = target.with_suffix(target.suffix + ".update_test")
            with test.open("wb"):
                pass
            test.unlink()
            break
        except OSError:
            time.sleep(0.25)
    else:
        return 2

    try:
        download_file(args.url, temp_file, args.sha256)
        os.replace(temp_file, target)
        if args.restart:
            subprocess.Popen([str(target)], close_fds=True)
        return 0
    except Exception as exc:
        print(f"Atualização falhou: {exc}")
        return 3
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(_cli())
