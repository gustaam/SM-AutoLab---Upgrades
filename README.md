<!-- Documentação completa do aplicativo, arquitetura, recursos, operação e release. -->

# SM AutoLab

Aplicativo Windows para automação de autorizações no Feegow, com execução de códigos a partir de planilhas, recuperação segura de execuções, histórico, atualização integrada e interface moderna.

**Versão atual no código:** `2.99.59`  
**Fonte de verdade da versão:** `VERSION`

## Principais recursos

- **Automação do Feegow:** leitura de códigos do Excel, login, autorização sequencial, tratamento de falhas, recuperação da página e recuperação do navegador.
- **Planilha virtualizada:** grade de alta capacidade com seleção, edição, copiar/colar, recortar, limpar, desfazer/refazer e renderização apenas do conteúdo visível.
- **Persistência e recuperação:** checkpoints, histórico de planilhas, rascunhos, estado processado e retomada segura sem reabrir ou reaproveitar indevidamente uma planilha já processada.
- **Histórico de execução:** detalhes de uma execução ficam agrupados; a área de histórico de erros é apresentada somente quando existem erros.
- **Interface:** dashboard, métricas de execução, progresso, tooltips, layout responsivo, tema claro/escuro e integração nativa com Windows 11.
- **Rolagem:** barras personalizadas com polegar arredondado, setas de navegação, arraste, paginação no trilho, repetição e estados de hover.
- **Atualização integrada:** descoberta de releases, validação do manifesto e SHA-256, substituição segura do executável, backup e rollback automático.
- **Segurança operacional:** credenciais ficam fora do código, gravações críticas usam escrita atômica com backup e o pipeline verifica dependências, estrutura e Windows Defender.

## Estrutura do projeto

### Produção

| Arquivo | Função |
|---|---|
| `main.py` | Ponto de entrada, inicialização e splash |
| `interface.py` | Interface desktop, planilha virtualizada, histórico, atualização e integração Windows 11 |
| `app.py` | Automação Selenium, resultados, checkpoints, configuração e persistência |
| `patch.py` | Camada histórica de compatibilidade ainda usada pelo runtime |

A produção foi consolidada nesses quatro módulos. `patch.py` permanece separado deliberadamente para preservar compatibilidade; novos recursos devem ser implementados nos módulos canônicos.

### Validação, build e dependências

| Caminho | Função |
|---|---|
| `scripts/validate.py` | Validação de arquitetura, versão, dependências, workflows, qualidade e executável |
| `scripts/smoke_ui.py` | Smoke test da interface |
| `build_windows.bat` | Build local do executável Windows |
| `requirements.txt` | Dependências do projeto |
| `VERSION` | Versão oficial do aplicativo |
| `SM AutoLab.ico` | Ícone do aplicativo |

### Testes

| Arquivo | Escopo |
|---|---|
| `tests/test_app.py` | Persistência, armazenamento seguro e resultados |
| `tests/test_main.py` | Inicialização e integração |
| `tests/test_planilha.py` | Planilha, seleção, edição, virtualização e persistência |
| `tests/test_patch.py` | Regressões de compatibilidade |
| `tests/test_validation.py` | Validadores, workflows, versão e executável |
| `tests/test_history.py` | Histórico, recuperação e retomada |

### Workflows e assets

| Caminho | Função |
|---|---|
| `.github/workflows/validate-main.yml` | CI da `main`: validação, dependências, testes, integração, smoke test e Defender |
| `.github/workflows/release.yml` | Build, validação e publicação da release |
| `assets/feegow_powered.png` | Identidade visual |
| `assets/laboratorio_principal.png` | Imagem principal da interface |
| `.gitignore` | Exclusões do versionamento |
| `README.md` | Documentação do projeto |

## Arquitetura

A separação atual é:

`main.py` → inicialização e splash  
`interface.py` → interface, planilha, histórico, atualização e Windows 11  
`app.py` → automação, resultados, checkpoints e persistência  
`patch.py` → compatibilidade histórica mantida por segurança

A regra de manutenção é evitar implementações paralelas e consolidar novos ajustes na implementação canônica correspondente.

## Planilha virtualizada

A grade usa `VirtualGridTree`, baseada em Canvas, com virtualização de linhas e pool visual limitado.

Principais características:

- até 10.000 linhas lógicas;
- renderização somente da região visível com overscan;
- seleção de células e retângulos;
- edição direta;
- copiar, colar, recortar e excluir;
- desfazer/refazer;
- identificação unificada de célula por hit-test;
- sincronização de rolagem horizontal e vertical;
- cabeçalho lateral com numeração das linhas.

A implementação evita criar um widget individual para cada linha da planilha.

## Recuperação e estado processado

Execuções interrompidas usam checkpoints associados à planilha/página e, na planilha interna, um fingerprint do conjunto de códigos.

O aplicativo diferencia uma execução interrompida de uma planilha que já foi processada. Quando não existe trabalho pendente, a planilha processada não é reapresentada como se pudesse ser retomada; o fluxo pode iniciar uma nova planilha em branco.

Essa proteção possui testes de regressão para alterações de conteúdo, persistência e estado processado.

## Histórico de erros

O histórico detalhado da execução é mantido de forma agrupada. A apresentação específica dos erros é condicional: quando não há erros, não é criada uma pasta de erros apenas para preencher a interface; quando há erros, os detalhes ficam organizados nessa área.

## Barra de rolagem

A interface utiliza uma barra personalizada inspirada no comportamento visual do Windows, com:

- polegar arredondado;
- setas de incremento e decremento;
- arraste do polegar;
- clique no trilho para paginação;
- repetição ao manter a seta pressionada;
- estados de hover;
- suporte vertical e horizontal.

## Atualização

A atualização é integrada à própria aplicação.

O fluxo:

1. consulta releases compatíveis;
2. valida versão e manifesto;
3. confere o SHA-256 do executável;
4. prepara o ambiente para substituição;
5. mantém backup durante a troca;
6. reinicia a aplicação de forma independente;
7. executa rollback quando a nova versão não confirma a inicialização.

Não existe updater separado publicado pelo projeto.

## Validação e qualidade

O CI verifica continuamente:

- arquitetura consolidada e ausência de módulos legados removidos;
- versão e progressão de versão;
- dependências;
- referências fixadas das GitHub Actions;
- qualidade estrutural;
- sintaxe;
- suíte de testes;
- integração da aplicação;
- smoke test da interface;
- estrutura e metadados do executável;
- Microsoft Defender.

O CI utiliza **Python 3.14.7** e **pip 26.2.1**. O build oficial utiliza **PyInstaller 6.22.3**.

## Release

A versão oficial do código neste `main` é **2.99.56**.

O fluxo de release possui dois caminhos:

- **Automático:** após o workflow `Validate main for release` concluir com sucesso para um push na `main`, o workflow de release é acionado por `workflow_run`. Isso evita depender de um disparo encadeado pelo mesmo `GITHUB_TOKEN` e reduz o risco de duplicidade.
- **Manual:** o workflow `release.yml` continua disponível por `workflow_dispatch`, exigindo a tag explícita da release.

Antes da publicação, o pipeline confirma que a tag corresponde ao commit atualmente validado da `main`, executa novamente os testes, gera o executável, valida metadados e Defender, cria o manifesto e verifica remotamente os assets publicados.

## Histórico recente da versão 2.99.56

A série `2.99.56` consolidou, entre outras mudanças:

- barras de rolagem arredondadas com setas;
- recuperação segura de planilhas interrompidas;
- distinção entre planilhas processadas e trabalho ainda pendente;
- histórico de erros exibido somente quando necessário;
- ajustes no fluxo automático de release;
- consolidação dos testes de regressão correspondentes.

---

**SM AutoLab** — automação de autorizações no Feegow, planilha virtualizada e interface desktop em uma base compacta e verificável.
