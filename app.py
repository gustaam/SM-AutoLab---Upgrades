import json
from datetime import datetime
from pathlib import Path
from automacao import Automacao, AutomacaoError
from planilha import carregar_codigos, PlanilhaError
from resultados import Resultados

def caminho_checkpoint(planilha_path,sheet):
    p=Path(planilha_path); return p.parent/f".{p.stem}_autolab_pagina_{sheet+1}_checkpoint.json"
def salvar_checkpoint(planilha_path,sheet,proximo_indice):
    c=caminho_checkpoint(planilha_path,sheet); t=c.with_suffix(c.suffix+".tmp")
    t.write_text(json.dumps({"planilha":str(Path(planilha_path).resolve()),"sheet":sheet,"proximo_indice":proximo_indice},ensure_ascii=False,indent=2),encoding="utf-8"); t.replace(c)
def ler_checkpoint(planilha_path,sheet):
    c=caminho_checkpoint(planilha_path,sheet)
    if not c.exists(): return None
    try:
        d=json.loads(c.read_text(encoding="utf-8"))
        if d.get("planilha")!=str(Path(planilha_path).resolve()) or d.get("sheet")!=sheet:return None
        x=int(d.get("proximo_indice",0)); return x if x>=0 else None
    except Exception:return None
def excluir_checkpoint(planilha_path,sheet):
    try:
        c=caminho_checkpoint(planilha_path,sheet)
        if c.exists(): c.unlink()
    except OSError: pass

def _fingerprint_codigos(codigos):
    import hashlib
    payload="\n".join(str(c) for c in codigos).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def caminho_checkpoint_interno():
    return Path.home() / "SM AutoLab" / "interno_checkpoint.json"

def salvar_checkpoint_interno(codigos, proximo_indice):
    c=caminho_checkpoint_interno()
    c.parent.mkdir(parents=True, exist_ok=True)
    payload={
        "version":1,
        "fingerprint":_fingerprint_codigos(codigos),
        "total":len(codigos),
        "proximo_indice":int(proximo_indice),
        "updated_at":datetime.now().isoformat(timespec="seconds"),
    }
    t=c.with_suffix(c.suffix+".tmp")
    t.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    t.replace(c)

def ler_checkpoint_interno(codigos):
    c=caminho_checkpoint_interno()
    if not c.exists(): return None
    try:
        d=json.loads(c.read_text(encoding="utf-8"))
        if d.get("fingerprint") != _fingerprint_codigos(codigos):
            return None
        x=int(d.get("proximo_indice",0))
        return x if 0 <= x <= len(codigos) else None
    except Exception:
        return None

def excluir_checkpoint_interno():
    try:
        c=caminho_checkpoint_interno()
        if c.exists(): c.unlink()
    except OSError:
        pass

def principal_interno(codigos, aplicativo=None, indice_inicial=0):
    codigos=[str(c).strip() for c in codigos if str(c).strip()]
    resultados=Resultados(len(codigos))
    auto=Automacao(status_callback=aplicativo.atualizar_status if aplicativo else None)
    if aplicativo is not None:
        aplicativo._automacao_atual=auto
    proximo_indice_seguro=int(indice_inicial)
    try:
        total=len(codigos)
        if total == 0:
            return resultados
        if aplicativo:
            aplicativo.atualizar_progresso(indice_inicial,total,0,0,"")
        auto.iniciar_navegador()
        for indice in range(indice_inicial,total):
            if aplicativo and aplicativo.deve_parar():
                salvar_checkpoint_interno(codigos,indice)
                break
            codigo=codigos[indice]
            numero=indice+1
            try:
                auto.executar_codigo(codigo)
                resultados.registrar_sucesso(numero,codigo)
            except AutomacaoError as exc:
                resultados.registrar_erro(numero,codigo,str(exc))
                if aplicativo:
                    aplicativo._add_activity(
                        f"Erro ({exc.tipo}) no código {codigo}. Indo para o próximo...",
                        aplicativo.ERROR
                    )
            salvar_checkpoint_interno(codigos,indice+1)
            proximo_indice_seguro=indice+1
            if aplicativo:
                aplicativo.atualizar_progresso(
                    indice+1,total,resultados.sucessos,resultados.erros,str(codigo)
                )
        interrompido=bool(aplicativo and aplicativo.deve_parar())
        if not interrompido:
            excluir_checkpoint_interno()
        return resultados
    except Exception:
        try:
            salvar_checkpoint_interno(codigos,proximo_indice_seguro)
        except Exception:
            pass
        raise
    finally:
        auto.fechar()
        if aplicativo is not None and getattr(aplicativo,"_automacao_atual",None) is auto:
            aplicativo._automacao_atual=None

def principal(planilha_path,sheet,aplicativo=None,indice_inicial=0):
    resultados=Resultados()
    auto=Automacao(status_callback=aplicativo.atualizar_status if aplicativo else None)
    if aplicativo is not None:
        aplicativo._automacao_atual = auto
    proximo_indice_seguro = int(indice_inicial)
    try:
        codigos=carregar_codigos(planilha_path,sheet); total=len(codigos); resultados=Resultados(total)
        if aplicativo: aplicativo.atualizar_progresso(indice_inicial,total,0,0,"")
        auto.iniciar_navegador()
        for indice in range(indice_inicial,total):
            if aplicativo and aplicativo.deve_parar():
                salvar_checkpoint(planilha_path,sheet,indice); break
            codigo=codigos[indice]; numero=indice+1
            try: auto.executar_codigo(codigo); resultados.registrar_sucesso(numero,codigo)
            except AutomacaoError as exc:
                resultados.registrar_erro(numero,codigo,str(exc))
                if aplicativo: aplicativo._add_activity(f"Erro ({exc.tipo}) no código {codigo}. Indo para o próximo...", aplicativo.ERROR)
            salvar_checkpoint(planilha_path,sheet,indice+1)
            proximo_indice_seguro = indice + 1
            if aplicativo: aplicativo.atualizar_progresso(indice+1,total,resultados.sucessos,resultados.erros,str(codigo))
        interrompido=bool(aplicativo and aplicativo.deve_parar())
        if not interrompido: excluir_checkpoint(planilha_path,sheet)
        return resultados
    except PlanilhaError as exc:
        if aplicativo: aplicativo.mostrar_erro(str(exc))
        return resultados
    except Exception:
        # Qualquer falha inesperada (queda de conexão não recuperada,
        # fechamento do navegador/processo, erro de Selenium etc.) preserva
        # o último índice confirmado. O código em execução não é marcado
        # como concluído, portanto será repetido na retomada.
        try:
            salvar_checkpoint(planilha_path, sheet, proximo_indice_seguro)
        except Exception:
            pass
        raise
    finally:
        auto.fechar()
        if aplicativo is not None and getattr(aplicativo, "_automacao_atual", None) is auto:
            aplicativo._automacao_atual = None
