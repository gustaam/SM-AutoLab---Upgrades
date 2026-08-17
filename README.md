# SM AutoLab — Upgrades

Repositório do SM AutoLab.

## Atualizações automáticas

A arquitetura de atualização foi preparada para usar GitHub Releases:

- `updater.py` consulta a última Release pública do repositório;
- o executável principal pode solicitar o `SM AutoLab Updater.exe` para baixar e substituir a versão atual;
- o updater verifica o SHA-256 informado pela Release antes de substituir o executável;
- `.github/workflows/release.yml` compila o aplicativo e o updater e publica os dois arquivos quando uma tag `vX.YY` ou `vX.YY.Z` é enviada.

### Publicar uma nova versão

1. Atualize `VERSION` para a nova versão.
2. Gere a tag correspondente, por exemplo `v2.65`.
3. Envie a tag ao GitHub.
4. O workflow `Build and publish release` cria a Release e anexa o executável do SM AutoLab e o updater.

Os dados locais do usuário não fazem parte do executável e não são substituídos durante a atualização.
