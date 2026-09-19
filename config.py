from pathlib import Path
import json
import os
import shutil
import tempfile
from typing import Any

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


def restore_backup(path: Path) -> bool:
    path = Path(path)
    backup = backup_path(path)
    if not backup.exists():
        return False
    try:
        shutil.copy2(backup, path)
        return True
    except OSError:
        return False