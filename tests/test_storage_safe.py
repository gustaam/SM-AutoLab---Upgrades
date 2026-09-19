import json
import tempfile
import unittest
from pathlib import Path

from app import atomic_write_json, atomic_write_text, backup_path, read_json_with_backup


class StorageSafeTests(unittest.TestCase):
    def test_escrita_atomica_cria_arquivo_e_backup_na_segunda_gravacao(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "estado.json"
            atomic_write_json(path, {"n": 1})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"n": 1})
            self.assertFalse(backup_path(path).exists())

            atomic_write_json(path, {"n": 2})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"n": 2})
            self.assertEqual(json.loads(backup_path(path).read_text(encoding="utf-8")), {"n": 1})

    def test_falha_de_corrompimento_recupera_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "estado.json"
            atomic_write_json(path, {"versao": 1})
            atomic_write_json(path, {"versao": 2})

            path.write_text("{corrompido", encoding="utf-8")
            self.assertEqual(read_json_with_backup(path), {"versao": 1})

    def test_escrita_atomicamente_nao_deixa_tmp_no_final(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "estado.txt"
            atomic_write_text(path, "ok")
            leftovers = list(Path(temp).glob(".*.tmp"))
            self.assertEqual(leftovers, [])
            self.assertEqual(path.read_text(encoding="utf-8"), "ok")


if __name__ == "__main__":
    unittest.main()
