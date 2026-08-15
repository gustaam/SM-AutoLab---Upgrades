from dataclasses import dataclass
from datetime import datetime

@dataclass
class ResultadoCodigo:
    numero: int
    codigo: str
    status: str
    erro: str = ""
    horario: str = ""

class Resultados:
    def __init__(self, total=0):
        self.total_planejado = total
        self.itens = []
    def registrar_sucesso(self, numero, codigo):
        self.itens.append(ResultadoCodigo(numero, str(codigo), "Sucesso", horario=datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    def registrar_erro(self, numero, codigo, erro):
        self.itens.append(ResultadoCodigo(numero, str(codigo), "Erro", erro=str(erro), horario=datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    @property
    def processados(self): return len(self.itens)
    @property
    def sucessos(self): return sum(x.status=="Sucesso" for x in self.itens)
    @property
    def erros(self): return sum(x.status=="Erro" for x in self.itens)
