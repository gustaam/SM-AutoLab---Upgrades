# SM AutoLab v2.42

Versão padrão estável de referência do SM AutoLab.

## Estado desta versão

A v2.42 é a base estável para futuras alterações. Ela preserva:

- retomada automática após interrupções por checkpoint;
- recuperação do navegador;
- fechamento do navegador ao fechar o aplicativo;
- interface e menus da linha v2.42;
- histórico, atividade e erros;
- seleção de planilha e processamento dos códigos;
- requisitos com Pillow.

## Estrutura

- `main.py` — ponto de entrada.
- `app.py` — inicialização da aplicação.
- `interface.py` — interface gráfica.
- `automacao.py` — automação Selenium/Feegow.
- `config.py` — configurações persistentes.
- `planilha.py` — leitura da planilha.
- `resultados.py` — resultados e histórico.
- `splash.py` — tela de inicialização.
- `assets/` — recursos visuais.
- `requirements.txt` — dependências.

## Segurança

Credenciais reais **não fazem parte deste repositório**.

O usuário e a senha do Feegow são configurados pelo próprio aplicativo e armazenados localmente em:

`%USERPROFILE%/SM AutoLab/feegow_config.json`

Esse arquivo está no `.gitignore` e não deve ser enviado ao GitHub.

## Instalação

```bash
python -m pip install -r requirements.txt
python main.py
```

## Build do Windows

Use `build_windows.bat` após instalar as dependências.

## Referência de versão

**v2.42 — Retomada na abertura, navegador e menus**

Esta versão deve ser tratada como a base estável antes de qualquer nova alteração.
