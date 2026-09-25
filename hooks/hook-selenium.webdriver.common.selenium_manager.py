from pathlib import Path

from PyInstaller.utils.hooks import get_package_dir

package_dir = Path(get_package_dir("selenium"))
manager = (
    package_dir
    / "webdriver"
    / "common"
    / "windows"
    / "selenium-manager.exe"
)

if not manager.is_file():
    raise FileNotFoundError(
        f"Selenium Manager não encontrado no pacote Selenium: {manager}"
    )

binaries = [
    (
        str(manager),
        "selenium/webdriver/common/windows",
    )
]
