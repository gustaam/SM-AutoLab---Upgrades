from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

# Prefer the Windows/system certificate store in packaged builds.
# This avoids CERTIFICATE_VERIFY_FAILED when Python's bundled CA set is incomplete.
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

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
    version_file = base / "VERSION"
    try:
        value = version_file.read_text(encoding="utf-8").strip()
        if value:
            return value
    except OSError:
        pass
    return "2.64"


def fetch_latest_release(timeout: int = 8) -> dict:
    request = urllib.request.Request(
        API_LATEST,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def find_update(timeout: int = 8) -> dict | None:
    release = fetch_latest_release(timeout)
    latest = str(release.get("tag_name", "")).lstrip("vV")
    current = current_version()
    if not latest or _version_tuple(latest) <= _version_tuple(current):
        return None

    assets = release.get("assets") or []
    expected_version = latest.replace(".", "")
    exe_assets = [
        asset for asset in assets
        if str(asset.get("name", "")).lower().endswith(".exe")
        and "updater" not in str(asset.get("name", "")).lower()
    ]

    # Use only the executable belonging to the exact release version.
    def _asset_matches(asset):
        name = str(asset.get("name", "")).lower()
        normalized = "".join(ch for ch in name if ch.isalnum())
        return expected_version in normalized and "smautolab" in normalized

    matching = [asset for asset in exe_assets if _asset_matches(asset)]
    asset = matching[0] if len(matching) == 1 else None
    if asset is None:
        return {
            "version": latest,
            "current": current,
            "name": release.get("name") or f"SM AutoLab v{latest}",
            "url": release.get("html_url") or "",
            "download_url": "",
            "sha256": "",
            "release_url": release.get("html_url") or "",
        }

    digest = str(asset.get("digest") or "")
    if digest.lower().startswith("sha256:"):
        digest = digest.split(":", 1)[1]

    return {
        "version": latest,
        "current": current,
        "name": release.get("name") or f"SM AutoLab v{latest}",
        "url": release.get("html_url") or "",
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

    if expected_sha256:
        digest = hasher.hexdigest().lower()
        if digest != expected_sha256.lower():
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
        # Development fallback: run updater.py when the project is not packaged.
        candidate = app_dir / "updater.py"
        if candidate.exists():
            updater_exe = candidate
        else:
            return False, "O componente SM AutoLab Updater não foi encontrado."

    if not update.get("download_url"):
        return False, "A release encontrada não possui um executável correspondente à versão."

    command = [
        str(updater_exe),
        "--target", str(target),
        "--url", str(update["download_url"]),
        "--sha256", str(update.get("sha256") or ""),
        "--restart",
    ]

    try:
        if updater_exe.suffix.lower() == ".py":
            command = [sys.executable] + command
        subprocess.Popen(command, close_fds=True)
        return True, ""
    except OSError as exc:
        return False, str(exc)


def _cli() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=False)
    parser.add_argument("--url", required=False)
    parser.add_argument("--sha256", default="")
    parser.add_argument("--restart", action="store_true")
    args = parser.parse_args()

    if not args.target or not args.url:
        print("SM AutoLab Updater pronto.")
        return 0

    target = Path(args.target).resolve()
    temp_dir = Path(tempfile.mkdtemp(prefix="sm_autolab_update_"))
    temp_file = temp_dir / target.name

    # Wait for the main program to close before replacing its executable.
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
