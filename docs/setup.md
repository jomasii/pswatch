# Como colocar no ar (passo a passo do João)

Faça nesta ordem. Nunca cole tokens no chat: eles vão direto nos campos do GitHub e do cron-job.org.

## 1. Bot do Telegram
1. No Telegram, abra o **@BotFather**, envie `/newbot` e siga as perguntas. Ele devolve um **token**.
2. Abra uma conversa com o seu bot novo e envie "oi".
3. Descubra o seu **chat id** (por exemplo, falando com o bot **@userinfobot**, que responde com o seu número).

## 2. Repositório público no GitHub
1. Crie um repositório **público** (ex.: `ps5watch`) em github.com.
2. Envie o código para a branch `main` (o Claude te ajuda com o `git push`).

## 3. Segredos do repositório
Em *Settings → Secrets and variables → Actions → New repository secret*, crie:
- `TELEGRAM_TOKEN` (o token do bot)
- `TELEGRAM_CHAT_ID` (o seu chat id)

## 4. Teste das fontes (uma vez)
Em *Actions → probe → Run workflow*. Abra o log: ele lista as ofertas encontradas.
- Se mostrar ofertas do Zoom/Buscapé, as fontes abrem pelo GitHub. Siga adiante.
- Se mostrar "FALHOU" nas duas, avise o Claude: o plano muda para o escopo menor.

## 5. Primeira execução
Em *Actions → watch → Run workflow*. Ela cria a branch `data` sozinha. Confira no log que terminou sem erro.

## 6. Página web (GitHub Pages)
*Settings → Pages → Build and deployment*: fonte **Deploy from a branch**, branch **data**, pasta **/ (root)**.
A página fica em `https://<seu-usuario>.github.io/<repositório>/`.

## 7. Disparo a cada 1 minuto (cron-job.org)
1. No GitHub: *Settings → Developer settings → Personal access tokens → Fine-grained tokens*. Crie um token **só para este repositório**, com a permissão **Actions: Read and write**.
2. Crie uma conta gratuita em cron-job.org e um job novo:
   - URL: `https://api.github.com/repos/<usuario>/<repositório>/actions/workflows/watch.yml/dispatches`
   - Método: **POST**; corpo: `{"ref":"main"}`
   - Cabeçalhos: `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`, `Content-Type: application/json`
   - Frequência: **a cada 1 minuto**
3. Em *Actions*, confira que aparecem execuções do `watch` a cada minuto (uma roda e as outras ficam na fila).

## 8. Conferir
Mande o teste: o Claude pode rodar o ensaio (`python -m ps5watch.dry_run`) para você ver o formato dos alertas.
