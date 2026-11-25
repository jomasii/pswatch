# Monitor de preço do PS5 — resumo da sessão

Data: 2026-11-24/25. Black Friday: **sexta, 2026-11-27**.

## 1. O que você pediu
Uma aplicação web que mostre a variação de preço e avise quando o preço cair nos principais marketplaces confiáveis do Brasil, para você comprar um **PlayStation 5** na Black Friday.

## 2. Decisões tomadas
| Tema | Decisão |
|---|---|
| Modelos | PS5 Slim com leitor de disco **e** PS5 Slim Digital (cada um com seu histórico) |
| Alerta | Telegram. Normal abaixo de **R$ 4.000**; **ALERTA MÁXIMO** abaixo de **R$ 3.600** (repetido a cada 60 s, até 5 vezes) |
| Preço que vale | À vista/Pix; o parcelado aparece na mensagem; frete fora do cálculo |
| Fontes | Zoom e Buscapé (JSON-LD das páginas de produto). Mercado Livre e cupons: **não construídos ainda** |
| Hospedagem | Grátis: GitHub Actions + GitHub Pages, repositório público |
| Latência | Disparo externo (cron-job.org) em vez do agendador nativo do GitHub; laço de checagem a cada 45 s dentro de cada execução |
| Cupons | Quando houver, só **avisar**; nunca mudam o limite do alerta (ainda não implementado) |
| Bundles com jogos | Ficam de fora (decisão do desenho; pode ser revista) |

## 3. O que foi construído
- Código Python em `src/ps5watch/`: leitura das fontes, identificação do modelo pelo título, regras de alerta, aviso de falha de fonte, cliente do Telegram, histórico e estado guardados na branch `data`.
- Página com gráfico de histórico: <https://jomasii.github.io/pswatch/>
- Repositório: <https://github.com/jomasii/pswatch>
- Workflows: `watch` (vigia), `probe` (teste das fontes), `telegram-test` (mensagem de teste).
- 95 testes automáticos passando.
- Documentos: `docs/superpowers/specs/2026-11-24-ps5-price-alert-design.md` (desenho), `docs/superpowers/plans/2026-11-24-ps5-price-alert.md` (plano), `docs/setup.md` (passo a passo).

## 4. Estado em produção (verificado nos logs)
- Zoom e Buscapé **abrem** a partir do GitHub Actions.
- O Telegram funciona: o teste chegou (o primeiro erro foi usar o id de um bot em vez do seu id pessoal).
- O `watch` roda continuamente; execuções "cancelled" são normais (o GitHub guarda só a fila mais recente).
- O cron-job.org dispara a cada **2 minutos** (provavelmente limite do plano gratuito), não a cada 1.
- Preços vistos no último teste: Digital R$ 4.370,07 (KaBuM!), com leitor R$ 4.621,75 (Magalu). Ambos acima de R$ 4.000, então nenhum alerta ainda.

## 5. Problemas encontrados e corrigidos na revisão final
- Anúncio com preço absurdo (< R$ 2.000) escondia as ofertas reais → agora vira só aviso "suspeito".
- Oferta que "pisca" (estoque, página fora do ar) repetia o alerta máximo → rearme só após 30 min.
- Acessórios, recondicionados, vitrine e importados passavam como console → descartados.
- "Disk + Controle DualSense" legítimo era descartado → agora aceito (combo com jogos continua fora).

## 6. Pendências
1. **Mercado Livre**: a API respondeu 403 sem token. Precisa registrar um aplicativo e guardar o token como segredo `ML_ACCESS_TOKEN`.
2. **Cupons** (só aviso): não construído.
3. **Menores adiados:** uma das 4 páginas de cada fonte pode falhar sem aviso; aviso de falha pode ser dado como enviado mesmo se o Telegram falhar; limite de 8 min da execução pode cortar uma checagem; nomes como "Amazon.com.br" não casam com a lista de lojas.
4. Acabamento das mensagens: loja em minúsculas ("kabum"); a linha "menor preço dos últimos 30 dias" mostra o próprio preço nos primeiros dias (você optou por deixar assim).
5. Conferir na primeira alerta real se o preço do Zoom é o à vista/Pix ou o parcelado.

## 7. Como conferir sozinho
- Execuções: <https://github.com/jomasii/pswatch/actions>
- Teste do Telegram: Actions → `telegram-test` → Run workflow.
- Ensaio local sem rede: `python -m ps5watch.dry_run`.
- Consulta real dos preços agora: `python scripts/live_check.py`.

## 8. Segurança
- O token do bot e o chat id ficam só nos **segredos do repositório** (`TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`). O token do GitHub do cron-job.org tem acesso só ao `pswatch` (Actions: Read and write) e foi trocado depois de aparecer em uma captura de tela.
- Se um token aparecer em captura de tela ou chat, gere outro.

## 9. Ferramentas instaladas neste computador (com a sua autorização)
Python 3.12, Git e GitHub CLI (`gh`), pelo winget. O `gh` está logado na conta `jomasii`.
