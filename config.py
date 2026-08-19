from pathlib import Path
import json

# Defaults
DEFAULT_SITE_URL = "https://franchising.feegow.com/pre-v8.1/extranet/?P=Login&Licenca=15003"
DEFAULT_PORTAL_USUARIO = "labsantamaria@taguatinga"
DEFAULT_PORTAL_SENHA = "acesso123"

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
    """Carrega as configurações persistidas e retorna todas as constantes."""
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
    dados = {
        "SITE_URL": DEFAULT_SITE_URL,
        "PORTAL_USUARIO": DEFAULT_PORTAL_USUARIO,
        "PORTAL_SENHA": DEFAULT_PORTAL_SENHA,
    }
    caminho = _caminho_config()
    temporario = caminho.with_suffix(".tmp")
    temporario.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    temporario.replace(caminho)
    carregar_configuracoes()
    return dados


def salvar_configuracoes(site_url, usuario, senha):
    """Salva as credenciais para uso nas próximas execuções."""
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

    # Atualiza imediatamente esta instância do módulo.
    carregar_configuracoes()
