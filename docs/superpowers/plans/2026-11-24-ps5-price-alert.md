# Monitor de preço do PS5 — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Monitorar o preço de dois modelos de PS5 Slim em lojas brasileiras e avisar no Telegram em menos de ~2 minutos quando o preço à vista/Pix cair abaixo de R$ 4.000 (alerta normal) ou R$ 3.600 (alerta máximo), com uma página web de histórico.

**Architecture:** Um laço em Python roda dentro de uma execução do GitHub Actions (disparada a cada 1 minuto por um agendador externo), consulta fontes de preço atrás de uma interface comum, decide alertas com regras puras (testáveis) e guarda estado e histórico numa branch `data`, gravando só quando algo muda. Uma página estática (GitHub Pages, servida da branch `data`) desenha o histórico.

**Tech Stack:** Python 3.12, `requests`, `beautifulsoup4` + `lxml`, `pytest`, GitHub Actions, GitHub Pages, Chart.js (CDN, versão fixa) na página.

**Spec:** `docs/superpowers/specs/2026-11-24-ps5-price-alert-design.md`

## Global Constraints

- Prazo: funcionando antes de **sexta 2026-11-27**.
- Custo zero; repositório **público** no GitHub; nada pago sem nova autorização do João.
- Modelos: `slim_disc` (PS5 Slim com leitor de disco) e `slim_digital` (PS5 Slim Digital). Sem PS5 Pro, sem usados, sem bundles com jogo, sem acessórios.
- Alerta normal: menor preço **à vista/Pix** < **R$ 4.000**; alerta máximo: < **R$ 3.600**; vale para qualquer um dos dois modelos. Frete fora do cálculo.
- Alerta máximo: reenviado a cada 60 s, até **5** vezes, ou até o preço sair da faixa.
- Mensagens em português, com: modelo, loja, preço à vista, preço parcelado, menor preço dos últimos 30 dias (ou "sem histórico ainda"), link direto, e aviso quando o frete não está incluído.
- Alerta de saúde se uma fonte falhar por **10 minutos** (mesmo que as outras funcionem); aviso de novo quando voltar. "Preço sem mudar" não é falha.
- Execução: ~5 min por run, laço a cada 30–60 s, `concurrency` sem cancelar (`cancel-in-progress: false`). Disparo externo de 1 min (cron-job.org); agendador nativo `*/5` como reserva.
- Segredos (token do bot, chat id, token de disparo, credenciais do Mercado Livre) só nos segredos do GitHub e do cron-job.org, nunca no código.
- Estado e histórico na branch `data`, gravados só quando algo muda.

## Review Focus

- Preço escrito de formas diferentes ("R$ 3.599,90", "3599,90", "R$ 3.599") ou ausente: deve virar o `Decimal` certo ou ser ignorado, nunca um alerta errado (Task 3).
- Oferta com preço absurdamente baixo (< R$ 2.000, quase certo anúncio errado ou acessório): vira uma mensagem "suspeito, confira", nunca um alerta máximo (Task 6).
- Fonte devolve lista vazia ou HTML de bloqueio: conta como falha da fonte, não como "sem ofertas" (Task 7).
- Envio ao Telegram falha: o alerta não pode ser marcado como enviado; tenta de novo na próxima checagem (Task 8).
- Preço sobe acima de R$ 4.000 e depois cai de novo: deve alertar de novo; mesmo preço repetido não pode alertar (Task 6).
- Estado perdido ou execução reiniciada no meio das 5 repetições: não pode recomeçar a contagem e floodar (Task 9).

---

### Task 1: Esqueleto do projeto, modelos e configuração

**Files:**
- Create: `pyproject.toml`, `requirements.txt`, `.gitignore`
- Create: `src/ps5watch/__init__.py`, `src/ps5watch/models.py`, `src/ps5watch/config.py`, `config.yaml`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `class ModelKey(str, Enum)`: `SLIM_DISC = "slim_disc"`, `SLIM_DIGITAL = "slim_digital"`
  - `@dataclass(frozen=True) class Coupon`: `store: str`, `code: str`, `description: str`, `source_url: str`, `seen_at: datetime`
  - `@dataclass(frozen=True) class Offer`: `model: ModelKey`, `store: str`, `price_cash: Decimal`, `price_installment: Decimal | None`, `url: str`, `source: str`, `seen_at: datetime`, `shipping_included: bool | None`
  - `@dataclass(frozen=True) class Config`: `normal_threshold: Decimal`, `max_threshold: Decimal`, `suspect_floor: Decimal`, `max_repeats: int`, `max_repeat_interval_s: int`, `allowed_stores: frozenset[str]`, `health_after_s: int`, `loop_duration_s: int`, `loop_interval_s: int`
  - `def load_config(path: Path) -> Config`

- [ ] **Step 1: Run `git init -b main`, create `.gitignore` (Python, `.venv`, `__pycache__`) and `requirements.txt` (`requests`, `beautifulsoup4`, `lxml`, `pytest`, `pyyaml`); create and activate a venv; `pip install -r requirements.txt`.**
- [ ] **Step 2: Write the failing test** `test_load_config_reads_spec_values` in `tests/test_config.py`: loads `config.yaml`, asserts `normal_threshold == Decimal("4000")`, `max_threshold == Decimal("3600")`, `suspect_floor == Decimal("2000")`, `max_repeats == 5`, `max_repeat_interval_s == 60`, `health_after_s == 600`, and `"amazon" in allowed_stores`.
- [ ] **Step 3: Run `pytest tests/test_config.py -v`; expect FAIL (módulo não existe).**
- [ ] **Step 4: Implement `models.py` and `config.py`, and write `config.yaml`.** `allowed_stores` (minúsculas, sem acento): amazon, mercado livre, magazine luiza, magalu, kabum, americanas, casas bahia, fast shop, carrefour. `loop_duration_s: 290`, `loop_interval_s: 45`. Valores em `Decimal` a partir de string.
- [ ] **Step 5: Run `pytest -v`; expect PASS.**
- [ ] **Step 6: Commit** `git add -A && git commit -m "chore: project skeleton, models and config"`

### Task 2: Teste rápido (spike) — as fontes abrem a partir do GitHub Actions?

Este é o ponto de decisão do plano. Não escreve código de produto.

**Files:**
- Create: `scripts/probe_sources.py`, `.github/workflows/probe.yml`

**Interfaces:**
- Produces: `scripts/probe_sources.py` imprime, para cada URL candidata, `status`, tamanho do corpo e se o texto contém "R$"; sai com código 0 sempre.

- [ ] **Step 1: Find the product-page URLs** do PS5 Slim com leitor e do PS5 Slim Digital no Zoom e no Buscapé (pela busca de cada site); coloque as quatro URLs em `config.yaml` sob `sources.zoom.urls` e `sources.buscape.urls` (por modelo).
- [ ] **Step 2: Implement `scripts/probe_sources.py`** com `requests` e um `User-Agent` de navegador comum, timeout 20 s, uma tentativa por URL.
- [ ] **Step 3: Write `probe.yml`** (`workflow_dispatch` apenas, Python 3.12, instala dependências, roda o script).
- [ ] **Step 4: Peça ao João para criar o repositório público no GitHub e fazer `git push`** (ver "Tarefas do João" no fim). Dispare o workflow e leia o log.
- [ ] **Step 5: Decide.** Se Zoom ou Buscapé responderam `200` com "R$" no corpo: siga o plano normalmente (pule a Task 5b). Se ambos foram bloqueados (403/captcha/sem preços): **não** construa a Task 4; faça a Task 5 e a Task 5b, e avise o João antes de seguir. Registre o resultado em `docs/superpowers/specs/2026-11-24-ps5-price-alert-design.md` (seção "Resultado do teste de fonte").
- [ ] **Step 6: Commit** `git commit -m "chore: probe sources from GitHub Actions"`

### Task 3: Preço em reais e casamento de modelo

**Files:**
- Create: `src/ps5watch/parsing.py`, `src/ps5watch/matching.py`
- Test: `tests/test_parsing.py`, `tests/test_matching.py`

**Interfaces:**
- Consumes: `ModelKey`
- Produces:
  - `def parse_brl(text: str) -> Decimal | None`
  - `def match_model(title: str) -> ModelKey | None`

- [ ] **Step 1: Write the failing tests.**
  - `test_parse_brl_formats`: `"R$ 3.599,90"`, `"3599,90"` → `Decimal("3599.90")`; `"R$ 3.599"` → `Decimal("3599")`; `"R$ 4.299,00 à vista"` → `Decimal("4299.00")`.
  - `test_parse_brl_rejects_garbage`: `""`, `"indisponível"`, `"R$"` → `None`.
  - `test_match_model_disc`: `"Console PlayStation 5 Slim com Leitor de Discos 1TB"` → `SLIM_DISC`.
  - `test_match_model_digital`: `"PS5 Slim Digital 1TB Edição Digital"` → `SLIM_DIGITAL`.
  - `test_match_model_excludes`: `"PlayStation 5 Pro 2TB"`, `"Controle DualSense PS5"`, `"PS5 Slim Disco + 2 Jogos"`, `"Console PS5 Slim Usado"`, `"Capa para PS5 Slim"` → todos `None`.
- [ ] **Step 2: Run `pytest tests/test_parsing.py tests/test_matching.py -v`; expect FAIL.**
- [ ] **Step 3: Implement** as duas funções. `match_model`: normaliza (minúsculas, sem acento); exige "playstation 5" ou "ps5" e "slim"; "digital" ⇒ `SLIM_DIGITAL`, senão "disco"/"leitor"/"mídia física" ⇒ `SLIM_DISC`; exclui por palavras (pro, usado, seminovo, controle, capa, suporte, jogo/jogos, bundle, combo, kit, "+"), lista de exclusão numa constante no módulo.
- [ ] **Step 4: Run the tests; expect PASS.**
- [ ] **Step 5: Commit** `git commit -m "feat: BRL parsing and model matching"`

### Task 4: Fontes Zoom e Buscapé (somente se a Task 2 passou)

**Files:**
- Create: `src/ps5watch/sources/__init__.py`, `src/ps5watch/sources/base.py`, `src/ps5watch/sources/aggregator.py`
- Create: `tests/fixtures/zoom_slim_disc.html`, `tests/fixtures/buscape_slim_digital.html` (páginas reais salvas pelo spike)
- Test: `tests/test_sources_aggregator.py`

**Interfaces:**
- Consumes: `Offer`, `ModelKey`, `parse_brl`, `match_model`, `Config`
- Produces:
  - `class SourceError(Exception)`
  - `class Source(Protocol)`: `name: str`; `def fetch(self) -> list[Offer]` (levanta `SourceError` em bloqueio, HTTP ≠ 200 ou página sem ofertas reconhecíveis)
  - `def parse_aggregator_page(html: str, model: ModelKey, source: str, now: datetime) -> list[Offer]`
  - `class AggregatorSource`: construtor `(name: str, urls: dict[ModelKey, str], session: requests.Session, clock: Callable[[], datetime])`, implementa `Source`

- [ ] **Step 1: Write the failing tests** com os HTML salvos: `test_parse_zoom_page_returns_store_offers` (≥ 1 oferta, cada uma com `store` não vazio, `price_cash` > 0, `url` começando com `http`); `test_parse_page_without_offers_raises_source_error` (HTML de bloqueio ⇒ `SourceError` via `AggregatorSource.fetch` com sessão falsa); `test_fetch_non_200_raises_source_error`.
- [ ] **Step 2: Run `pytest tests/test_sources_aggregator.py -v`; expect FAIL.**
- [ ] **Step 3: Implement.** Extrair loja, preço à vista (Pix quando houver, senão o preço único), preço parcelado, link e frete; descartar ofertas cujo título não passe em `match_model` ou cuja loja não esteja em `allowed_stores`. Cabeçalhos de navegador, timeout 15 s.
- [ ] **Step 4: Run the tests; expect PASS.**
- [ ] **Step 5: Commit** `git commit -m "feat: Zoom/Buscape aggregator source"`

### Task 5: Fonte Mercado Livre (API oficial)

**Files:**
- Create: `src/ps5watch/sources/mercadolivre.py`
- Create: `tests/fixtures/ml_search_slim_disc.json`
- Test: `tests/test_sources_mercadolivre.py`

**Interfaces:**
- Consumes: `Source`, `SourceError`, `Offer`, `match_model`
- Produces: `class MercadoLivreSource(name="mercadolivre")`, construtor `(queries: dict[ModelKey, str], session, clock, access_token: str | None)`; `fetch() -> list[Offer]`; `def parse_ml_results(payload: dict, model: ModelKey, now: datetime) -> list[Offer]`

- [ ] **Step 1: Confirmar na documentação oficial** (`developers.mercadolivre.com.br`) o formato atual da busca e dos preços (os campos de preço do `/items` estão migrando para endpoints próprios) e se a busca exige token; salvar uma resposta real em `tests/fixtures/ml_search_slim_disc.json`.
- [ ] **Step 2: Write the failing tests:** `test_parse_ml_results_keeps_only_matching_new_items` (descarta usados e títulos que `match_model` rejeita); `test_parse_ml_results_uses_cash_price`; `test_fetch_http_error_raises_source_error`.
- [ ] **Step 3: Run `pytest tests/test_sources_mercadolivre.py -v`; expect FAIL.**
- [ ] **Step 4: Implement** `parse_ml_results` e `MercadoLivreSource.fetch`; só vendedores reputados ou loja oficial (campo confirmado no Step 1). Se exigir app registrado, ler `ML_ACCESS_TOKEN` do ambiente e pedir ao João (ver "Tarefas do João"); se atrasar, deixar a fonte desativada em `config.yaml` (`sources.mercadolivre.enabled: false`).
- [ ] **Step 5: Run the tests; expect PASS.**
- [ ] **Step 6: Commit** `git commit -m "feat: Mercado Livre source"`

### Task 5b: Fontes diretas de lojas (somente se a Task 2 bloqueou o Zoom/Buscapé)

**Files:**
- Create: `src/ps5watch/sources/kabum.py`, `src/ps5watch/sources/magalu.py` (e outras que o teste mostrar acessíveis)
- Test: `tests/test_sources_direct.py`, fixtures `tests/fixtures/kabum_*.html`, `magalu_*.html`

**Interfaces:**
- Consumes/Produces: mesma interface `Source` da Task 4; uma classe por loja, `fetch() -> list[Offer]`.

- [ ] **Step 1: Probe** com `scripts/probe_sources.py` (ampliar a lista) quais lojas abrem a partir do Actions; só implementar as que abrem.
- [ ] **Step 2: Write the failing tests** por loja (`test_<loja>_parses_price_and_url`, `test_<loja>_block_page_raises_source_error`) com HTML salvo.
- [ ] **Step 3: Run; expect FAIL. Step 4: Implement. Step 5: Run; expect PASS.**
- [ ] **Step 6: Commit** `git commit -m "feat: direct store sources (fallback)"`

### Task 5c: Cupons ativos (somente aviso, não muda limites)

**Files:**
- Create: `src/ps5watch/coupons.py`
- Create: `tests/fixtures/coupons_promobit.html`
- Test: `tests/test_coupons.py`

**Interfaces:**
- Consumes: `Coupon` (definido na Task 1 em `models.py`: `store: str`, `code: str`, `description: str`, `source_url: str`, `seen_at: datetime`), `Config`
- Produces:
  - `def parse_coupons_page(html: str, store: str, now: datetime) -> list[Coupon]`
  - `class CouponSource`: construtor `(urls: dict[str, str], session, clock)`; `def fetch(self) -> list[Coupon]` (nunca levanta; devolve `[]` e registra o erro em log se a página falhar)
  - `def coupons_for_store(coupons: list[Coupon], store: str) -> list[Coupon]`

- [ ] **Step 1: Escolher uma página de cupons** (Promobit, Pelando ou Cuponomia) por loja aceita e salvar uma real em `tests/fixtures/coupons_promobit.html`; guardar as URLs em `config.yaml` sob `sources.coupons.urls`.
- [ ] **Step 2: Write the failing tests:** `test_parse_coupons_page_returns_code_and_description`; `test_parse_coupons_ignores_expired`; `test_fetch_returns_empty_list_when_page_fails` (sessão falsa que levanta erro ⇒ `[]`, sem exceção); `test_coupons_for_store_matches_normalized_name`.
- [ ] **Step 3: Run `pytest tests/test_coupons.py -v`; expect FAIL.**
- [ ] **Step 4: Implement.** Só cupons marcados como ativos/não expirados; guardar o texto da condição quando houver, sem tentar interpretá-lo.
- [ ] **Step 5: Run; expect PASS.**
- [ ] **Step 6: Wire in** (feito junto com as Tasks 8 e 10): `format_message` aceita `coupons: list[Coupon]` e acrescenta "Cupom ativo: <CODIGO> — <descrição>. Confira as condições." às mensagens `normal` e `max` da loja da oferta; `run_once` busca cupons uma vez por iteração e **não** os passa para `decide_alerts`. Testes: `test_format_message_includes_coupon_note` (Task 8) e `test_coupon_does_not_change_thresholds` (Task 10: preço R$ 4.100 com cupom ativo ⇒ nenhum alerta).
- [ ] **Step 7: Commit** `git commit -m "feat: coupon notices (informational)"`

### Task 6: Regras de alerta

**Files:**
- Create: `src/ps5watch/alerts.py`
- Test: `tests/test_alerts.py`

**Interfaces:**
- Consumes: `Offer`, `ModelKey`, `Config`
- Produces:
  - `@dataclass class ModelAlertState`: `last_alert_price: Decimal | None`, `was_below: bool`, `max_sent: int`, `last_max_at: datetime | None`
  - `@dataclass class AlertState`: `models: dict[ModelKey, ModelAlertState]` (com `to_dict()` / `from_dict()`)
  - `@dataclass class Message`: `kind: Literal["normal","max","suspect","health"]`, `model: ModelKey | None`, `offer: Offer | None`, `low_30d: Decimal | None`
  - `def decide_alerts(offers: list[Offer], state: AlertState, low_30d: dict[ModelKey, Decimal | None], now: datetime, cfg: Config) -> tuple[list[Message], AlertState]` (função pura; só considera o menor `price_cash` por modelo; ignora lojas fora de `allowed_stores`)

- [ ] **Step 1: Write the failing tests** (fixtures: `make_offer(model, price, store="kabum")`):
  - `test_below_4000_alerts_once`: preço 3.950 → 1 `normal`; segunda chamada com o mesmo preço → 0 mensagens.
  - `test_lower_price_alerts_again`: 3.950 depois 3.900 → novo `normal`.
  - `test_rise_above_then_drop_alerts_again`: 3.950 → 4.100 (0 msgs) → 3.950 (novo `normal`).
  - `test_below_3600_sends_max_and_repeats_up_to_5`: 3.500 em `t0` → `max`; em `t0+60s` ... até 5 no total; 6ª chamada em `t0+300s` → 0; chamada em `t0+30s` → 0 (intervalo).
  - `test_max_repeat_resets_on_new_lower_price`: depois de 5 envios, preço cai para 3.400 → novo `max` e contagem recomeça.
  - `test_each_model_independent`: disco a 3.500 e digital a 3.900 → um `max` (disco) e um `normal` (digital).
  - `test_price_at_threshold_does_not_alert`: exatamente 4.000 → 0; 3.600 exatos → só `normal`.
  - `test_suspect_price_below_2000_is_not_max`: 1.500 → 1 `suspect`, 0 `max`.
  - `test_store_not_allowed_is_ignored`: loja `"lojinha xyz"` a 3.000 → 0 mensagens.
- [ ] **Step 2: Run `pytest tests/test_alerts.py -v`; expect FAIL.**
- [ ] **Step 3: Implement `decide_alerts`** como função pura sobre o estado recebido, devolvendo o novo estado (sem I/O, sem relógio global).
- [ ] **Step 4: Run the tests; expect PASS.**
- [ ] **Step 5: Commit** `git commit -m "feat: alert decision rules"`

### Task 7: Saúde das fontes

**Files:**
- Create: `src/ps5watch/health.py`
- Test: `tests/test_health.py`

**Interfaces:**
- Consumes: `Message`, `Config`
- Produces:
  - `@dataclass class SourceHealth`: `failing_since: datetime | None`, `alerted: bool`
  - `@dataclass class HealthState`: `sources: dict[str, SourceHealth]` (com `to_dict()` / `from_dict()`)
  - `def update_health(state: HealthState, results: dict[str, str | None], now: datetime, cfg: Config) -> tuple[list[tuple[str, str]], HealthState]`; `results[nome]` é `None` se OK ou o texto do erro; devolve lista de `(nome, "down" | "up")`

- [ ] **Step 1: Write the failing tests:** `test_no_alert_before_10_minutes` (falha por 9 min → vazio); `test_alert_after_10_minutes_once` (10 min → `[("zoom","down")]`; chamada seguinte → vazio); `test_recovery_alert` (volta OK → `[("zoom","up")]`); `test_one_source_down_alerts_even_if_others_ok`; `test_empty_offer_list_counts_as_failure` (a camada que chama marca lista vazia como erro; teste no runner na Task 10).
- [ ] **Step 2: Run; expect FAIL. Step 3: Implement. Step 4: Run; expect PASS.**
- [ ] **Step 5: Commit** `git commit -m "feat: source health tracking"`

### Task 8: Telegram e texto das mensagens

**Files:**
- Create: `src/ps5watch/telegram.py`, `src/ps5watch/formatting.py`
- Test: `tests/test_telegram.py`, `tests/test_formatting.py`

**Interfaces:**
- Consumes: `Message`, `Offer`
- Produces:
  - `def format_message(msg: Message) -> str`
  - `class TelegramClient`: construtor `(token: str, chat_id: str, session)`; `def send(self, text: str) -> bool` (devolve `False` em qualquer falha, nunca levanta)

- [ ] **Step 1: Write the failing tests:**
  - `test_format_max_message_contains_required_fields`: contém "ALERTA MÁXIMO", modelo ("PS5 Slim com leitor" ou "PS5 Slim Digital"), loja, "R$ 3.499,00", parcelado, "menor preço dos últimos 30 dias" e a URL.
  - `test_format_without_history_says_sem_historico_ainda`.
  - `test_format_flags_shipping_not_included` (quando `shipping_included is False` ou `None`: "frete não incluído").
  - `test_format_suspect_and_health_messages`.
  - `test_send_posts_to_bot_api`: sessão falsa recebe POST em `https://api.telegram.org/bot<token>/sendMessage` com `chat_id` e `text`; devolve `True`.
  - `test_send_returns_false_on_http_error_and_on_exception`.
- [ ] **Step 2: Run; expect FAIL. Step 3: Implement** (preços no formato `R$ 3.499,00`). **Step 4: Run; expect PASS.**
- [ ] **Step 5: Commit** `git commit -m "feat: Telegram client and message formatting"`

### Task 9: Estado e histórico na branch `data`

**Files:**
- Create: `src/ps5watch/store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: `AlertState`, `HealthState`, `Offer`
- Produces:
  - `def record_history(history: dict, offers: list[Offer], now: datetime) -> bool` (altera `history` em memória; devolve `True` só se houve mudança de preço de algum par modelo+loja, ou se passou 1 hora desde o último ponto; formato `history[model][store] = [[iso_time, price_cash], ...]`)
  - `def low_30d(history: dict, model: ModelKey, now: datetime) -> Decimal | None`
  - `class DataStore`: construtor `(repo_dir: Path, runner: Callable[[list[str]], str])`; `load() -> tuple[AlertState, HealthState, dict]` (arquivos `state.json`, `history.json`; ausentes ⇒ estado vazio); `save(alert, health, history, changed: bool) -> None` (só faz `commit` e `push` da branch `data` se `changed`; em falha de push faz `pull --rebase` e tenta mais 2 vezes)

- [ ] **Step 1: Write the failing tests:** `test_record_history_only_on_change` (mesmo preço duas vezes ⇒ 2ª devolve `False`; preço novo ⇒ `True`); `test_record_history_hourly_checkpoint`; `test_low_30d_ignores_older_points`; `test_load_missing_files_returns_empty_state`; `test_save_does_not_commit_when_unchanged` (runner falso não recebe `commit`); `test_save_retries_push_after_conflict`; `test_state_roundtrip_preserves_max_sent` (a contagem das 5 repetições sobrevive a salvar e carregar).
- [ ] **Step 2: Run; expect FAIL. Step 3: Implement** com comandos `git` via `runner`. **Step 4: Run; expect PASS.**
- [ ] **Step 5: Commit** `git commit -m "feat: state and history storage on data branch"`

### Task 10: Laço principal

**Files:**
- Create: `src/ps5watch/run.py`
- Test: `tests/test_run.py`

**Interfaces:**
- Consumes: tudo acima
- Produces:
  - `def run_once(sources: list[Source], store: DataStore, telegram: TelegramClient, cfg: Config, now: datetime) -> None`
  - `def run_loop(sources, store, telegram, cfg, clock, sleep) -> None` (chama `run_once` a cada `loop_interval_s` até `loop_duration_s`)
  - `def main() -> None` (lê `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `ML_ACCESS_TOKEN` do ambiente; falha com mensagem clara se faltar)

- [ ] **Step 1: Write the failing tests** (fontes e Telegram falsos):
  - `test_run_once_sends_alert_and_marks_sent_only_if_telegram_ok`: Telegram devolve `False` ⇒ o estado salvo NÃO registra o alerta; na próxima chamada ele é reenviado.
  - `test_run_once_empty_source_result_counts_as_health_failure`.
  - `test_run_once_continues_when_one_source_raises`: uma fonte levanta `SourceError`, a outra devolve ofertas ⇒ alerta sai.
  - `test_run_once_persists_state_between_calls_so_repeats_not_restarted`.
  - `test_run_loop_runs_expected_number_of_iterations` (clock e sleep falsos: 290 s / 45 s ⇒ 7 iterações).
- [ ] **Step 2: Run; expect FAIL. Step 3: Implement** (carrega estado, busca todas as fontes, atualiza saúde, calcula `low_30d`, `decide_alerts`, envia, só então marca como enviado, `record_history`, `store.save`). **Step 4: Run; expect PASS.**
- [ ] **Step 5: Commit** `git commit -m "feat: main polling loop"`

### Task 11: Workflow do GitHub Actions e disparo de 1 minuto

**Files:**
- Create: `.github/workflows/watch.yml`, `docs/setup.md`

**Interfaces:**
- Produces: workflow `watch` com gatilhos `workflow_dispatch` e `schedule: "*/5 * * * *"`; `concurrency: { group: watch, cancel-in-progress: false }`; `timeout-minutes: 8`; `permissions: { contents: write }`; usa os segredos `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `ML_ACCESS_TOKEN`; faz checkout da branch `data` num diretório separado.

- [ ] **Step 1: Write `watch.yml`** conforme acima, com `python -m ps5watch.run`.
- [ ] **Step 2: Write `docs/setup.md`** com o passo a passo do João (ver "Tarefas do João"), incluindo a chamada do cron-job.org: `POST https://api.github.com/repos/<dono>/<repo>/actions/workflows/watch.yml/dispatches`, cabeçalhos `Authorization: Bearer <token>` e `Accept: application/vnd.github+json`, corpo `{"ref":"main"}`, a cada 1 minuto.
- [ ] **Step 3: Validate** com `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/watch.yml'))"`; expect: sem erro.
- [ ] **Step 4: Commit** `git commit -m "ci: watch workflow and setup guide"`

### Task 12: Página web com histórico

**Files:**
- Create: `site/index.html`, `site/app.js`, `scripts/publish_site.py`
- Test: `tests/test_publish_site.py`

**Interfaces:**
- Consumes: formato de `history.json` da Task 9
- Produces: `site/index.html` + `app.js` (Chart.js 4.4.1 via cdnjs) mostrando, por modelo, um gráfico de linhas por loja, o menor preço atual por loja e o menor preço do período, e as faixas de R$ 4.000 e R$ 3.600; `def publish_site(site_dir: Path, data_dir: Path) -> None` copia `index.html` e `app.js` para o diretório da branch `data` (que o GitHub Pages serve).

- [ ] **Step 1: Write the failing test** `test_publish_site_copies_assets_and_keeps_history` (`index.html` e `app.js` aparecem em `data_dir`; `history.json` existente não é apagado).
- [ ] **Step 2: Run; expect FAIL. Step 3: Implement** `publish_site` e a página (lê `history.json` por caminho relativo; texto em português; mostra "sem dados ainda" quando vazio; layout legível no celular). **Step 4: Run; expect PASS.**
- [ ] **Step 5: Commit** `git commit -m "feat: static history page"`

### Task 13: Ensaio completo e checklist de entrada no ar

**Files:**
- Create: `scripts/dry_run.py`
- Test: `tests/test_dry_run.py`

**Interfaces:**
- Produces: `scripts/dry_run.py` roda `run_once` com uma fonte falsa que devolve R$ 3.500 e um Telegram "impresso no terminal", sem rede; o teste verifica que sai exatamente uma mensagem "ALERTA MÁXIMO" e que, numa segunda chamada 60 s depois, sai a repetição #2.

- [ ] **Step 1: Write the failing test** `test_dry_run_prints_max_alert_then_repeat`.
- [ ] **Step 2: Run; expect FAIL. Step 3: Implement. Step 4: Run `pytest -v`; expect todos PASS.**
- [ ] **Step 5: Com o João:** mandar uma mensagem de teste real pelo bot ("teste ok"), disparar o workflow `watch` manualmente, confirmar no log que uma execução completa roda sem erro e que a branch `data` recebe `state.json`, e confirmar que o cron-job.org dispara a cada minuto (aba "Actions" mostrando runs em fila/rodando).
- [ ] **Step 6: Commit** `git commit -m "test: dry run and go-live checklist"`

---

## Tarefas do João (só ele pode fazer)

1. Criar o bot no Telegram com o @BotFather, mandar uma mensagem qualquer para ele e descobrir o chat id. **Não cole o token no chat**; coloque-o direto nos segredos do GitHub (`TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`).
2. Criar o repositório **público** no GitHub e fazer o primeiro `push`.
3. Criar um token do GitHub de escopo mínimo (só Actions: write neste repositório) e usá-lo no cron-job.org.
4. Criar a conta no cron-job.org e o job de 1 minuto (passo a passo em `docs/setup.md`).
5. Se a API do Mercado Livre exigir, registrar um aplicativo e guardar o token como segredo `ML_ACCESS_TOKEN`.
6. Ativar o GitHub Pages apontando para a branch `data`.

## Autorrevisão

- Cobertura do desenho: dois modelos (Tasks 1, 3), limites e repetição (Task 6), Pix à vista (Tasks 4, 5, 6), saúde (Task 7), Telegram e conteúdo da mensagem (Task 8), estado só na mudança (Task 9), laço e latência (Tasks 10, 11), página web (Task 12), teste da fonte e plano de escape (Tasks 2, 5b), pendências do João (seção própria).
- Tipos usados em tarefas posteriores batem com os definidos antes (`Offer`, `Message`, `AlertState`, `HealthState`, `DataStore`, `Source`).
- Decisão minha fora do desenho: preços abaixo de R$ 2.000 viram mensagem "suspeito", nunca alerta máximo (Review Focus).
