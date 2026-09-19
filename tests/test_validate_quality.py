import tempfile
import unittest
from pathlib import Path

from scripts.validate import validate_quality


class QualityValidationTests(unittest.TestCase):
    def test_repositorio_atual_passa_na_validacao(self):
        root = Path(__file__).resolve().parents[1]
        result = validate_quality(root)
        self.assertGreaterEqual(result["modules"], 1)
        self.assertEqual(result["cycles"], [])

    def test_detecta_metodo_duplicado_direto_na_classe(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").write_text(
                "class App:\n"
                "    def x(self): pass\n"
                "    def x(self): pass\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "método duplicado"):
                validate_quality(root)

    def test_detecta_import_wildcard(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").write_text(
                "from config import *\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "import wildcard"):
                validate_quality(root)

    def test_detecta_ciclo_local(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").write_text("from interface import App\n", encoding="utf-8")
            (root / "interface.py").write_text("import main\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ciclo de importação"):
                validate_quality(root)


if __name__ == "__main__":
    unittest.main()
