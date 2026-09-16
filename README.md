# SM AutoLab

## Base atual

Esta é a base estável atual do SM AutoLab. A versão vigente é sempre a declarada no arquivo `VERSION`; a aplicação usa calendário nativo com `tkinter.Canvas` e elementos `CustomTkinter` no visual Fluent 2. A numeração de versões futuras não altera a estrutura funcional da base.

## Arquivos e histórico

- calendário mensal interativo;
- navegação entre meses dentro da janela de retenção;
- clique em uma data para listar somente as planilhas salvas naquele dia;
- botão `← Voltar` para retornar ao calendário;
- destaque visual para dias com planilhas;
- retenção de até 60 dias;
- seleção múltipla de datas;
- animação/estado visual de seleção;
- contador de células selecionadas;
- exclusão somente das datas selecionadas;
- botão `Limpar histórico` para limpar tudo;
- contador de códigos calculado somente a partir do histórico existente.

## Estrutura de manutenção

`main.py` usa `patch.py` como ponto único de entrada das correções consolidadas de interface. As camadas-base `patch_base.py`, `patch_arquivos.py` e `patch_ajustes.py` permanecem separadas nesta etapa para preservar a ordem de aplicação e reduzir o risco de regressão durante a reorganização. O aplicativo valida a presença das funcionalidades essenciais antes de abrir.

## Build e releases

Antes de qualquer release, a validação da `main` confere a estrutura atual, os componentes obrigatórios, a ausência de referências legadas, a sintaxe e a integração das camadas. O workflow de release exige que a tag aponte exatamente para a `main` validada, compara a tag com `VERSION`, gera somente o aplicativo principal e seu manifesto. A atualização automática é integrada ao próprio executável e verifica o manifesto, a versão superior e o SHA-256 antes de substituir a instalação.

## Arquitetura consolidada

As correções de interface históricas estão reunidas em `patch.py`, que mantém `aplicar_patch_ui` como único ponto chamado por `main.py`. Os módulos auxiliares de base permanecem como dependências internas nesta etapa e não são chamados diretamente pelo ponto de entrada principal.
