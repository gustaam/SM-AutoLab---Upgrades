import unittest
from pathlib import Path


class SeleniumManagerHookTests(unittest.TestCase):
    def test_hook_coleta_o_binario_windows_no_destino_esperado(self):
        root = Path(__file__).resolve().parents[1]
        hook = root / "hooks" / "hook-selenium.webdriver.common.selenium_manager.py"
        source = hook.read_text(encoding="utf-8")

        self.assertIn('get_package_dir("selenium")', source)
        self.assertIn('"selenium-manager.exe"', source)
        self.assertIn('"selenium/webdriver/common/windows"', source)
        self.assertIn("binaries = [", source)


if __name__ == "__main__":
    unittest.main()
