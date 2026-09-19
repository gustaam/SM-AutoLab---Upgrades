import unittest
from types import SimpleNamespace
from pathlib import Path

from execution_center_29924 import (
    SM_AUTOLAB_EXECUTION_29924,
    format_execution_center,
)


class ExecutionCenterStage11Tests(unittest.TestCase):
    def test_stage11_marker(self):
        self.assertEqual(
            SM_AUTOLAB_EXECUTION_29924,
            "SM-AUTOLAB-EXECUTION-CENTER-29924",
        )

    def test_formatacao_normaliza_progresso_e_metricas(self):
        data = format_execution_center(3, 10, 2, 1, "ABC123")
        self.assertEqual(data["processados"], 3)
        self.assertEqual(data["total"], 10)
        self.assertEqual(data["sucessos"], 2)
        self.assertEqual(data["erros"], 1)
        self.assertAlmostEqual(data["percentual"], 0.3)
        self.assertEqual(data["status"], "Processando código 3 de 10")
        self.assertEqual(data["ultimo"], "ABC123")

    def test_formatacao_nao_permite_progresso_acima_do_total(self):
        data = format_execution_center(20, 10, 18, 2)
        self.assertEqual(data["processados"], 10)
        self.assertEqual(data["percentual"], 1.0)

    def test_formatacao_sem_total_e_estavel(self):
        data = format_execution_center(0, 0, 0, 0)
        self.assertEqual(data["percentual"], 0.0)
        self.assertEqual(data["status"], "Preparando execução")
        self.assertEqual(data["ultimo"], "—")

    def test_boot_e_instalador_estao_integrados(self):
        root = Path(__file__).resolve().parents[1]
        main = (root / "main.py").read_text(encoding="utf-8")
        build = (root / "build_windows.bat").read_text(encoding="utf-8")
        workflow = (root / ".github" / "workflows" / "validate-main.yml").read_text(encoding="utf-8")
        self.assertIn("SM_AUTOLAB_EXECUTION_29924", main)
        self.assertIn("install_ui_execution_center_29924", main)
        self.assertIn("install_ui_execution_center_29924", build)
        self.assertIn("install_ui_execution_center_29924", workflow)

    def test_modulo_expoe_funcao_do_centro(self):
        source = (Path(__file__).resolve().parents[1] / "execution_center_29924.py").read_text(encoding="utf-8")
        self.assertIn("def format_execution_center", source)
        self.assertIn("def install_ui_execution_center_29924", source)


if __name__ == "__main__":
    unittest.main()
