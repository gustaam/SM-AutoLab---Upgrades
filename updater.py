from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

REPO = "gustaam/SM-AutoLab---Upgrades"
API_RELEASES = f"https://api.github.com/repos/{REPO}/releases?per_page=30"
USER_AGENT = "SM-AutoLab-Updater"
UPDATE_CHANNEL = "SM-AUTOLAB-RESET-2026-09"
MANIFEST_ASSET_NAMES = {
    "release-manifest.json",
    "sm autolab release manifest.json",
    "sm.autolab.release.manifest.json",
}


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
    return ""


def fetch_releases(timeout: int = 8) -> list[dict]:
    request = urllib.request.Request(
        API_RELEASES,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data if isinstance(data, list) else []


def _is_manifest_asset(asset: dict) -> bool:
    name = str(asset.get("name", "")).strip().lower()
    return name in MANIFEST_ASSET_NAMES


def _main_asset_candidates(assets: list[dict]) -> list[dict]:
    return [
        asset for asset in assets
        if str(asset.get("name", "")).lower().endswith(".exe")
        and "updater" not in str(asset.get("name", "")).lower()
    ]


def _updater_asset_candidates(assets: list[dict]) -> list[dict]:
    return [
        asset for asset in assets
        if str(asset.get("name", "")).lower().endswith(".exe")
        and "updater" in str(asset.get("name", "")).lower()
    ]


def _release_asset_by_name(assets: list[dict], expected_name: str) -> dict | None:
    expected = str(expected_name).strip().lower()
    return next(
        (asset for asset in assets if str(asset.get("name", "")).strip().lower() == expected),
        None,
    )


def _load_release_manifest(release: dict, timeout: int) -> dict | None:
    """Confirma que os assets pertencem à mesma release e à linha atual."""
    assets = release.get("assets") or []
    manifest_asset = next((asset for asset in assets if _is_manifest_asset(asset)), None)
    if manifest_asset is None:
        return None

    url = str(manifest_asset.get("browser_download_url") or "")
    if not url:
        return None

    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            manifest = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None

    if not isinstance(manifest, dict) or manifest.get("channel") != UPDATE_CHANNEL:
        return None

    release_tag = str(release.get("tag_name", "")).strip().lstrip("vV")
    manifest_tag = str(manifest.get("tag", "")).strip().lstrip("vV")
    manifest_version = str(manifest.get("version", "")).strip().lstrip("vV")
    if not release_tag or manifest_tag != release_tag or manifest_version != release_tag:
        return None

    main_asset = _release_asset_by_name(assets, str(manifest.get("main_asset", "")))
    updater_asset = _release_asset_by_name(assets, str(manifest.get("updater_asset", "")))
    if main_asset is None or updater_asset is None:
        return None
    if main_asset not in _main_asset_candidates(assets):
        return None
    if updater_asset not in _updater_asset_candidates(assets):
        return None

    return manifest


def find_update(timeout: int = 8) -> dict | None:
    current = current_version()
    current_tuple = _version_tuple(current)
    compatible = []

    for release in fetch_releases(timeout):
        if release.get("draft") or release.get("prerelease"):
            continue
        if f"<!-- {UPDATE_CHANNEL} -->" not in str(release.get("body") or ""):
            continue

        assets = release.get("assets") or []
        if not any(_is_manifest_asset(asset) for asset in assets):
            continue
        manifest = _load_release_manifest(release, timeout)
        if manifest is None:
            continue

        latest = str(release.get("tag_name", "")).lstrip("vV")
        if not latest or _version_tuple(latest) <= current_tuple:
            continue
        compatible.append((release, _version_tuple(latest), manifest))

    if not compatible:
        return None

    release, _, manifest = max(compatible, key=lambda item: item[1])
    latest = str(release.get("tag_name", "")).lstrip("vV")
    assets = release.get("assets") or []
    asset = _release_asset_by_name(assets, str(manifest["main_asset"]))
    if asset is None:
        return None
    digest = str(asset.get("digest") or "")
    if digest.lower().startswith("sha256:"):
        digest = digest.split(":", 1)[1]
    if not digest:
        digest = str(manifest.get("main_sha256") or "")

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
    updater_names = (
        "SM AutoLab Updater.exe",
        "SM.AutoLab Updater.exe",
        "SM.AutoLab.Updater.exe",
        "SM_AutoLab_Updater.exe",
    )
    updater_exe = next((app_dir / name for name in updater_names if (app_dir / name).exists()), None)

    if updater_exe is None:
        expected = "smautolabupdaterexe"
        for candidate in app_dir.glob("*.exe"):
            normalized = "".join(ch for ch in candidate.name.lower() if ch.isalnum())
            if normalized == expected:
                updater_exe = candidate
                break

    if updater_exe is None:
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
