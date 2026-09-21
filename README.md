# SM AutoLab

Automação de autorizações no Feegow em um aplicativo desktop para Windows, com planilha virtualizada, histórico, recuperação de execução, atualização integrada e interface moderna.

**Versão em preparação:** `2.99.29`  
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
| `main.py` | Ponto de entrada da aplicação: configura o ambiente do Windows, executa o splash e inicializa a interface principal. |
| `interface.py` | Camada de interface desktop: janela principal, planilha, histórico, configurações, atualização integrada e integração visual com o Windows. |
| `app.py` | Núcleo operacional: automação Selenium/Feegow, leitura de dados, resultados, checkpoints e persistência de configurações. |
| `scripts/validate.py` | Validador do projeto: arquitetura, dependências, workflows, versão e integridade do executável. |
| `build_windows.bat` | Script de build para Windows: valida o ambiente, executa testes e gera o executável com PyInstaller. |
| `requirements.txt` | Define as dependências Python do projeto com suas versões utilizadas no ambiente de execução e build. |
| `VERSION` | Armazena a versão oficial do aplicativo usada pelo build, CI e release. |
| `SM AutoLab.ico` | Arquivo de identidade visual usado como ícone do aplicativo e do executável. |

### Testes

| Arquivo | Escopo |
|---|---|
| `tests/test_app.py` | Testes do núcleo operacional, resultados, checkpoints e persistência. |
| `tests/test_main.py` | Testes do ponto de entrada, inicialização e integração da aplicação. |
| `tests/test_planilha.py` | Testes da planilha, seleção, edição, navegação e comportamento da grade. |
| `tests/test_patch.py` | Testes de regressão da arquitetura e das regras de compatibilidade do projeto. |
| `tests/test_validation.py` | Testes das regras de validação estrutural, versão, qualidade e release. |

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

A produção foi compactada em três módulos:

`main.py` → inicialização e splash  
`interface.py` → interface, planilha, histórico e atualização integrada  
`app.py` → automação e persistência

As correções históricas agora estão consolidadas diretamente nesses módulos. A regra de manutenção é evitar implementações paralelas: novos ajustes devem entrar na implementação canônica correspondente.

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

A release atualmente publicada é **v2.99.28**.

A **v2.99.29** está em preparação com a consolidação definitiva da UI, correção do hover de Aparência, seleção determinística da planilha e remoção das camadas de compatibilidade legadas e do patch runtime.

O fluxo valida a base, cria o executável, verifica PE/metadados e Defender, gera um manifesto com SHA-256 e publica o asset. O aplicativo usa esse manifesto para localizar versões compatíveis e validar a integridade antes da atualização.

---

**SM AutoLab** — automação, planilha de alta capacidade e interface desktop em uma base enxuta e verificável.
