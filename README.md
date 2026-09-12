# SM AutoLab — v2.99.1

## Base atual

Esta é a base estável atual do SM AutoLab. A aplicação usa calendário nativo com `tkinter.Canvas` e elementos `CustomTkinter` no visual Fluent 2. A numeração de versões futuras não altera a estrutura funcional da base.

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
- botão `Limpar todo histórico` para limpar tudo;
- contador de códigos calculado somente a partir do histórico existente.

## Estrutura de manutenção

`main.py` usa nomes neutros (`patch_base.py` e `patch_arquivos.py`) para que funcionalidades não fiquem vinculadas a números históricos de versão. Os módulos versionados antigos são mantidos apenas como camadas de compatibilidade interna até uma futura consolidação segura.

## Build e releases

O workflow de release valida a versão da tag contra `VERSION`, verifica os componentes obrigatórios, executa a validação sintática, gera o aplicativo e o updater e recusa sobrescrever uma release existente. O updater aceita as nomenclaturas históricas do executável updater e só considera releases da linha-base atual com manifesto válido e versão superior à instalada.
