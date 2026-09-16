import unittest
from pathlib import Path


class TestPatch(unittest.TestCase):
    def test_instrucao_ctrl_clique_foi_removida(self):
        root = Path(__file__).resolve().parents[1]
        for name in ("main.py", "interface.py", "patch.py"):
            self.assertNotIn("Ctrl + clique para selecionar várias datas", (root / name).read_text(encoding="utf-8"))

    def test_componentes_base_estao_fisicamente_consolidados(self):
        root = Path(__file__).resolve().parents[1]
        patch = (root / "patch.py").read_text(encoding="utf-8")
        for name in ("patch_base.py", "patch_arquivos.py", "patch_ajustes.py"):
            self.assertFalse((root / name).exists(), msg=f"{name} ainda existe")
        for marker in (
            "_SOURCE_PATCH_BASE", "_SOURCE_PATCH_ARQUIVOS", "_SOURCE_PATCH_AJUSTES",
            "_NS_PATCH_BASE", "_NS_PATCH_ARQUIVOS", "_NS_PATCH_AJUSTES",
        ):
            self.assertIn(marker, patch)

    def test_ponto_de_entrada_atualizado(self):
        root = Path(__file__).resolve().parents[1]
        main = (root / "main.py").read_text(encoding="utf-8")
        interface = (root / "interface.py").read_text(encoding="utf-8")
        atualizacao = (root / "atualizacao.py").read_text(encoding="utf-8")
        build = (root / "build_windows.bat").read_text(encoding="utf-8")
        self.assertIn("from patch import aplicar_patch_ui", main)
        for content in (main, interface, atualizacao, build):
            self.assertNotIn("from patch_base import", content)
            self.assertNotIn("from patch_arquivos import", content)
            self.assertNotIn("from patch_ajustes import", content)
        self.assertIn("from patch import aplicar_patch_ui", build)

    def test_artifacts_temporarios_da_etapa_b_nao_existirem(self):
        root = Path(__file__).resolve().parents[1]
        self.assertFalse((root / ".etapa-b-trigger").exists())
        self.assertFalse((root / ".github" / "workflows" / "_fix_patch_b_import.yml").exists())


if __name__ == "__main__":
    unittest.main()
