from pathlib import Path
import pandas as pd
from config import CODE_COLUMN

class PlanilhaError(Exception):
    pass

def carregar_codigos(caminho, sheet):
    caminho = Path(caminho)
    if not caminho.exists():
        raise PlanilhaError("A planilha selecionada não foi encontrada.")
    try:
        df = pd.read_excel(caminho, sheet_name=sheet)
    except Exception as exc:
        raise PlanilhaError(f"Não foi possível ler a planilha: {exc}") from exc
    if CODE_COLUMN not in df.columns:
        raise PlanilhaError(f"A coluna '{CODE_COLUMN}' não foi encontrada na planilha.")
    codigos = df[CODE_COLUMN].dropna().astype(str).tolist()
    if not codigos:
        raise PlanilhaError(f"A coluna '{CODE_COLUMN}' não possui códigos para processar.")
    return codigos
