# SM AutoLab

Automação de autorizações no Feegow com uma interface desktop moderna, uma planilha virtualizada de alta capacidade e um ciclo de build/release fortemente validado.

**Versão atual:** `2.99.24` — definida exclusivamente pelo arquivo `VERSION`.

## O que o SM AutoLab faz

O SM AutoLab automatiza o processamento de códigos em uma rotina operacional integrada ao Feegow. O aplicativo lê códigos de uma planilha Excel, abre o navegador controlado pelo Selenium, realiza o login e percorre a rotina de autorização procedimento a procedimento.

A aplicação foi evoluindo para concentrar tudo em uma arquitetura pequena e verificável, sem perder as melhorias acumuladas na interface.

## Principais funcionalidades

### Automação do Feegow

- Leitura de códigos da coluna configurada da planilha Excel.
- Abertura e controle do navegador por Selenium.
- Login com credenciais configuradas localmente pelo usuário.
- Abertura automática da área **Autorizar Procedimento**.
- Execução sequencial dos códigos.
- Tratamento de falhas por código, permitindo continuar para o próximo item quando possível.
- Recuperação automática da tela e reinicialização do navegador quando a sessão fica inutilizável.
- Feedback de status durante login, navegação, execução e recuperação.
- Contadores incrementais de processados, sucessos e erros.

### Planilha virtualizada

A grade foi projetada para trabalhar com **até 10.000 linhas lógicas** sem criar 10.000 widgets de interface.

- Renderização virtual em Canvas.
- Pool reutilizável de células visíveis.
- Overscan pequeno para rolagem suave.
- Cálculo do intervalo visível em vez de percorrer toda a planilha.
- Seleção por célula e seleção retangular.
- Arraste para seleção.
- Seleção de todas as células preenchidas.
- Edição direta da célula.
- Copiar, recortar e colar.
- Colagem por teclado com fallback local/global e suporte ao evento de clipboard.
- Exclusão de conteúdo com Delete/Backspace.
- Desfazer e refazer.
- Limpeza seletiva.
- Contador de linhas preenchidas.
- Armazenamento esparso: células vazias não precisam permanecer materializadas.

### Rascunhos, checkpoints e recuperação

- Salvamento de rascunho da planilha.
- Recuperação de rascunho ao reabrir a aplicação.
- Checkpoint por planilha/aba durante execução.
- Checkpoint interno para execução direta a partir de códigos em memória.
- Impressão digital (fingerprint) da lista de códigos para evitar retomar uma execução em uma lista diferente.
- Limpeza automática do checkpoint ao concluir a execução.

### Histórico e calendário

- Histórico persistente das planilhas processadas.
- Calendário mensal em Canvas.
- Navegação pelos meses disponíveis.
- Destaque visual das datas com planilhas.
- Abertura do conteúdo salvo a partir da data selecionada.
- Seleção múltipla de datas.
- Animação visual de seleção.
- Exclusão seletiva de datas.
- Limpeza de todo o histórico mediante confirmação.
- Contador de códigos baseado no histórico efetivamente salvo.
- A abertura de snapshots converge para a mesma implementação canônica da planilha, evitando uma segunda grade paralela.

### Dashboard e acompanhamento de sessão

- Dashboard inicial integrado à tela principal.
- Resumo contextual da sessão.
- Indicadores de execução.
- Anel de progresso sincronizado.
- Atualização incremental de métricas.
- Histórico de atividades e mensagens de erro.
- Indicador de status com estado visual de prontidão.

### Interface e experiência visual

A interface combina CustomTkinter, Canvas e integração nativa com o Windows.

- Visual inspirado no **Fluent 2**.
- Estados hover e foco mais consistentes.
- Microanimações discretas de acento.
- Layout responsivo para redimensionamento da janela.
- Tooltips universais para botões e controles relevantes.
- Menus de aparência/configurações com interação por clique e hover.
- Calendário e componentes gráficos desenhados diretamente em Canvas quando isso reduz overhead.
- Splash screen otimizado para reutilizar o mesmo item de imagem em vez de redesenhar toda a tela a cada frame.
- Preservação de atalhos e interações de teclado da planilha.

### Integração nativa com Windows 11

No Windows 11 compatível, o aplicativo aproveita recursos do DWM; fora desse cenário, utiliza fallback visual sólido.

- Mica na janela principal.
- Mica Alt em janelas secundárias persistentes.
- Acrylic em diálogos transitórios.
- Cantos arredondados via DWM.
- Integração com recursos de tema claro/escuro.
- DPI awareness com fallback para APIs disponíveis na versão do Windows.
- Ajustes nativos de tema/acessibilidade da interface.
- Fallback seguro quando APIs nativas não estão disponíveis.

## Segurança e persistência

As credenciais não são gravadas no código-fonte.

- Usuário e senha começam vazios no código.
- As configurações fornecidas pelo usuário são armazenadas localmente na pasta de dados do **SM AutoLab**.
- Gravações críticas utilizam escrita atômica.
- Arquivos importantes podem manter backup anterior para recuperação.
- JSON corrompido pode ser recuperado a partir do backup quando disponível.
- Nenhuma credencial precisa ser adicionada ao Git.
- O pipeline executa verificação do Windows Defender sobre a árvore do projeto.

## Atualização automática

O atualizador faz parte do próprio aplicativo; não existe um executável de updater separado como componente da distribuição.

O processo valida:

1. versão disponível;
2. versão atual versus versão candidata;
3. manifesto da release;
4. integridade do arquivo pelo SHA-256;
5. compatibilidade do asset esperado;
6. preparação do ambiente para reinício independente;
7. substituição segura do executável.

Isso reduz dependências externas do processo de atualização.

## Arquitetura atual

A base de produção foi compactada para quatro módulos principais:

| Arquivo | Responsabilidade |
|---|---|
| `main.py` | Ponto de entrada da aplicação, splash, inicialização unificada da UI, dashboard, layout responsivo, tooltips e correções finais de interface. |
| `interface.py` | Camada principal de interface: planilha virtual, calendário/histórico, edição, seleção, undo/redo, atualização integrada e recursos nativos do Windows. |
| `app.py` | Automação do Feegow, leitura das planilhas, resultados da execução, checkpoints, configuração local e armazenamento seguro. |
| `patch.py` | Compatibilidade histórica consolidada. Mantém a ordem de aplicação dos patches sem espalhar dezenas de arquivos auxiliares pela árvore. |

### Por que `patch.py` continua separado?

Ele funciona como a fronteira de compatibilidade das correções históricas. As antigas camadas de patch foram incorporadas fisicamente ao arquivo em namespaces isolados, preservando ordem e resolução de nomes sem manter módulos externos individuais.

## Mapa das pastas e arquivos

```
SM-AutoLab---Upgrades/
├── .github/
│   └── workflows/
│       ├── validate-main.yml   # CI da main, validações e preparação automática da release
│       └── release.yml         # build, validação do executável, manifesto e publicação
│
├── assets/
│   ├── feegow_powered.png      # identidade/assinatura visual relacionada ao Feegow
│   └── laboratorio_principal.png # imagem usada pela interface
│
├── scripts/
│   └── validate.py             # validador consolidado de arquitetura, dependências,
│                               # qualidade, VERSION e executável PE
│
├── tests/
│   ├── test_patch.py           # regressões, compatibilidade e contratos da base
│   ├── test_main.py            # testes da camada principal/dashboard/UI
│   ├── test_planilha.py        # planilha virtual, histórico, calendário e edição
│   ├── test_app.py             # automação, resultados, checkpoints e armazenamento
│   └── test_validation.py      # testes dos validadores consolidados
│
├── app.py                      # automação + persistência + configuração
├── interface.py                # UI + planilha + histórico + atualização + Windows nativo
├── main.py                     # bootstrap + splash + UI integrada
├── patch.py                    # compatibilidade e patches históricos consolidados
├── build_windows.bat           # build manual do executável Windows
├── requirements.txt            # dependências de runtime fixadas
├── VERSION                     # versão canônica do aplicativo
├── SM AutoLab.ico              # ícone do executável
├── README.md                   # documentação principal
└── .gitignore                  # exclusões do Git
```

## Validação, testes e qualidade

A suíte atual está consolidada em **5 arquivos**, preservando **120 casos de teste**.

O validador único oferece:

- `all`: arquitetura, VERSION e qualidade;
- `architecture`: estrutura e integração;
- `version`: validação de versão;
- `quality`: qualidade estrutural e ciclos de importação;
- `executable`: validação básica do PE gerado.

O CI também executa:

- Python **3.14.7**;
- `pip 26.2.1`;
- dependências fixadas em `requirements.txt`;
- compilação sintática com `compileall`;
- suíte completa de testes;
- teste de integração da inicialização da UI;
- Windows Defender.

## Build do Windows

O build oficial produz um único executável principal:

`dist/SM AutoLab.exe`

O processo usa PyInstaller e incorpora:

- ícone do aplicativo;
- assets;
- `VERSION`;
- metadados de arquivo/produto gerados automaticamente a partir da versão.

O arquivo intermediário de metadados é temporário e não faz parte da árvore versionada.

## Release

O fluxo de release valida a base antes de publicar:

1. validação estrutural e de dependências;
2. testes automatizados e integração;
3. Defender;
4. confirmação de que a `main` não mudou após a validação;
5. validação da versão;
6. criação/alinhamento da tag exata do commit validado;
7. build do executável;
8. validação do PE e dos metadados;
9. geração do manifesto com SHA-256;
10. publicação e verificação dos assets.

A release publicada anteriormente é **v2.99.23**. A próxima versão preparada pela base atual é **v2.99.24**, ainda dependente da validação completa e publicação.

## Histórico recente de consolidação

As principais reduções estruturais já concluídas foram:

- remoção de módulos auxiliares duplicados de UI e planilha;
- consolidação da grade virtualizada em `interface.py`;
- consolidação da automação e persistência em `app.py`;
- consolidação do validador em `scripts/validate.py`;
- consolidação da suíte de testes de 18 para 5 arquivos;
- eliminação de arquivos históricos obsoletos da árvore principal;
- manutenção das compatibilidades históricas dentro de `patch.py`;
- eliminação de referências de importação para módulos removidos;
- validação contínua após cada compactação para evitar regressões.

## Consolidação da v2.99.24

A `v2.99.24` é a primeira versão preparada sobre a árvore consolidada em quatro módulos de produção, cinco arquivos de teste e dois workflows. O fluxo de release está integrado ao `validate-main.yml`, enquanto `release.yml` permanece dedicado ao build e à publicação do executável.

## Manutenção

A regra da base é simples: **não introduzir uma nova implementação paralela quando a implementação canônica já existe**.

Ao alterar o aplicativo:

- atualize a implementação canônica;
- atualize os testes correspondentes;
- atualize `scripts/validate.py` quando a estrutura mudar;
- execute o CI completo antes do merge;
- não deixe referências a arquivos removidos;
- mantenha `VERSION` como única fonte de verdade da versão.

---

**SM AutoLab** — automação de processos, planilha de alta capacidade e interface desktop integrada em uma base enxuta e verificável.
