# Núcleo de automação Feegow: execução Selenium, resultados, checkpoints e persistência.
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException, NoAlertPresentException
# O endereço pode permanecer como padrão público; credenciais nunca ficam no código.
DEFAULT_SITE_URL = "https://franchising.feegow.com/pre-v8.1/extranet/?P=Login&Licenca=15003"
DEFAULT_PORTAL_USUARIO = ""
DEFAULT_PORTAL_SENHA = ""

SITE_URL = DEFAULT_SITE_URL
PORTAL_USUARIO = DEFAULT_PORTAL_USUARIO
PORTAL_SENHA = DEFAULT_PORTAL_SENHA

LOGIN_USER_XPATH = '//input[@type="text" or @type="email"][1]'
LOGIN_PASSWORD_XPATH = '//input[@type="password"][1]'
LOGIN_BUTTON_XPATH = '//button[contains(normalize-space(.), "Entrar")] | //input[@type="submit"]'
PAGE_LINK_XPATH = '//a[@href="?P=Autorizar&Pers=1" or contains(@href, "P=Autorizar&Pers=1")]'
CODE_INPUT_XPATH = '//input[@id="Codigo"]'
CONFIRM_BUTTON_XPATH = '//button[contains(@class,"btn-success") and contains(@class,"btn-block")]'

PAGE_LOAD_TIMEOUT = 45
LOGIN_TIMEOUT = 20
ELEMENT_TIMEOUT = 4
ALERT_TIMEOUT = 0.8
RECOVERY_TIMEOUT = 1.8
INPUT_DELAY = 0.08
CODE_COLUMN = "Codigos"

_CONFIG_FILE = Path.home() / "SM AutoLab" / "feegow_config.json"


def _caminho_config():
    _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    return _CONFIG_FILE


def carregar_configuracoes():
    """Carrega as configurações persistidas; credenciais não existem no código-fonte."""
    global SITE_URL, PORTAL_USUARIO, PORTAL_SENHA

    valores = {
        "SITE_URL": DEFAULT_SITE_URL,
        "PORTAL_USUARIO": DEFAULT_PORTAL_USUARIO,
        "PORTAL_SENHA": DEFAULT_PORTAL_SENHA,
    }

    try:
        caminho = _caminho_config()
        if caminho.exists():
            dados = json.loads(caminho.read_text(encoding="utf-8"))
            for chave in valores:
                valor = dados.get(chave)
                if isinstance(valor, str) and valor.strip():
                    valores[chave] = valor.strip()
    except Exception:
        pass

    SITE_URL = valores["SITE_URL"]
    PORTAL_USUARIO = valores["PORTAL_USUARIO"]
    PORTAL_SENHA = valores["PORTAL_SENHA"]

    return {
        "SITE_URL": SITE_URL,
        "PORTAL_USUARIO": PORTAL_USUARIO,
        "PORTAL_SENHA": PORTAL_SENHA,
    }


def restaurar_configuracoes():
    """Restaura o endereço padrão e limpa as credenciais salvas."""
    dados = {
        "SITE_URL": DEFAULT_SITE_URL,
        "PORTAL_USUARIO": DEFAULT_PORTAL_USUARIO,
        "PORTAL_SENHA": DEFAULT_PORTAL_SENHA,
    }
    caminho = _caminho_config()
    atomic_write_json(caminho, dados)
    carregar_configuracoes()
    return dados


def salvar_configuracoes(site_url, usuario, senha):
    """Salva as credenciais somente na configuração local do usuário."""
    site_url = str(site_url).strip()
    usuario = str(usuario).strip()
    senha = str(senha)

    if not site_url:
        raise ValueError("O endereço do Feegow não pode ficar vazio.")
    if not usuario:
        raise ValueError("O usuário não pode ficar vazio.")
    if not senha:
        raise ValueError("A senha não pode ficar vazia.")

    dados = {
        "SITE_URL": site_url,
        "PORTAL_USUARIO": usuario,
        "PORTAL_SENHA": senha,
    }

    caminho = _caminho_config()
    temporario = caminho.with_suffix(".tmp")
    temporario.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    temporario.replace(caminho)

    carregar_configuracoes()


# Armazenamento seguro (unificado de storage_safe.py).

def backup_path(path: Path) -> Path:
    path = Path(path)
    return path.with_name(path.name + ".bak")


def atomic_write_text(path: Path, text: str, *, backup: bool = True) -> None:
    """Grava no mesmo diretório e substitui o destino atomicamente."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(str(text))
            handle.flush()
            os.fsync(handle.fileno())

        if backup and path.exists():
            shutil.copy2(path, backup_path(path))

        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def atomic_write_json(
    path: Path,
    payload: Any,
    *,
    backup: bool = True,
) -> None:
    atomic_write_text(
        Path(path),
        json.dumps(payload, ensure_ascii=False, indent=2),
        backup=backup,
    )


def read_json_with_backup(path: Path, default: Any = None) -> Any:
    """Lê o JSON principal; em caso de corrupção, tenta o backup anterior."""
    path = Path(path)
    last_error: Exception | None = None
    for candidate in (path, backup_path(path)):
        if not candidate.exists():
            continue
        try:
            with candidate.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            last_error = exc
    if last_error is not None:
        return default
    return default



def _recarregar_configuracao_runtime():
    dados = carregar_configuracoes()
    globals()["SITE_URL"] = dados["SITE_URL"]
    globals()["PORTAL_USUARIO"] = dados["PORTAL_USUARIO"]
    globals()["PORTAL_SENHA"] = dados["PORTAL_SENHA"]
    return dados


class AutomacaoError(Exception):
    def __init__(self, mensagem, tipo="erro_site", recuperado=False):
        super().__init__(mensagem); self.tipo=tipo; self.recuperado=recuperado

class Automacao:
    def __init__(self, status_callback=None):
        self.driver=None; self.status_callback=status_callback

    def _status(self,t):
        if self.status_callback: self.status_callback(t)

    @staticmethod
    def _diagnostico_path():
        return Path.home() / "SM AutoLab" / "selenium_runtime.log"

    def _registrar_diagnostico(self, mensagem):
        """Registra diagnóstico técnico sem credenciais nem códigos."""
        try:
            caminho = self._diagnostico_path()
            caminho.parent.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with caminho.open("a", encoding="utf-8") as handle:
                handle.write(f"[{stamp}] {mensagem}\n")
        except Exception:
            pass

    @staticmethod
    def _bundle_cft():
        bundle_root = getattr(sys, "_MEIPASS", None)
        if not bundle_root:
            return None

        root = Path(bundle_root) / "chrome_for_testing"
        browser = root / "chrome-win64" / "chrome.exe"
        driver = root / "chromedriver-win64" / "chromedriver.exe"
        version_file = root / "version.txt"

        if not browser.is_file() or not driver.is_file():
            return None

        try:
            version = version_file.read_text(encoding="utf-8").strip() or "unknown"
        except OSError:
            version = "unknown"

        return root, browser, driver, version

    @staticmethod
    def _cache_cft(root, version):
        """Copia o navegador embutido para uma pasta estável antes de executá-lo."""
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "SM AutoLab" / "ChromeForTesting"
        destination = base / version

        browser = destination / "chrome-win64" / "chrome.exe"
        driver = destination / "chromedriver-win64" / "chromedriver.exe"
        if browser.is_file() and driver.is_file():
            return destination, browser, driver

        base.mkdir(parents=True, exist_ok=True)
        temporary = base / f".{version}.tmp-{os.getpid()}"
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)

        shutil.copytree(root, temporary)
        if destination.exists():
            shutil.rmtree(destination, ignore_errors=True)
        temporary.replace(destination)

        if not browser.is_file() or not driver.is_file():
            raise FileNotFoundError(
                f"Chrome for Testing copiado de forma incompleta para {destination}"
            )
        return destination, browser, driver

    def _criar_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-default-apps")
        options.add_argument("--no-first-run")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--start-minimized")

        try:
            import selenium
            selenium_version = selenium.__version__
        except Exception:
            selenium_version = "desconhecido"

        self._registrar_diagnostico(
            "Início do driver; "
            f"frozen={getattr(sys, 'frozen', False)}; "
            f"meipass={getattr(sys, '_MEIPASS', '')}; "
            f"selenium={selenium_version}"
        )

        bundle = self._bundle_cft()
        if bundle is not None:
            root, bundled_browser, bundled_driver, version = bundle
            self._registrar_diagnostico(
                f"CFT embutido detectado: versão={version}; root={root}; "
                f"browser={bundled_browser}; driver={bundled_driver}"
            )
            self._status("Selenium: preparando navegador integrado...")
            try:
                cache_root, browser_path, driver_path = self._cache_cft(root, version)
                self._registrar_diagnostico(
                    f"CFT preparado em cache estável: root={cache_root}; "
                    f"browser={browser_path}; driver={driver_path}"
                )
                options.binary_location = str(browser_path)
                service = Service(executable_path=str(driver_path))
                driver = webdriver.Chrome(service=service, options=options)
                driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
                capabilities = getattr(driver, "capabilities", {}) or {}
                chrome_caps = capabilities.get("chrome", {}) or {}
                self._registrar_diagnostico(
                    "Driver iniciado com CFT integrado: "
                    f"browserVersion={capabilities.get('browserVersion', '')}; "
                    f"driverVersion={chrome_caps.get('chromedriverVersion', '')}; "
                    f"current_url={getattr(driver, 'current_url', '')}"
                )
                self._status("Selenium: navegador integrado iniciado.")
                try:
                    driver.minimize_window()
                except WebDriverException:
                    pass
                return driver
            except Exception as exc:
                self._registrar_diagnostico(
                    f"Falha ao iniciar CFT integrado: {type(exc).__name__}: {exc!r}"
                )
                raise AutomacaoError(
                    "Não foi possível iniciar o Chrome for Testing integrado. "
                    f"Detalhes técnicos foram registrados em {self._diagnostico_path()}. "
                    f"Erro: {exc}",
                    "navegador",
                ) from exc

        self._registrar_diagnostico(
            "CFT embutido não disponível; usando webdriver.Chrome() com Selenium Manager."
        )
        self._status("Selenium: abrindo navegador...")
        try:
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
            capabilities = getattr(driver, "capabilities", {}) or {}
            chrome_caps = capabilities.get("chrome", {}) or {}
            self._registrar_diagnostico(
                "Driver iniciado via Selenium Manager: "
                f"browserVersion={capabilities.get('browserVersion', '')}; "
                f"driverVersion={chrome_caps.get('chromedriverVersion', '')}; "
                f"current_url={getattr(driver, 'current_url', '')}"
            )
            try:
                driver.minimize_window()
            except WebDriverException:
                pass
            return driver
        except Exception as exc:
            self._registrar_diagnostico(
                f"Falha no webdriver.Chrome(): {type(exc).__name__}: {exc!r}"
            )
            raise AutomacaoError(
                "Não foi possível iniciar o navegador da automação. "
                f"Detalhes técnicos foram registrados em {self._diagnostico_path()}. "
                f"Erro: {exc}",
                "navegador",
            ) from exc

    def iniciar_navegador(self):
        dados = _recarregar_configuracao_runtime()
        if not dados["PORTAL_USUARIO"] or not dados["PORTAL_SENHA"]:
            mensagem = "Configure o usuário e a senha do Feegow em Configurações antes de iniciar."
            self._status("Configuração necessária")
            raise AutomacaoError(mensagem, "configuracao")
        self._status("Abrindo o Feegow...")
        self.driver=self._criar_driver()
        try:
            self.driver.get(SITE_URL)
            self._registrar_diagnostico(
                f"Feegow carregado: url={self.driver.current_url}; title={self.driver.title!r}"
            )
        except Exception as exc:
            self._registrar_diagnostico(
                f"Falha ao carregar Feegow: {type(exc).__name__}: {exc!r}; "
                f"url={getattr(self.driver, 'current_url', '')}"
            )
            raise
        self._fazer_login()
        self._abrir_autorizacao()

    def _fazer_login(self):
        try:
            self._status("Entrando no portal...")
            u=WebDriverWait(self.driver,LOGIN_TIMEOUT,poll_frequency=.2).until(EC.visibility_of_element_located((By.XPATH,LOGIN_USER_XPATH)))
            p=WebDriverWait(self.driver,LOGIN_TIMEOUT,poll_frequency=.2).until(EC.visibility_of_element_located((By.XPATH,LOGIN_PASSWORD_XPATH)))
            self._registrar_diagnostico("Campos de login encontrados.")
            u.clear(); u.send_keys(PORTAL_USUARIO); p.clear(); p.send_keys(PORTAL_SENHA)
            WebDriverWait(self.driver,LOGIN_TIMEOUT,poll_frequency=.2).until(EC.element_to_be_clickable((By.XPATH,LOGIN_BUTTON_XPATH))).click()
            self._registrar_diagnostico(
                f"Botão de login acionado; url={self.driver.current_url}; title={self.driver.title!r}"
            )
            WebDriverWait(self.driver,PAGE_LOAD_TIMEOUT,poll_frequency=.2).until(EC.presence_of_element_located((By.XPATH,PAGE_LINK_XPATH)))
            self._registrar_diagnostico(
                f"Login concluído; link de autorização encontrado; url={self.driver.current_url}"
            )
        except TimeoutException as e:
            self._registrar_diagnostico(
                f"Timeout no login; url={getattr(self.driver, 'current_url', '')}; title={getattr(self.driver, 'title', '')!r}"
            )
            raise AutomacaoError("Falha no login: tempo excedido.","login") from e
        except WebDriverException as e:
            self._registrar_diagnostico(
                f"WebDriverError no login: {type(e).__name__}: {e!r}"
            )
            raise AutomacaoError("Falha no navegador durante o login.","navegador") from e
        except Exception as e:
            self._registrar_diagnostico(
                f"Erro geral no login: {type(e).__name__}: {e!r}"
            )
            raise AutomacaoError(f"Falha no login: {e}","login") from e

    def _abrir_autorizacao(self):
        try:
            self._status("Abrindo Autorizar Procedimento...")
            WebDriverWait(self.driver,PAGE_LOAD_TIMEOUT,poll_frequency=.2).until(EC.element_to_be_clickable((By.XPATH,PAGE_LINK_XPATH))).click()
            self._registrar_diagnostico(
                f"Link de autorização acionado; url={self.driver.current_url}; title={self.driver.title!r}"
            )
            WebDriverWait(self.driver,PAGE_LOAD_TIMEOUT,poll_frequency=.2).until(EC.presence_of_element_located((By.XPATH,CODE_INPUT_XPATH)))
            self._registrar_diagnostico(
                f"Campo de código encontrado; url={self.driver.current_url}"
            )
        except TimeoutException as e:
            self._registrar_diagnostico(
                f"Timeout ao abrir Autorizar Procedimento; url={getattr(self.driver, 'current_url', '')}; title={getattr(self.driver, 'title', '')!r}"
            )
            raise AutomacaoError("Não foi possível abrir Autorizar Procedimento.","autorizacao") from e
        except WebDriverException as e:
            self._registrar_diagnostico(
                f"WebDriverError ao abrir autorização: {type(e).__name__}: {e!r}"
            )
            raise AutomacaoError("O navegador apresentou um problema ao abrir Autorizar Procedimento.","navegador") from e

    def executar_codigo(self,codigo):
        try:
            self._executar_codigo_uma_vez(codigo)
        except Exception as e:
            tipo=self._classificar_erro(e); self.tentar_fechar_alerta()
            recuperado=self.recuperar_apos_erro(tipo)
            msg=str(e)
            raise AutomacaoError(msg,tipo,recuperado) from e

    def _executar_codigo_uma_vez(self,codigo):
        try:
            campo=WebDriverWait(self.driver,ELEMENT_TIMEOUT,poll_frequency=.15).until(EC.element_to_be_clickable((By.XPATH,CODE_INPUT_XPATH)))
            campo.click(); campo.clear(); sleep(INPUT_DELAY); campo.send_keys(str(codigo),Keys.ENTER)
            WebDriverWait(self.driver,ELEMENT_TIMEOUT,poll_frequency=.15).until(EC.element_to_be_clickable((By.XPATH,CONFIRM_BUTTON_XPATH))).click()
            self.tentar_fechar_alerta()
            WebDriverWait(self.driver,RECOVERY_TIMEOUT,poll_frequency=.15).until(EC.element_to_be_clickable((By.XPATH,CODE_INPUT_XPATH)))
        except TimeoutException as e: raise AutomacaoError("O site não respondeu a tempo.","timeout") from e
        except (StaleElementReferenceException,NoSuchElementException) as e: raise AutomacaoError("O elemento da tela mudou ou desapareceu.","elemento") from e
        except ElementClickInterceptedException as e: raise AutomacaoError("O site bloqueou o clique do próximo elemento.","elemento") from e
        except WebDriverException as e: raise AutomacaoError("O navegador perdeu a comunicação com a página.","navegador") from e

    def _classificar_erro(self,e):
        return e.tipo if isinstance(e,AutomacaoError) else ("navegador" if isinstance(e,WebDriverException) else "erro_site")

    def recuperar_apos_erro(self,tipo):
        if self.driver is None or not self._navegador_vivo(): return self._reiniciar_navegador()
        try:
            self._status("Recuperando a tela para o próximo código...")
            self.tentar_fechar_alerta()
            WebDriverWait(self.driver,RECOVERY_TIMEOUT,poll_frequency=.15).until(EC.presence_of_element_located((By.XPATH,CODE_INPUT_XPATH)))
            return True
        except Exception: return self._reiniciar_navegador()

    def _navegador_vivo(self):
        try: _=self.driver.current_url; return True
        except Exception: return False

    def _reiniciar_navegador(self):
        dados = _recarregar_configuracao_runtime()
        if not dados["PORTAL_USUARIO"] or not dados["PORTAL_SENHA"]:
            raise AutomacaoError("Configure o usuário e a senha do Feegow em Configurações antes de continuar.", "configuracao")
        self._status("Recuperando o navegador e entrando novamente...")
        self.fechar()
        self.driver=self._criar_driver(); self.driver.get(SITE_URL); self._fazer_login(); self._abrir_autorizacao(); self._status("Navegador recuperado. Continuando..."); return True

    def tentar_fechar_alerta(self):
        if self.driver is None:
            return False
        try:
            self.driver.switch_to.alert.accept()
            return True
        except NoAlertPresentException:
            pass
        except WebDriverException:
            return False

        try:
            WebDriverWait(self.driver, 0.18, poll_frequency=0.05).until(
                EC.alert_is_present()
            )
            self.driver.switch_to.alert.accept()
            return True
        except (TimeoutException, NoAlertPresentException, WebDriverException):
            return False

    def fechar(self):
        if self.driver:
            try: self.driver.quit()
            except Exception: pass
            self.driver=None


class PlanilhaError(Exception):
    """Erro de leitura ou validação da planilha de códigos."""


@dataclass
class ResultadoCodigo:
    numero: int
    codigo: str
    status: str
    erro: str = ""
    horario: str = ""


class Resultados:
    """Acumula os resultados da execução dos códigos em O(1) para métricas."""

    def __init__(self, total=0):
        self.total_planejado = total
        self.itens = []
        self.codigos_erros = []
        self.erros_detalhes = []
        self._sucessos = 0
        self._erros = 0

    def registrar_sucesso(self, numero, codigo):
        self.itens.append(
            ResultadoCodigo(
                numero,
                str(codigo),
                "Sucesso",
                horario=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        )
        self._sucessos += 1

    def registrar_erro(self, numero, codigo, erro):
        codigo = str(codigo)
        self.itens.append(
            ResultadoCodigo(
                numero,
                codigo,
                "Erro",
                erro=str(erro),
                horario=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        )
        if codigo not in self.codigos_erros:
            self.codigos_erros.append(codigo)
        self.erros_detalhes.append(
            {
                "numero": int(numero),
                "codigo": codigo,
                "erro": str(erro),
                "horario": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        self._erros += 1

    @property
    def processados(self):
        return len(self.itens)

    @property
    def sucessos(self):
        return self._sucessos

    @property
    def erros(self):
        return self._erros


def carregar_codigos(caminho, sheet):
    """Lê os códigos da coluna configurada na planilha Excel."""
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


def caminho_checkpoint(planilha_path, sheet):
    p = Path(planilha_path)
    return p.parent / f".{p.stem}_autolab_pagina_{sheet + 1}_checkpoint.json"


def salvar_checkpoint(planilha_path, sheet, proximo_indice):
    c = caminho_checkpoint(planilha_path, sheet)
    atomic_write_json(
        c,
        {
            "planilha": str(Path(planilha_path).resolve()),
            "sheet": sheet,
            "proximo_indice": proximo_indice,
        },
    )


def ler_checkpoint(planilha_path, sheet):
    c = caminho_checkpoint(planilha_path, sheet)
    if not c.exists():
        return None
    try:
        d = read_json_with_backup(c, {})
        if d.get("planilha") != str(Path(planilha_path).resolve()) or d.get("sheet") != sheet:
            return None
        x = int(d.get("proximo_indice", 0))
        return x if x >= 0 else None
    except Exception:
        return None


def excluir_checkpoint(planilha_path, sheet):
    try:
        c = caminho_checkpoint(planilha_path, sheet)
        if c.exists():
            c.unlink()
    except OSError:
        pass


def _fingerprint_codigos(codigos):
    payload = "\n".join(str(c) for c in codigos).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def caminho_checkpoint_interno():
    return Path.home() / "SM AutoLab" / "interno_checkpoint.json"


def salvar_checkpoint_interno(codigos, proximo_indice):
    c = caminho_checkpoint_interno()
    c.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "fingerprint": _fingerprint_codigos(codigos),
        "total": len(codigos),
        "proximo_indice": int(proximo_indice),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    atomic_write_json(c, payload)


def ler_checkpoint_interno(codigos):
    c = caminho_checkpoint_interno()
    if not c.exists():
        return None
    try:
        d = read_json_with_backup(c, {})
        if d.get("fingerprint") != _fingerprint_codigos(codigos):
            return None
        x = int(d.get("proximo_indice", 0))
        return x if 0 <= x <= len(codigos) else None
    except Exception:
        return None


def excluir_checkpoint_interno():
    try:
        c = caminho_checkpoint_interno()
        if c.exists():
            c.unlink()
    except OSError:
        pass


def principal_interno(codigos, aplicativo=None, indice_inicial=0):
    codigos = [str(c).strip() for c in codigos if str(c).strip()]
    resultados = Resultados(len(codigos))
    auto = Automacao(status_callback=aplicativo.atualizar_status if aplicativo else None)
    if aplicativo is not None:
        aplicativo._automacao_atual = auto
    proximo_indice_seguro = int(indice_inicial)
    try:
        total = len(codigos)
        if total == 0:
            return resultados
        if aplicativo:
            aplicativo.atualizar_progresso(indice_inicial, total, 0, 0, "")
        auto.iniciar_navegador()
        for indice in range(indice_inicial, total):
            if aplicativo and aplicativo.deve_parar():
                salvar_checkpoint_interno(codigos, indice)
                break
            codigo = codigos[indice]
            numero = indice + 1
            try:
                auto.executar_codigo(codigo)
                resultados.registrar_sucesso(numero, codigo)
            except AutomacaoError as exc:
                resultados.registrar_erro(numero, codigo, str(exc))
                if aplicativo:
                    registrar = getattr(aplicativo, "_registrar_codigo_erro_historico", None)
                    if callable(registrar):
                        registrar(codigo, numero, str(exc))
                    aplicativo._add_activity(
                        f"Erro ({exc.tipo}) no código {codigo}. Indo para o próximo...",
                        aplicativo.ERROR,
                    )
            salvar_checkpoint_interno(codigos, indice + 1)
            proximo_indice_seguro = indice + 1
            if aplicativo:
                aplicativo.atualizar_progresso(
                    indice + 1,
                    total,
                    resultados.sucessos,
                    resultados.erros,
                    str(codigo),
                )
        interrompido = bool(aplicativo and aplicativo.deve_parar())
        if not interrompido:
            excluir_checkpoint_interno()
        return resultados
    except Exception:
        try:
            salvar_checkpoint_interno(codigos, proximo_indice_seguro)
        except Exception:
            pass
        raise
    finally:
        auto.fechar()
        if aplicativo is not None and getattr(aplicativo, "_automacao_atual", None) is auto:
            aplicativo._automacao_atual = None


def principal(planilha_path, sheet, aplicativo=None, indice_inicial=0):
    resultados = Resultados()
    auto = Automacao(status_callback=aplicativo.atualizar_status if aplicativo else None)
    if aplicativo is not None:
        aplicativo._automacao_atual = auto
    proximo_indice_seguro = int(indice_inicial)
    try:
        codigos = carregar_codigos(planilha_path, sheet)
        total = len(codigos)
        resultados = Resultados(total)
        if aplicativo:
            aplicativo.atualizar_progresso(indice_inicial, total, 0, 0, "")
        auto.iniciar_navegador()
        for indice in range(indice_inicial, total):
            if aplicativo and aplicativo.deve_parar():
                salvar_checkpoint(planilha_path, sheet, indice)
                break
            codigo = codigos[indice]
            numero = indice + 1
            try:
                auto.executar_codigo(codigo)
                resultados.registrar_sucesso(numero, codigo)
            except AutomacaoError as exc:
                resultados.registrar_erro(numero, codigo, str(exc))
                if aplicativo:
                    registrar = getattr(aplicativo, "_registrar_codigo_erro_historico", None)
                    if callable(registrar):
                        registrar(codigo, numero, str(exc))
                    aplicativo._add_activity(
                        f"Erro ({exc.tipo}) no código {codigo}. Indo para o próximo...",
                        aplicativo.ERROR,
                    )
            salvar_checkpoint(planilha_path, sheet, indice + 1)
            proximo_indice_seguro = indice + 1
            if aplicativo:
                aplicativo.atualizar_progresso(
                    indice + 1,
                    total,
                    resultados.sucessos,
                    resultados.erros,
                    str(codigo),
                )
        interrompido = bool(aplicativo and aplicativo.deve_parar())
        if not interrompido:
            excluir_checkpoint(planilha_path, sheet)
        return resultados
    except PlanilhaError as exc:
        if aplicativo:
            aplicativo.mostrar_erro(str(exc))
        return resultados
    except Exception:
        try:
            salvar_checkpoint(planilha_path, sheet, proximo_indice_seguro)
        except Exception:
            pass
        raise
    finally:
        auto.fechar()
        if aplicativo is not None and getattr(aplicativo, "_automacao_atual", None) is auto:
            aplicativo._automacao_atual = None
