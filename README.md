# SM AutoLab

## Base atual

Esta é a base estável atual do SM AutoLab. A versão vigente é sempre a declarada no arquivo `VERSION`; a aplicação usa calendário nativo com `tkinter.Canvas` e elementos `CustomTkinter` no visual Fluent 2. A numeração de versões futuras não altera a estrutura funcional da base.

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

`main.py` usa `patch.py` como ponto único de entrada das correções. `patch.py` incorpora fisicamente, em namespaces isolados, as antigas camadas `patch_base.py`, `patch_arquivos.py` e `patch_ajustes.py`, preservando a ordem histórica de aplicação e evitando alterações de resolução de nomes entre componentes. O aplicativo valida a presença das funcionalidades essenciais antes de abrir.

## Build e releases

Antes de qualquer release, a validação da `main` confere a estrutura atual, os componentes obrigatórios, a ausência de referências legadas, a sintaxe e a integração das camadas. O workflow de release exige que a tag aponte exatamente para a `main` validada, compara a tag com `VERSION`, gera somente o aplicativo principal e seu manifesto. A atualização automática é integrada ao próprio executável e verifica o manifesto, a versão superior e o SHA-256 antes de substituir a instalação.

## Arquitetura consolidada

Todas as correções de interface históricas estão reunidas em `patch.py`, que mantém `aplicar_patch_ui` como único ponto chamado por `main.py`. Os antigos módulos `patch_base.py`, `patch_arquivos.py` e `patch_ajustes.py` não fazem mais parte da árvore final; seus conteúdos são preservados internamente em namespaces próprios dentro de `patch.py`.
