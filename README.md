# SM AutoLab — v2.99

## Base

Esta versão parte da base v2.96 e substitui o mecanismo externo de calendário por um calendário nativo desenhado em `tkinter.Canvas`, integrado ao visual Fluent 2 do aplicativo.

## Arquivos

- calendário mensal interativo;
- navegação entre meses dentro da janela de retenção;
- clique em uma data para listar somente as planilhas salvas naquele dia;
- botão `← Voltar` para retornar ao calendário;
- destaque visual para dias com planilhas;
- retenção de até 60 dias;
- contador de códigos do mês;
- janela de Arquivos com tamanho mínimo explícito.

## Por que o calendário foi alterado

As versões anteriores com `tkcalendar` chegaram a empacotar a dependência, mas o executável continuou apresentando uma janela branca/pequena. Para reduzir pontos de falha no executável Windows, esta versão não depende de `tkcalendar` nem de `Babel`. O calendário usa somente Tkinter padrão para a grade e CustomTkinter para os elementos Fluent 2.

## Build

Execute `build_windows.bat`. O script instala as dependências, limpa caches e valida os componentes essenciais antes de chamar o PyInstaller.
