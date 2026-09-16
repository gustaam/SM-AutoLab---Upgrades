import unittest
from pathlib import Path


class TestPatchUI(unittest.TestCase):
    def test_instrucao_ctrl_clique_foi_removida(self):
        root = Path(__file__).resolve().parents[1]
        for name in ("main.py", "interface.py", "patch_ui.py"):
            self.assertNotIn("Ctrl + clique para selecionar várias datas", (root / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
