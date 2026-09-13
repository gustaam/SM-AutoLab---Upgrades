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


def _version_tuple(value: str) -> tuple[int, int, int]:
    value = str(value).strip().lstrip("vV")
    parts: list[int] = []
    for piece in value.split(".")[:3]:
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple((parts + [0, 0, 0])[:3])


def current_version(base: Path | None = None) -> str:
    base = base or Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    try:
        value = (base / "VERSION").read_text(encoding="utf-8").strip()
        if value:
            return value.lstrip("vV")
    except OSError:
        pass
    return ""


def fetch_releases(timeout: int = 8) -> list[dict]:
    request = urllib.request.Request(
        API_RELEASES,
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data if isinstance(data, list) else []


def _is_manifest_asset(asset: dict) -> bool:
    return str(asset.get("name", "")).strip().lower() in MANIFEST_ASSET_NAMES


def _release_asset_by_name(assets: list[dict], expected_name: str) -> dict | None:
    expected = str(expected_name).strip().lower()
    return next(
        (asset for asset in assets if str(asset.get("name", "")).strip().lower() == expected),
        None,
    )


def _is_main_asset(asset: dict) -> bool:
    name = str(asset.get("name", "")).strip().lower()
    return name.endswith(".exe") and "updater" not in name


def _is_updater_asset(asset: dict) -> bool:
    name = str(asset.get("name", "")).strip().lower()
    return name.endswith(".exe") and "updater" in name


def _load_release_manifest(release: dict, timeout: int = 8) -> dict | None:
    assets = release.get("assets") or []
    manifest_asset = next((a for a in assets if _is_manifest_asset(a)), None)
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
    release_version = str(release.get("tag_name", "")).strip().lstrip("vV")
    manifest_version = str(manifest.get("version", "")).strip().lstrip("vV")
    manifest_tag = str(manifest.get("tag", "")).strip().lstrip("vV")
    if not release_version or manifest_version != release_version or manifest_tag != release_version:
        return None
    main_asset = _release_asset_by_name(assets, str(manifest.get("main_asset", "")))
    updater_asset = _release_asset_by_name(assets, str(manifest.get("updater_asset", "")))
    if main_asset is None or updater_asset is None:
        return None
    if not _is_main_asset(main_asset) or not _is_updater_asset(updater_asset):
        return None
    return manifest


def find_update(timeout: int = 8) -> dict | None:
    current = current_version()
    current_tuple = _version_tuple(current)
    compatible: list[tuple[dict, tuple[int, int, int], dict]] = []
    try:
        releases = fetch_releases(timeout)
    except Exception:
        return None
    for release in releases:
        if release.get("draft") or release.get("prerelease"):
            continue
        tag = str(release.get("tag_name", "")).strip().lstrip("vV")
        if not tag:
            continue
        version_tuple = _version_tuple(tag)
        if version_tuple <= current_tuple:
            continue
        manifest = _load_release_manifest(release, timeout)
        if manifest is None:
            continue
        compatible.append((release, version_tuple, manifest))
    if not compatible:
        return None
    release, _, manifest = max(compatible, key=lambda item: item[1])
    latest = str(release.get("tag_name", "")).strip().lstrip("vV")
    assets = release.get("assets") or []
    asset = _release_asset_by_name(assets, str(manifest.get("main_asset", "")))
    if asset is None:
        return None
    digest = str(asset.get("digest") or "")
    if digest.lower().startswith("sha256:"):
        digest = digest.split(":", 1)[1]
    if not digest:
        digest = str(manifest.get("main_sha256") or "")
    if not digest:
        return None
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
    if expected_sha256 and hasher.hexdigest().lower() != expected_sha256.lower():
        try:
            destination.unlink()
        except OSError:
            pass
        raise RuntimeError("A verificação SHA-256 da atualização falhou.")


def _spawn_integrated_helper(target: Path, update: dict) -> tuple[bool, str]:
    helper_dir = Path(tempfile.mkdtemp(prefix="sm_autolab_integrated_update_"))
    helper = helper_dir / target.name
    try:
        shutil.copy2(target, helper)
        flags = 0
        if os.name == "nt":
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        subprocess.Popen(
            [
                str(helper),
                "--sm-autolab-updater",
                "--target", str(target),
                "--url", str(update["download_url"]),
                "--sha256", str(update.get("sha256") or ""),
                "--restart",
                "--cleanup-dir", str(helper_dir),
            ],
            cwd=str(helper_dir),
            close_fds=True,
            creationflags=flags,
        )
        return True, ""
    except OSError as exc:
        shutil.rmtree(helper_dir, ignore_errors=True)
        return False, str(exc)


def launch_updater(update: dict) -> tuple[bool, str]:
    target = Path(sys.executable).resolve()
    if not update.get("download_url"):
        return False, "A release encontrada não possui um executável correspondente à versão."

    # O executável principal já contém o updater. Uma cópia temporária atua
    # como auxiliar, permitindo substituir o arquivo original após o fechamento.
    if getattr(sys, "frozen", False) and target.suffix.lower() == ".exe":
        return _spawn_integrated_helper(target, update)

    # Compatibilidade com execução por Python e instalações antigas.
    app_dir = target.parent
    updater_names = (
        "SM AutoLab Updater.exe",
        "SM.AutoLab Updater.exe",
        "SM.AutoLab.Updater.exe",
        "SM_AutoLab_Updater.exe",
    )
    updater_exe = next((app_dir / name for name in updater_names if (app_dir / name).exists()), None)
    if updater_exe is None:
        candidate = app_dir / "updater.py"
        updater_exe = candidate if candidate.exists() else None
    if updater_exe is None:
        return False, "O componente SM AutoLab Updater não foi encontrado."

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


def _schedule_cleanup(path: Path) -> None:
    if os.name != "nt":
        return
    try:
        command = f'ping 127.0.0.1 -n 3 >nul & rmdir /s /q "{path}"'
        subprocess.Popen(
            ["cmd", "/c", command],
            creationflags=subprocess.CREATE_NO_WINDOW,
            close_fds=True,
        )
    except OSError:
        pass


def _cli() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--sm-autolab-updater", action="store_true")
    parser.add_argument("--target")
    parser.add_argument("--url")
    parser.add_argument("--sha256", default="")
    parser.add_argument("--restart", action="store_true")
    parser.add_argument("--cleanup-dir")
    args = parser.parse_args()

    if not args.target or not args.url:
        print("SM AutoLab Updater pronto.")
        return 0

    target = Path(args.target).resolve()
    cleanup_dir = Path(args.cleanup_dir).resolve() if args.cleanup_dir else None
    temp_dir = Path(tempfile.mkdtemp(prefix="sm_autolab_update_"))
    temp_file = temp_dir / target.name

    deadline = time.time() + 60
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
        shutil.rmtree(temp_dir, ignore_errors=True)
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
        if cleanup_dir:
            _schedule_cleanup(cleanup_dir)


if __name__ == "__main__":
    raise SystemExit(_cli())
