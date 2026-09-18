import unittest

from app import ResultadoCodigo, Resultados, SM_AUTOLAB_EXECUCAO_29923


class ExecucaoPerformanceStage10Tests(unittest.TestCase):
    def test_stage10_marker(self):
        self.assertEqual(
            SM_AUTOLAB_EXECUCAO_29923,
            "SM-AUTOLAB-EXECUCAO-PERFORMANCE-29923",
        )

    def test_metricas_de_resultados_sao_incrementais(self):
        resultados = Resultados(total=4)
        self.assertEqual(resultados.processados, 0)
        self.assertEqual(resultados.sucessos, 0)
        self.assertEqual(resultados.erros, 0)

        resultados.registrar_sucesso(1, "A")
        resultados.registrar_erro(2, "B", "falha")
        resultados.registrar_sucesso(3, "C")

        self.assertEqual(resultados.processados, 3)
        self.assertEqual(resultados.sucessos, 2)
        self.assertEqual(resultados.erros, 1)
        self.assertEqual(len(resultados.itens), 3)

    def test_contadores_nao_dependem_de_recontagem_dos_itens(self):
        resultados = Resultados(total=2)
        resultados.itens = [
            ResultadoCodigo(1, "A", "Sucesso"),
            ResultadoCodigo(2, "B", "Erro", erro="falha"),
        ]

        self.assertEqual(resultados.sucessos, 0)
        self.assertEqual(resultados.erros, 0)

        resultados.registrar_sucesso(3, "C")
        self.assertEqual(resultados.sucessos, 1)
        self.assertEqual(resultados.erros, 0)


if __name__ == "__main__":
    unittest.main()
