from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException
from config import *

# As configurações do portal podem ser alteradas pela interface.
# Recarregamos antes de iniciar ou recuperar o navegador.

class AutomacaoError(Exception):
    def __init__(self, mensagem, tipo="erro_site", recuperado=False):
        super().__init__(mensagem); self.tipo=tipo; self.recuperado=recuperado

class Automacao:
    def __init__(self, status_callback=None):
        self.driver=None; self.status_callback=status_callback
    def _status(self,t):
        if self.status_callback: self.status_callback(t)
    def iniciar_navegador(self):
        carregar_configuracoes()
        self._status("Abrindo o Feegow...")
        self.driver=webdriver.Chrome()
        self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        self.driver.get(SITE_URL); self._fazer_login(); self._abrir_autorizacao()
    def _fazer_login(self):
        try:
            self._status("Entrando no portal...")
            u=WebDriverWait(self.driver,LOGIN_TIMEOUT,poll_frequency=.2).until(EC.visibility_of_element_located((By.XPATH,LOGIN_USER_XPATH)))
            p=WebDriverWait(self.driver,LOGIN_TIMEOUT,poll_frequency=.2).until(EC.visibility_of_element_located((By.XPATH,LOGIN_PASSWORD_XPATH)))
            u.clear(); u.send_keys(PORTAL_USUARIO); p.clear(); p.send_keys(PORTAL_SENHA)
            WebDriverWait(self.driver,LOGIN_TIMEOUT,poll_frequency=.2).until(EC.element_to_be_clickable((By.XPATH,LOGIN_BUTTON_XPATH))).click()
            WebDriverWait(self.driver,PAGE_LOAD_TIMEOUT,poll_frequency=.2).until(EC.presence_of_element_located((By.XPATH,PAGE_LINK_XPATH)))
        except TimeoutException as e: raise AutomacaoError("Falha no login: tempo excedido.","login") from e
        except WebDriverException as e: raise AutomacaoError("Falha no navegador durante o login.","navegador") from e
        except Exception as e: raise AutomacaoError(f"Falha no login: {e}","login") from e
    def _abrir_autorizacao(self):
        try:
            self._status("Abrindo Autorizar Procedimento...")
            WebDriverWait(self.driver,PAGE_LOAD_TIMEOUT,poll_frequency=.2).until(EC.element_to_be_clickable((By.XPATH,PAGE_LINK_XPATH))).click()
            WebDriverWait(self.driver,PAGE_LOAD_TIMEOUT,poll_frequency=.2).until(EC.presence_of_element_located((By.XPATH,CODE_INPUT_XPATH)))
        except TimeoutException as e: raise AutomacaoError("Não foi possível abrir Autorizar Procedimento.","autorizacao") from e
        except WebDriverException as e: raise AutomacaoError("O navegador apresentou um problema ao abrir Autorizar Procedimento.","navegador") from e
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
        carregar_configuracoes()
        self._status("Recuperando o navegador e entrando novamente...")
        self.fechar()
        self.driver=webdriver.Chrome(); self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT); self.driver.get(SITE_URL); self._fazer_login(); self._abrir_autorizacao(); self._status("Navegador recuperado. Continuando..."); return True
    def tentar_fechar_alerta(self):
        try:
            WebDriverWait(self.driver,ALERT_TIMEOUT,poll_frequency=.1).until(EC.alert_is_present()); self.driver.switch_to.alert.accept(); return True
        except Exception: return False
    def fechar(self):
        if self.driver:
            try: self.driver.quit()
            except Exception: pass
            self.driver=None
