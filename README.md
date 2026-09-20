# SM AutoLab

Automação de autorizações no Feegow em um aplicativo desktop para Windows, com planilha virtualizada, histórico, recuperação de execução, atualização integrada e interface moderna.

**Versão atual:** `2.99.27`  
**Fonte de verdade da versão:** `VERSION`

## Principais recursos

- **Automação do Feegow:** leitura de códigos do Excel, login, autorização sequencial, tratamento de falhas e recuperação da sessão.
- **Planilha virtualizada:** grade de alta capacidade com seleção, edição, copiar/colar, limpar e desfazer/refazer sem criar um widget por linha.
- **Histórico e recuperação:** rascunhos, checkpoints, histórico de planilhas, calendário e retomada segura de execuções.
- **Interface:** dashboard, indicadores de execução, tema claro/escuro, tooltips, layout responsivo e recursos nativos do Windows 11.
- **Atualização integrada:** procura releases compatíveis, valida o manifesto e o SHA-256 e substitui o executável de forma segura.
- **Segurança operacional:** credenciais ficam fora do código, arquivos de configuração são persistidos localmente e o pipeline verifica dependências e Windows Defender.

## Estrutura do projeto

### Arquivos principais

| Arquivo | Função |
|---|---|
| `main.py` | Entrada da aplicação. Inicia o splash, configura DPI e conecta o bootstrap da interface às camadas consolidadas. |
| `interface.py` | Interface principal. Reúne a planilha virtualizada, histórico/calendário, edição, undo/redo, atualização integrada e integração visual com o Windows. |
| `app.py` | Núcleo operacional. Controla Selenium/Feegow, leitura de planilhas, resultados, checkpoints e configuração persistente. |
| `patch.py` | Camada única de compatibilidade. Mantém correções históricas consolidadas e aplica sua sequência sem voltar a criar módulos paralelos. |
| `scripts/validate.py` | Validador central de arquitetura, versão, dependências, workflows e executável. |
| `build_windows.bat` | Build manual para Windows, com validações, testes, metadados e geração do executável via PyInstaller. |
| `requirements.txt` | Dependências de runtime com versões fixadas. |
| `VERSION` | Versão oficial usada pelo build, CI e release. |
| `SM AutoLab.ico` | Ícone usado no executável e na identidade do aplicativo. |

### Testes

| Arquivo | Escopo |
|---|---|
| `tests/test_app.py` | Automação, resultados, checkpoints e persistência. |
| `tests/test_main.py` | Bootstrap, dashboard e integração da camada principal. |
| `tests/test_planilha.py` | Planilha virtualizada, histórico, calendário e interações da grade. |
| `tests/test_patch.py` | Compatibilidade e aplicação das correções consolidadas. |
| `tests/test_validation.py` | Regras do validador estrutural e de release. |

### Workflows e assets

| Caminho | Função |
|---|---|
| `.github/workflows/validate-main.yml` | CI da `main`: arquitetura, dependências, sintaxe, testes, integração e Defender; também prepara a release quando aplicável. |
| `.github/workflows/release.yml` | Build oficial, validação do PE/metadados, geração do manifesto, SHA-256 e publicação da release. |
| `assets/feegow_powered.png` | Identidade visual exibida na interface. |
| `assets/laboratorio_principal.png` | Imagem principal usada na interface/splash. |
| `.gitignore` | Arquivos temporários e artefatos que não devem ser versionados. |
| `README.md` | Documentação e mapa rápido da base. |

## Arquitetura

A produção foi compactada em quatro módulos:

`main.py` → inicialização e integração da UI  
`interface.py` → interface e planilha  
`app.py` → automação e persistência  
`patch.py` → compatibilidade histórica

A regra de manutenção é evitar implementações paralelas: novos ajustes devem entrar na implementação canônica correspondente.

## Validação e qualidade

O projeto valida continuamente:

- arquitetura e ausência de arquivos legados;
- versões fixadas de Python, pip e dependências;
- referências das GitHub Actions;
- sintaxe e suíte de testes;
- integração da aplicação;
- metadados e estrutura do executável;
- Windows Defender.

O CI utiliza **Python 3.14.7** e **pip 26.2.1**. O build oficial usa **PyInstaller 6.22.2**.

## Build do Windows

O build produz um único executável:

`dist/SM AutoLab.exe`

O executável recebe ícone, assets, versão e metadados do produto durante a geração. Os arquivos de metadados temporários não fazem parte da árvore versionada.

## Release e atualização

A release atualmente publicada é **v2.99.27**.

O fluxo valida a base, cria o executável, verifica PE/metadados e Defender, gera um manifesto com SHA-256 e publica o asset. O aplicativo usa esse manifesto para localizar versões compatíveis e validar a integridade antes da atualização.

---

**SM AutoLab** — automação, planilha de alta capacidade e interface desktop em uma base enxuta e verificável.
