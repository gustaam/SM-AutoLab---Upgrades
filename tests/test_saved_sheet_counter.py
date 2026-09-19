import unittest
from types import SimpleNamespace
import main


class SavedSheetCounterTests(unittest.TestCase):
    def test_home_counter_conta_apenas_senhas_da_planilha_atual(self):
        class FakeLabel:
            def __init__(self):
                self.text = None
            def configure(self, **kwargs):
                self.text = kwargs.get("text")
            def winfo_manager(self):
                return "pack"
            def pack_configure(self, **kwargs):
                pass
            def pack_forget(self):
                self.text = None

        class AppStub:
            arquivos_contador_label = FakeLabel()
            _planilha_data = {
                "0,0": "10",
                "0,1": "senha-1",
                "0,2": "item",
                "1,1": "senha-2",
                "2,0": "20",
            }
            _planilha_arquivo = SimpleNamespace(exists=lambda: False)

        main._home_counter(AppStub)
        self.assertEqual(AppStub.arquivos_contador_label.text, "2 Códigos salvos")


if __name__ == "__main__":
    unittest.main()
