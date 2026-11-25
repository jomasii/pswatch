# Monitor de preço do PS5 — resumo da sessão

Data: 2026-11-24/25 (atualizado em 25/11 à tarde). Black Friday: **sexta, 2026-11-27**. Cyber Monday: **segunda, 2026-11-30**.

## 1. O que você pediu
Uma aplicação web que mostre a variação de preço e avise quando o preço cair nos principais marketplaces confiáveis do Brasil, para você comprar um **PlayStation 5** na Black Friday.

## 2. Decisões tomadas
| Tema | Decisão |
|---|---|
| Modelos | PS5 Slim com leitor de disco **e** PS5 Slim Digital (cada um com seu histórico) |
| Alerta | Telegram. Normal abaixo de **R$ 4.000**; **ALERTA MÁXIMO** abaixo de **R$ 3.600** (repetido a cada 60 s, até 5 vezes) |
| Preço que vale | À vista/Pix; o parcelado aparece na mensagem; frete fora do cálculo |
| Fontes | Zoom e Buscapé (a cada 45 s, o tempo todo) + **Mercado Livre via Apify** (só em janelas da Black Friday e Cyber Monday) |
| Hospedagem | Grátis: GitHub Actions + GitHub Pages, repositório público; Apify no plano grátis (US$ 5/mês) |
| Latência | Disparo externo (cron-job.org, a cada 2 min) em vez do agendador nativo do GitHub; laço de checagem a cada 45 s dentro de cada execução |
| Combos com jogos | **Incluídos** no alerta, marcados na mensagem como "🎮 Combo com jogos" |
| Cupons | Só **avisar**; nunca mudam o limite do alerta. Mercado Livre: cupom do próprio anúncio aparece no alerta. Amazon/Pelando: bloqueiam leitura da nuvem → use o alerta "PS5" no app do Pelando |

## 3. O que foi construído
- Código Python em `src/ps5watch/`: leitura das fontes, identificação do modelo pelo título, regras de alerta, aviso de falha de fonte, cliente do Telegram, histórico e estado guardados na branch `data`.
- Página com gráfico de histórico: <https://jomasii.github.io/pswatch/>
- Repositório: <https://github.com/jomasii/pswatch>
- Workflows: `watch` (vigia), `probe` (teste das fontes), `telegram-test` (mensagem de teste), `apify-probe` (teste dos robôs do Apify), `ml-probe` (teste da API oficial do Mercado Livre, aguardando aprovação do app).
- **158 testes** automáticos passando.
- Documentos: `docs/superpowers/specs/2026-11-24-ps5-price-alert-design.md` (desenho), `docs/superpowers/plans/2026-11-24-ps5-price-alert.md` (plano), `docs/setup.md` (passo a passo).

### Adicionado em 25/11
- **Combos com jogos** passaram a entrar no alerta (marcados como combo). "+ Controle DualSense" não conta como combo.
- **Aviso de falha por página**: se uma página do Zoom/Buscapé cair por mais de 10 min, chega uma mensagem por fonte listando as páginas afetadas, e outra quando voltam.
- **Teste de alerta real**: o limite foi subido para R$ 4.500 por alguns minutos, o alerta chegou certo no Telegram e o limite voltou para R$ 4.000.
- **Mercado Livre via Apify** (detalhes na seção 5).
- **Painel ao vivo** em <https://jomasii.github.io/pswatch/> (desenho em `docs/superpowers/specs/2026-11-25-painel-ao-vivo-design.md`):
  - visual escuro; destaque do menor preço de cada modelo com quanto falta para R$ 4.000 e botão "Abrir oferta";
  - 🏆 ranking das ofertas de agora (filtros Digital / Com leitor / Sem combos) e 📉 menores preços já vistos (vezes e tempo no ar);
  - atualiza sozinho a cada ~75 s; a barra mostra a última checagem e fica **vermelha ("vigia parado?") após 15 min** sem checagem;
  - os links abrem a página do Zoom/Buscapé com a oferta da loja destacada (mais um clique até a loja); no Mercado Livre, o anúncio direto;
  - se o GitHub limitar as consultas, entra em "modo lento" (atraso até ~5 min) e avisa na barra;
  - o histórico passou a guardar o link de cada preço; preços antigos aparecem como "sem link".

## 4. Estado em produção (verificado nos logs)
- Zoom e Buscapé **abrem** a partir do GitHub Actions; 6 páginas em cada (4 do console e 2 de combos).
- O Telegram funciona (teste e alerta real chegaram).
- O `watch` roda continuamente; execuções "cancelled" são normais (o GitHub guarda só a fila mais recente).
- Preços vistos em 25/11: Digital a partir de R$ 4.179 (Magalu, por ~7 min) e ~R$ 4.370 (KaBuM!); no Mercado Livre, Digital R$ 5.499 e combo com disco R$ 4.844. Nada abaixo de R$ 4.000 ainda.

## 5. Mercado Livre
### Por que Apify
- A busca pública da API do Mercado Livre responde 403, e o aplicativo oficial que você registrou pode levar **até 10 dias** para ser aprovado.
- Comparamos alternativas: Apify (robôs prontos, cobra por resultado), GeckoAPI (R$ 126,90/mês, frescor dos dados incerto), serviços genéricos de scraping (caros para o Mercado Livre) e SerpApi/Google Shopping (atrasado). Escolhido: **Apify**.
- Testamos dois robôs: `karamelo/mercadolivre-scraper-brasil-portugues` e `riseandcode/apify-mercadolivre-search`. Trouxeram as mesmas ofertas em ~15 s. Escolhido o **karamelo** (respeita o limite de itens e informa compra internacional e estoque).

### Custo real (conferido no painel do Apify)
- O karamelo cobra **US$ 0,005 por resultado** (4x o que a página dizia).
- Cada consulta tem teto de **US$ 0,05**, o que limita a 10 resultados.
- Gasto até agora: **US$ 0,29** (teste dos dois robôs + 2 consultas ao vivo). Depois você conseguiu crédito extra: restam **US$ 8,71**.

### Agenda (horário de Brasília), definida em `config.yaml`
| Período | Frequência | Consultas |
|---|---|---|
| Até sexta 27/11 00h | pausado (sem custo, sem aviso de falha) | 0 |
| Sexta 27/11 (Black Friday) | a cada 11 min | ~131 |
| Sábado 28 e domingo 29 | a cada 6 h | ~8 |
| Segunda 30/11 (Cyber Monday) | a cada 66 min | ~22 |
| Depois de 01/12 00h | desligado | 0 |

- Total: 161 consultas ≈ **US$ 8,05**. Trava de segurança: para de vez na **163ª consulta** (as 2 do teste contam). Com 11 min na sexta, a trava nunca é atingida antes da Cyber Monday.
- Entre uma consulta e outra, as ofertas vêm de um cache (`mercadolivre.json` na branch `data`), então o alerta continua considerando o Mercado Livre.
- Teste ao vivo em 25/11 (12h20–12h40): 2 consultas com o intervalo correto, 4 ofertas válidas, e nenhuma consulta depois do fim da janela.

### Ajustes no filtro de modelo por causa do Mercado Livre
- "Unidade de disco" avulsa (R$ 659) era aceita como console → descartada.
- Anúncios em espanhol ("Consola ... Blanco") são compras internacionais → descartados (também pelo campo de compra internacional do robô).
- Títulos colados como "Slimdigital"/"Slimdisk" passaram a ser reconhecidos.
- Anúncios sem estoque são ignorados.

### Cupons
- O alerta de uma oferta do Mercado Livre mostra a linha "🎟️ Cupom/promoção do anúncio: ..." quando o anúncio tem cupom. O limite continua valendo sobre o preço **sem** cupom.
- O formato do campo de cupom do robô não é documentado; o texto é lido de forma tolerante (nunca quebra o alerta) e só será visto de verdade na sexta.
- Teste grátis de 25/11: **Pelando** (bloqueio da Cloudflare, HTTP 403) e **Amazon** (HTTP 503) não abrem a partir do GitHub. Para eles: alerta "PS5" no app do Pelando, com notificações ligadas.

### Cuidado ao editar datas no `config.yaml`
Use sempre dois dígitos: `2026-12-01`, não `2026-12-1`. Uma data inválida faz o vigia inteiro parar (inclusive Zoom e Buscapé).

## 6. Problemas encontrados e corrigidos na revisão final
- Anúncio com preço absurdo (< R$ 2.000) escondia as ofertas reais → agora vira só aviso "suspeito".
- Oferta que "pisca" (estoque, página fora do ar) repetia o alerta máximo → rearme só após 30 min.
- Acessórios, recondicionados, vitrine e importados passavam como console → descartados.
- "Disk + Controle DualSense" legítimo era descartado → agora aceito.

## 7. Pendências
1. **Congelamento**: nenhuma mudança no código na sexta. Mudanças só até quinta à noite (26/11).
2. **App oficial do Mercado Livre**: aguardando aprovação (até 10 dias); o `ml-probe` está pronto para quando sair. Provavelmente não chega a tempo.
3. **Sua parte:** criar o alerta "PS5" no app do Pelando; notificações do Telegram com som; estar logado nas lojas com endereço e Pix prontos.
4. **Menores adiados:** aviso de falha pode ser dado como enviado mesmo se o Telegram falhar; limite de 8 min da execução pode cortar uma checagem. (O nome "Amazon" foi conferido e casa normalmente.)
5. Acabamento das mensagens: loja em minúsculas ("kabum", "mercado livre"); a linha "menor preço dos últimos 30 dias" mostra o próprio preço nos primeiros dias.
6. Conferir na primeira alerta real se o preço é o à vista/Pix. No Mercado Livre o robô traz só o preço anunciado (normalmente igual ao Pix).

## 8. Como conferir sozinho
- Execuções: <https://github.com/jomasii/pswatch/actions>
- Teste do Telegram: Actions → `telegram-test` → Run workflow.
- Gasto no Apify: painel do Apify → Billing → Usage.
- Consultas já feitas ao Mercado Livre: arquivo `mercadolivre.json` na branch `data` (campo `runs`).
- Ensaio local sem rede: `python -m ps5watch.dry_run`.
- Consulta real dos preços agora: `python scripts/live_check.py`.

## 9. Segurança
- Segredos do repositório: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `APIFY_TOKEN`, `ML_CLIENT_ID`, `ML_CLIENT_SECRET`. Nenhum deles é impresso nos logs.
- O token do GitHub do cron-job.org tem acesso só ao `pswatch` (Actions: Read and write) e foi trocado depois de aparecer em uma captura de tela.
- Se um token aparecer em captura de tela ou chat, gere outro.

## 10. Ferramentas instaladas neste computador (com a sua autorização)
Python 3.12, Git e GitHub CLI (`gh`), pelo winget. O `gh` está logado na conta `jomasii`.
