from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

REPO = "gustaam/SM-AutoLab---Upgrades"
API_RELEASES = f"https://api.github.com/repos/{REPO}/releases?per_page=30"
USER_AGENT = "SM AutoLab"
UPDATE_CHANNEL = "SM-AUTOLAB-RESET-2026-09"
MANIFEST_ASSET_NAMES = {
    "release-manifest.json",
    "sm autolab release manifest.json",
    "sm.autolab.release.manifest.json",
}


def _normalize_asset_name(value: str) -> str:
    """Normaliza nomes para aceitar diferenças de separador e capitalização."""
    text = str(value or "").strip().lower()
    return re.sub(r"[\s._-]+", "", text)


def _version_tuple(value: str) -> tuple[int, ...]:
    """Converte versões numéricas em tupla sem truncar componentes."""
    value = str(value or "").strip().lstrip("vV")
    if not re.fullmatch(r"\d+(?:\.\d+)*", value):
        return ()
    parts = [int(piece) for piece in value.split(".")]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def current_version(base: Path | None = None) -> str:
    base = base or Path(getattr(__import__("sys"), "_MEIPASS", Path(__file__).resolve().parent))
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
    name = _normalize_asset_name(str(asset.get("name", "")))
    return name in {_normalize_asset_name(item) for item in MANIFEST_ASSET_NAMES}


def _release_asset_by_name(assets: list[dict], expected_name: str) -> dict | None:
    expected = _normalize_asset_name(expected_name)
    if not expected:
        return None
    return next(
        (
            asset
            for asset in assets
            if _normalize_asset_name(str(asset.get("name", ""))) == expected
        ),
        None,
    )


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
    if main_asset is None:
        return None
    main_name = str(main_asset.get("name", "")).strip().lower()
    if not main_name.endswith(".exe") or "updater" in _normalize_asset_name(main_name):
        return None
    return manifest


def find_update(timeout: int = 8) -> dict | None:
    current = current_version()
    current_tuple = _version_tuple(current)
    if not current_tuple:
        return None
    compatible: list[tuple[dict, tuple[int, ...], dict]] = []
    try:
        releases = fetch_releases(timeout)
    except Exception:
        return None
    for release in releases:
        if release.get("draft") or release.get("prerelease"):
            continue
        tag = str(release.get("tag_name", "")).strip().lstrip("vV")
        version_tuple = _version_tuple(tag)
        if not tag or not version_tuple or version_tuple <= current_tuple:
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


def _escape_cmd_path(value: str) -> str:
    """Escapa caracteres especiais para uso em arquivo .cmd sem expansão de variáveis."""
    return (
        str(value)
        .replace("^", "^^")
        .replace("&", "^&")
        .replace("|", "^|")
        .replace("<", "^<")
        .replace(">", "^>")
        .replace("%", "%%")
        .replace("!", "^^!")
    )


def _sanitize_pyinstaller_environment(environ: dict[str, str] | None = None) -> dict[str, str]:
    """Remove o estado interno herdado do PyInstaller antes do reinício."""
    source = dict(os.environ if environ is None else environ)
    return {
        key: value
        for key, value in source.items()
        if not key.upper().startswith("_PYI_") and key.upper() != "_MEIPASS2"
    }


def _prepare_independent_restart_environment(environ: dict[str, str] | None = None) -> dict[str, str]:
    """Prepara o ambiente para que a nova onefile seja tratada como instância independente."""
    env = _sanitize_pyinstaller_environment(environ)
    # Requisito oficial do PyInstaller para reinício de uma onefile que
    # sobreviverá ao processo atual (por exemplo, autoatualização).
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def _schedule_replace_after_exit(target: Path, downloaded: Path) -> tuple[bool, str]:
    script_dir = downloaded.parent
    script = script_dir / "apply_update.cmd"
    target_cmd = _escape_cmd_path(str(target))
    downloaded_cmd = _escape_cmd_path(str(downloaded))
    script_text = f"""@echo off
setlocal DisableDelayedExpansion
:wait_replace
move /Y "{downloaded_cmd}" "{target_cmd}" >nul 2>&1
if exist "{downloaded_cmd}" (
    timeout /t 1 /nobreak >nul
    goto wait_replace
)
start "" "{target_cmd}"
cd /d "%TEMP%" >nul 2>&1
rmdir /s /q "{_escape_cmd_path(str(script_dir))}" >nul 2>&1
"""
    try:
        script.write_text(script_text, encoding="utf-8", newline="\r\n")
        flags = 0
        if os.name == "nt":
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
        restart_env = _prepare_independent_restart_environment()
        subprocess.Popen(
            ["cmd.exe", "/d", "/c", str(script)],
            cwd=str(script_dir),
            close_fds=True,
            creationflags=flags,
            env=restart_env,
        )
        return True, ""
    except OSError as exc:
        return False, str(exc)


def launch_updater(update: dict) -> tuple[bool, str]:
    if os.name != "nt":
        return False, "A atualização automática integrada só está disponível no Windows."
    if not update.get("download_url"):
        return False, "A release encontrada não possui um executável correspondente à versão."

    target = Path(__import__("sys").executable).resolve()
    if target.suffix.lower() != ".exe" or not getattr(__import__("sys"), "frozen", False):
        return False, "A atualização automática integrada só está disponível no executável do SM AutoLab."

    temp_dir = Path(tempfile.mkdtemp(prefix="sm_autolab_update_"))
    downloaded = temp_dir / target.name
    try:
        download_file(str(update["download_url"]), downloaded, str(update.get("sha256") or ""))
        ok, error = _schedule_replace_after_exit(target, downloaded)
        if not ok:
            raise RuntimeError(error or "Não foi possível preparar a substituição da atualização.")
        return True, ""
    except Exception as exc:
        try:
            if downloaded.exists():
                downloaded.unlink()
        except OSError:
            pass
        try:
            script = temp_dir / "apply_update.cmd"
            if script.exists():
                script.unlink()
        except OSError:
            pass
        try:
            temp_dir.rmdir()
        except OSError:
            pass
        return False, str(exc)


if __name__ == "__main__":
    print("SM AutoLab pronto.")
