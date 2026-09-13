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
- botão `Limpar todo histórico` para limpar tudo;
- contador de códigos calculado somente a partir do histórico existente.

## Estrutura de manutenção

`main.py` usa módulos com nomes neutros: `patch_base.py` e `patch_arquivos.py`. Assim, a versão do aplicativo não fica vinculada ao nome de uma implementação histórica. Os componentes internos permanecem encapsulados nesses módulos e a inicialização valida a presença das funcionalidades essenciais antes de abrir a aplicação.

## Build e releases

Antes de qualquer release, a validação da `main` confere a estrutura atual, os componentes obrigatórios, a ausência de referências legadas, a sintaxe e a integração das camadas. O workflow de release exige que a tag aponte exatamente para a `main` validada, compara a tag com `VERSION`, gera o aplicativo e o updater e recusa sobrescrever uma release existente. O updater aceita as três nomenclaturas históricas do executável updater e só considera releases da linha-base atual com manifesto válido e versão superior à instalada.
