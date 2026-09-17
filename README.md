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

`main.py` concentra a inicialização, o splash, as correções do histórico ilimitado e as correções finais de UI. `patch.py` permanece como ponto único de entrada das correções históricas consolidadas. `app.py` reúne a orquestração da execução, leitura das planilhas e armazenamento dos resultados.

Os módulos pequenos `planilha.py`, `resultados.py`, `splash.py` e `ui_fixes_29912.py` foram incorporados aos módulos principais e removidos da árvore para evitar fragmentação desnecessária.

## Build e releases

Antes de qualquer release, a validação da `main` confere a estrutura atual, os componentes obrigatórios, a ausência de referências legadas, a sintaxe e a integração das camadas. O workflow de release exige que a tag aponte exatamente para a `main` validada, compara a tag com `VERSION`, gera somente o aplicativo principal e seu manifesto. A atualização automática é integrada ao próprio executável e verifica o manifesto, a versão superior e o SHA-256 antes de substituir a instalação.

## Arquitetura consolidada

As correções de interface históricas permanecem reunidas em `patch.py`, que mantém `aplicar_patch_ui` como ponto de integração. As correções finais específicas da UI estão em `main.py`, no mesmo módulo de inicialização, sem um arquivo separado.
