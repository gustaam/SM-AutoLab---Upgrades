# Prepara Chrome for Testing + ChromeDriver oficiais para o build Windows.
from __future__ import annotations

import json
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

CF_T_ROOT = "https://googlechromelabs.github.io/chrome-for-testing"
VERSIONS_URL = f"{CF_T_ROOT}/last-known-good-versions-with-downloads.json"
PLATFORM = "win64"
RESOURCE_ROOT = Path("build_resources") / "chrome_for_testing"


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "SM-AutoLab-Build/1.0"},
    )
    with urllib.request.urlopen(request, timeout=180) as response, destination.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)


def _safe_extract(zip_path: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if target != destination and destination not in target.parents:
                raise RuntimeError(f"Entrada ZIP insegura: {member.filename}")
        archive.extractall(destination)


def _download_url(downloads: list[dict]) -> str:
    for item in downloads:
        if item.get("platform") == PLATFORM:
            return str(item.get("url") or "")
    return ""


def _existing_bundle_is_valid(version: str) -> bool:
    try:
        existing_version = (RESOURCE_ROOT / "version.txt").read_text(encoding="utf-8").strip()
    except OSError:
        return False
    return (
        existing_version == version
        and (RESOURCE_ROOT / "chrome-win64" / "chrome.exe").is_file()
        and (RESOURCE_ROOT / "chromedriver-win64" / "chromedriver.exe").is_file()
    )


def prepare() -> tuple[str, Path]:
    with urllib.request.urlopen(
        urllib.request.Request(
            VERSIONS_URL,
            headers={"User-Agent": "SM-AutoLab-Build/1.0"},
        ),
        timeout=60,
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))

    stable = payload.get("channels", {}).get("Stable", {})
    version = str(stable.get("version") or "").strip()
    chrome_url = _download_url(stable.get("downloads", {}).get("chrome", []))
    driver_url = _download_url(stable.get("downloads", {}).get("chromedriver", []))
    if not version or not chrome_url or not driver_url:
        raise RuntimeError("Não foi possível resolver Chrome for Testing/ChromeDriver Stable para win64.")

    if _existing_bundle_is_valid(version):
        print(f"Chrome for Testing {version} já preparado em {RESOURCE_ROOT}.")
        return version, RESOURCE_ROOT

    RESOURCE_ROOT.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="sm_autolab_cft_", dir=str(RESOURCE_ROOT.parent)))
    try:
        chrome_zip = staging / "chrome.zip"
        driver_zip = staging / "chromedriver.zip"
        print(f"Baixando Chrome for Testing {version}...")
        _download(chrome_url, chrome_zip)
        print("Baixando ChromeDriver correspondente...")
        _download(driver_url, driver_zip)

        extracted = staging / "extracted"
        extracted.mkdir()
        _safe_extract(chrome_zip, extracted)
        _safe_extract(driver_zip, extracted)

        browser = extracted / "chrome-win64" / "chrome.exe"
        driver = extracted / "chromedriver-win64" / "chromedriver.exe"
        if not browser.is_file():
            raise RuntimeError(f"Chrome for Testing extraído sem chrome.exe: {browser}")
        if not driver.is_file():
            raise RuntimeError(f"ChromeDriver extraído sem chromedriver.exe: {driver}")

        final_staging = staging / "chrome_for_testing"
        final_staging.mkdir()
        shutil.copytree(
            extracted / "chrome-win64",
            final_staging / "chrome-win64",
        )
        shutil.copytree(
            extracted / "chromedriver-win64",
            final_staging / "chromedriver-win64",
        )
        (final_staging / "version.txt").write_text(
            version + "\n",
            encoding="utf-8",
        )

        if RESOURCE_ROOT.exists():
            shutil.rmtree(RESOURCE_ROOT)
        final_staging.replace(RESOURCE_ROOT)
        print(f"Bundle Chrome for Testing pronto: {RESOURCE_ROOT}")
        return version, RESOURCE_ROOT
    finally:
        shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    prepare()
