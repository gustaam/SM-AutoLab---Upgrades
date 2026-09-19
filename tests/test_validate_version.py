import tempfile
import unittest
from pathlib import Path

from scripts.validate import parse_version, validate_version


class VersionValidationTests(unittest.TestCase):
    def test_parse_version_normaliza_prefixo_v(self):
        self.assertEqual(parse_version("v2.99.21"), (2, 99, 21))
        self.assertEqual(parse_version("2.99.21.1"), (2, 99, 21, 1))

    def test_parse_version_rejeita_formato_invalido(self):
        for value in ("", "v", "2.99", "2.99.x", "2.99.21.1.0"):
            self.assertEqual(parse_version(value), ())

    def test_validate_version_aceita_mesma_versao_anterior(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "VERSION").write_text("2.99.21\n", encoding="utf-8")
            (root / "PREV").write_text("2.99.21\n", encoding="utf-8")
            self.assertEqual(
                validate_version(root / "VERSION", root / "PREV"),
                (2, 99, 21),
            )

    def test_validate_version_aceita_incremento(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "VERSION").write_text("2.99.22\n", encoding="utf-8")
            (root / "PREV").write_text("2.99.21\n", encoding="utf-8")
            self.assertEqual(
                validate_version(root / "VERSION", root / "PREV"),
                (2, 99, 22),
            )

    def test_validate_version_rejeita_regressao(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "VERSION").write_text("2.99.20\n", encoding="utf-8")
            (root / "PREV").write_text("2.99.21\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_version(root / "VERSION", root / "PREV")


if __name__ == "__main__":
    unittest.main()
