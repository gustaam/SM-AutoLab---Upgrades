<!-- Documentação do projeto. -->

# SM AutoLab

Automação de autorizações no Feegow em um aplicativo desktop para Windows, com planilha virtualizada, histórico, recuperação de execução, atualização integrada e interface moderna.

**Versão em preparação:** `2.99.36`  
**Fonte de verdade da versão:** `VERSION`

## Principais recursos

- **Automação do Feegow:** leitura de códigos do Excel, validação pré-execução, login, autorização sequencial, tratamento de falhas e recuperação da sessão.
- **Planilha virtualizada:** grade de alta capacidade com seleção, edição, copiar/colar, limpar e desfazer/refazer sem criar um widget por linha.
- **Histórico e recuperação:** rascunhos, checkpoints, histórico de planilhas, calendário e retomada segura de execuções.
- **Interface:** dashboard, indicadores de execução, tema claro/escuro, tooltips, layout responsivo e recursos nativos do Windows 11.
- **Atualização integrada:** procura releases compatíveis, valida manifesto e SHA-256, substitui o executável com backup temporário e faz rollback automático se a nova versão não confirmar a inicialização.
- **Segurança operacional:** credenciais ficam fora do código, arquivos de configuração são persistidos localmente e o pipeline verifica dependências e Windows Defender.

## Estrutura do projeto

### Arquivos principais

| Arquivo | Função |
|---|---|
| `main.py` | Inicialização e splash |
| `interface.py` | Interface desktop e planilha |
| `app.py` | Automação e persistência |
| `scripts/validate.py` | Validação estrutural e de release |
| `build_windows.bat` | Build do executável Windows |
| `requirements.txt` | Dependências do projeto |
| `VERSION` | Versão oficial do aplicativo |
| `SM AutoLab.ico` | Ícone do aplicativo e executável |

### Testes

| Arquivo | Escopo |
|---|---|
| `tests/test_app.py` | Testes do núcleo operacional |
| `tests/test_main.py` | Testes de inicialização |
| `tests/test_planilha.py` | Testes da planilha e grade |
| `tests/test_patch.py` | Testes de regressão arquitetural |
| `tests/test_validation.py` | Testes de validação e release |

### Workflows e assets

| Caminho | Função |
|---|---|
| `.github/workflows/validate-main.yml` | Validação contínua da main |
| `.github/workflows/release.yml` | Build e publicação da release |
| `assets/feegow_powered.png` | Identidade visual |
| `assets/laboratorio_principal.png` | Imagem principal da interface |
| `.gitignore` | Exclusões do versionamento |
| `README.md` | Documentação do projeto |

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

A release atualmente publicada é **v2.99.35**.

A **v2.99.32** restaura os tooltips da interface e o efeito de hover dos cards **Executados**, **Não executados** e **Código atual**, mantendo a aba **Não executados** removida.

A **v2.99.33** restaura a numeração visível das linhas no cabeçalho lateral da planilha, inclusive após reabrir a planilha.

A **v2.99.34** corrige o ciclo de vida dos tooltips para que desapareçam ao clicar, perder o foco ou destruir o controle, evitando que o tooltip de **Abrir** fique preso sobre a planilha.

A **v2.99.35** corrige o salvamento da planilha interna, disponibilizando a função de escrita atômica usada pela interface e cobrindo esse caminho com teste de regressão.

A **v2.99.36** adiciona validação pré-execução da planilha, dashboard de execução com métricas de tempo/progresso e atualização segura com backup e rollback automático.

O fluxo valida a base, cria o executável, verifica PE/metadados e Defender, gera um manifesto com SHA-256 e publica o asset. O aplicativo usa esse manifesto para localizar versões compatíveis e validar a integridade antes da atualização.

---

**SM AutoLab** — automação, planilha de alta capacidade e interface desktop em uma base enxuta e verificável.
