# SM AutoLab

## Base atual

Esta é a base estável atual do SM AutoLab. A versão vigente é sempre a declarada no arquivo `VERSION`; a aplicação usa calendário nativo com `tkinter.Canvas` e elementos `CustomTkinter` no visual Fluent 2. A numeração de versões futuras não altera a estrutura funcional da base. A partir da 2.99.16, a interface principal também recebe uma camada visual Fluent 2 refinada, com superfícies mais consistentes, estados hover e uma microanimação discreta de acento no cabeçalho. No Windows 11 Build 22621 ou superior, a interface usa os materiais de composição do DWM: Mica na janela principal, Mica Alt em janelas secundárias persistentes e Acrylic em diálogos transitórios; em sistemas sem esse suporte, a paleta Fluent 2 sólida permanece como fallback. A partir da 2.99.17, a tela inicial também recebe um dashboard moderno de sessão, com resumo contextual, indicadores de execução e anel de progresso sincronizado com a automação.

## Arquivos e histórico

- calendário mensal interativo;
- navegação entre meses conforme o histórico disponível;
- clique em uma data para listar somente as planilhas salvas naquele dia;
- botão `← Voltar` para retornar ao calendário;
- destaque visual para dias com planilhas;
- histórico ilimitado;
- seleção múltipla de datas;
- animação/estado visual de seleção;
- contador de células selecionadas;
- exclusão somente das datas selecionadas;
- botão `Limpar histórico` para limpar tudo;
- contador de códigos calculado somente a partir do histórico existente.

## Estrutura de manutenção

`main.py` concentra a inicialização, o splash, as correções do histórico ilimitado e as correções finais de UI. `patch.py` permanece como ponto único de entrada das correções históricas consolidadas. `app.py` reúne a orquestração da execução, leitura das planilhas e armazenamento dos resultados.

Os módulos pequenos `planilha.py`, `resultados.py`, `splash.py` e `ui_fixes_29912.py` foram incorporados aos módulos principais e removidos da árvore para evitar fragmentação desnecessária.

## Configuração e credenciais

As credenciais do Feegow não fazem parte do código-fonte. `config.py` mantém apenas valores padrão vazios e persiste as configurações fornecidas pelo usuário em `SM AutoLab/feegow_config.json`. A automação interrompe o início ou a recuperação do navegador quando usuário e senha não estiverem configurados.

## Build e releases

Antes de qualquer release, a validação da `main` confere a estrutura atual, os componentes obrigatórios, a ausência de referências legadas, a sintaxe e a integração das camadas. O workflow de release exige que a tag aponte exatamente para a `main` validada, compara a tag com `VERSION`, gera somente o aplicativo principal e seu manifesto. A atualização automática é integrada ao próprio executável e verifica o manifesto, a versão superior e o SHA-256 antes de substituir a instalação.

O `build_windows.bat` é autossuficiente quanto aos metadados de versão do executável: o antigo `version_info_template.txt` foi incorporado diretamente ao processo de build. O arquivo temporário `version_info.txt` continua sendo gerado apenas durante o build e é ignorado pelo Git.

## Arquitetura consolidada

As correções de interface históricas permanecem reunidas em `patch.py`, que mantém `aplicar_patch_ui` como ponto de integração. As correções finais específicas da UI estão em `main.py`, no mesmo módulo de inicialização, sem um arquivo separado.

### Mapa de integração

`patch.py` é o ponto único de entrada das correções consolidadas de interface. Ele incorpora fisicamente, em namespaces isolados, as antigas camadas de base e mantém a ordem histórica de aplicação. É o único módulo de patches importado por `main.py`.

Os antigos `patch_base.py`, `patch_arquivos.py` e `patch_ajustes.py` tiveram seus conteúdos preservados integralmente em fontes internas `_SOURCE_PATCH_BASE`, `_SOURCE_PATCH_ARQUIVOS` e `_SOURCE_PATCH_AJUSTES`, executadas nos namespaces `_NS_PATCH_BASE`, `_NS_PATCH_ARQUIVOS` e `_NS_PATCH_AJUSTES`. Isso preserva a resolução de nomes e a sequência de monkey-patches sem manter módulos externos separados.

`atualizacao.py` é o motor integrado de atualização do próprio executável.
