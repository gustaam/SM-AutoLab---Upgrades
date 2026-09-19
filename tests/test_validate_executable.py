import tempfile
import unittest
from pathlib import Path
import struct

from scripts.validate import validate_pe


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


if __name__ == "__main__":
    unittest.main()
