import unittest
from pathlib import Path

from windows11_native_29925 import (
    SM_AUTOLAB_WINDOWS_NATIVE_29925,
    _material_for_window,
)


class Windows11NativeStage12Tests(unittest.TestCase):
    def test_stage12_marker(self):
        self.assertEqual(
            SM_AUTOLAB_WINDOWS_NATIVE_29925,
            "SM-AUTOLAB-WINDOWS-NATIVE-29925",
        )

    def test_material_hierarchy(self):
        class Root:
            def title(self):
                return "SM AutoLab"

        class Secondary:
            def __init__(self, title):
                self._title = title

            def title(self):
                return self._title

        root = Root()
        self.assertEqual(_material_for_window(root, root), "mica")
        self.assertEqual(
            _material_for_window(Secondary("Planilha — SM AutoLab"), root),
            "mica_alt",
        )
        self.assertEqual(
            _material_for_window(Secondary("Mudar o Feegow"), root),
            "acrylic",
        )

    def test_main_build_and_workflows_integrate_stage12(self):
        root = Path(__file__).resolve().parents[1]
        main = (root / "main.py").read_text(encoding="utf-8")
        build = (root / "build_windows.bat").read_text(encoding="utf-8")
        validate = (root / ".github" / "workflows" / "validate-main.yml").read_text(encoding="utf-8")
        release = (root / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

        self.assertIn("install_ui_windows11_native_29925", main)
        self.assertIn(
            "from interface import App; from main import install_ui, _validar_base_aplicacao",
            build,
        )
        self.assertIn(
            "from interface import App; from main import install_ui, _validar_base_aplicacao",
            validate,
        )
        self.assertIn(
            "from interface import App; from main import install_ui, _validar_base_aplicacao",
            release,
        )

    def test_native_layer_has_accessibility_and_dwm_paths(self):
        source = (
            Path(__file__).resolve().parents[1] / "windows11_native_29925.py"
        ).read_text(encoding="utf-8")
        self.assertIn("SystemParametersInfoW", source)
        self.assertIn("DwmSetWindowAttribute", source)
        self.assertIn("SetWindowTheme", source)
        self.assertIn("DWMWA_SYSTEMBACKDROP_TYPE", source)
        self.assertIn("DWMWCP_ROUND", source)


if __name__ == "__main__":
    unittest.main()
