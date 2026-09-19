import struct
import tempfile
import unittest
from pathlib import Path

from scripts.validate import parse_version, validate_pe, validate_quality, validate_version

# tests/test_validate_executable.py

class ExecutableValidationTests(unittest.TestCase):
    def _write_pe(self, size=1_100_000, mz=b"MZ", pe=b"PE\x00\x00"):
        handle = tempfile.NamedTemporaryFile(delete=False)
        path = Path(handle.name)
        handle.close()
        data = bytearray(max(size, 0x100))
        data[:2] = mz
        struct.pack_into("<I", data, 0x3C, 0x80)
        data[0x80:0x84] = pe
        path.write_bytes(data)
        return path

    def test_validate_pe_aceita_executavel_pe_minimo(self):
        path = self._write_pe()
        try:
            result = validate_pe(path)
            self.assertEqual(result["pe_offset"], 0x80)
            self.assertGreaterEqual(result["size"], 1_000_000)
        finally:
            path.unlink(missing_ok=True)

    def test_rejeita_assinatura_mz(self):
        path = self._write_pe(mz=b"XX")
        try:
            with self.assertRaises(ValueError):
                validate_pe(path)
        finally:
            path.unlink(missing_ok=True)

    def test_rejeita_assinatura_pe(self):
        path = self._write_pe(pe=b"NOPE")
        try:
            with self.assertRaises(ValueError):
                validate_pe(path)
        finally:
            path.unlink(missing_ok=True)

    def test_rejeita_arquivo_pequeno(self):
        path = self._write_pe(size=1000)
        try:
            with self.assertRaises(ValueError):
                validate_pe(path)
        finally:
            path.unlink(missing_ok=True)


# tests/test_validate_quality.py

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


# tests/test_validate_version.py

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
