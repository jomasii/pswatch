# Painel ao vivo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The watcher publishes the current offers with their links, and the GitHub Pages panel shows them nearly live in a dark dashboard with two rankings.

**Architecture:**
- History points gain a link: `[time, price, url]`.
- A new `snapshot.py` builds `offers.json`. `run_once` saves it through `DataStore` when the offers change, or every 5 min as a heartbeat.
- The static page (`site/index.html` + `site/app.js`) polls `offers.json` and `history.json` through the GitHub contents API with ETag, and falls back to the Pages copies.

**Tech Stack:** Python 3.12, pytest, vanilla JS, Chart.js 4.4.1 (cdnjs), GitHub Pages and the GitHub REST API.

**Spec:** `docs/superpowers/specs/2026-11-25-painel-ao-vivo-design.md`

## Global Constraints
- Done and pushed before the Thursday 2026-11-26 night freeze. No change may break `python -m ps5watch.run`.
- Heartbeat: 300 s. "Vigia parado?" warning: 600 s since `checked_at`.
- Polling: `offers.json` every 30 s, `history.json` every 300 s. Endpoint: `https://api.github.com/repos/jomasii/pswatch/contents/<file>?ref=data` with `Accept: application/vnd.github.raw`.
- Fallback: the same-origin `offers.json` / `history.json`, used on a 403/429 response or a network error.
- Rankings list only offers with `price >= suspect_floor` from `allowed_stores`.
- Data text is inserted with `textContent` only. An `href` is set only when the URL starts with `https://`. Links open with `target="_blank" rel="noopener noreferrer"`.
- Interface text is in Portuguese (pt-BR) and prices use BRL formatting.

## Review Focus
- Old 2-element history points mixed with new 3-element points. `low_30d`, `record_history` and the page must accept both (test in Task 1, page check in Task 3).
- Same price, new link. Do not add a history point and do not count it as a change; the link in `offers.json` still updates (Task 1 and Task 2 tests).
- An empty offer list, for example when every source is down, must still write `offers.json` with `offers: []` and `checked_at`, so the page shows "sem ofertas" and not stale ones (Task 2 test).
- Offers that are identical except for `seen_at` must not trigger a commit every 45 s (Task 2 test).
- A malicious or odd URL (`javascript:`, `http:`) must never become a clickable link (Task 3 browser check).

---

### Task 1: Store the link in history points

**Files:**
- Modify: `src/ps5watch/store.py` (`record_history`, `low_30d`)
- Test: `tests/test_store.py`

**Interfaces:**
- Produces:
  - `record_history(history, offers, now) -> bool` (unchanged signature). New points are `[iso_time, str(price), url]`.
  - `low_30d` reads `p[0]` and `p[1]` only.

- [ ] **Step 1: Write failing tests**

```python
def test_record_history_stores_link_of_cheapest_offer():
    history = {}
    record_history(history, [make_offer(price="3900", url="https://a/1"), make_offer(price="3950", url="https://a/2")], T0)
    assert history["slim_disc"]["kabum"] == [[T0.isoformat(), "3900", "https://a/1"]]

def test_record_history_same_price_new_link_is_not_a_change():
    history = {}
    record_history(history, [make_offer(price="3900", url="https://a/1")], T0)
    assert record_history(history, [make_offer(price="3900", url="https://a/9")], T0 + timedelta(minutes=1)) is False

def test_old_two_element_points_still_work():
    history = {"slim_disc": {"kabum": [[(T0 - timedelta(days=1)).isoformat(), "3800"]]}}
    assert low_30d(history, ModelKey.SLIM_DISC, T0) == Decimal("3800")
    assert record_history(history, [make_offer(price="3900")], T0) is True
```

- [ ] **Step 2: Run** `python -m pytest tests/test_store.py -q`. Expected: the 3 new tests FAIL.
- [ ] **Step 3: Implement.**
  - Keep the cheapest offer per key (not only its price) so its `url` is available.
  - Read `last = points[-1]` as `last[0]`, `last[1]`.
  - In `low_30d`, iterate `for p in points` and use `p[0]` and `p[1]`.
- [ ] **Step 4: Run** `python -m pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit** `feat: keep offer link in price history`.

### Task 2: Publish `offers.json` from the watcher

**Files:**
- Create: `src/ps5watch/snapshot.py`
- Modify: `src/ps5watch/store.py` (`DataStore.load_snapshot`, `DataStore.save`), `src/ps5watch/run.py` (`run_once`)
- Test: `tests/test_snapshot.py`, `tests/test_run.py`, `tests/test_store.py`

**Interfaces:**
- Consumes: history points `[time, price, url?]` from Task 1.
- Produces:
  - `build_snapshot(offers: list[Offer], history: dict, cfg: Config, now: datetime) -> dict`, returning `{"checked_at": iso, "offers": [ {model, store, price, url, bundle, title, promo, source, since} ... ]}`.
    - Offers are filtered to `price_cash >= cfg.suspect_floor` and `store in cfg.allowed_stores`.
    - They are sorted by price, then store.
    - `price` is a string.
    - `since` is the ISO time of the earliest point in the latest unbroken run of history points for that (model, store) with the same price, or `now` when there is none.
    - Duplicates are dropped: the same (model, store, price, url) appears once.
  - `snapshot_changed(old: dict | None, new: dict, now: datetime, heartbeat_s: int = 300) -> bool`.
    - Returns True when `old` is None, when `old["offers"] != new["offers"]`, or when `old["checked_at"]` is 300 s or more before `now`.
  - `DataStore.load_snapshot() -> dict | None` reads `offers.json`.
  - `DataStore.save(alert, health, history, changed, snapshot: dict | None = None)` also writes `offers.json` when `snapshot` is given.
  - `run_once` follows `getattr(store, "load_snapshot", None)` for test fakes:
    - It computes `snapshot_changed`, ORs it into `changed`, and passes `snapshot=new_snapshot` only when that is true.
    - When there is no change, it keeps the previously saved `checked_at` and does not write.

- [ ] **Step 1: Write failing tests** in `tests/test_snapshot.py`:
  - `test_snapshot_filters_suspect_and_unknown_stores_and_sorts`: offers at R$ 1.500 (kabum), R$ 3.900 (lojax) and R$ 4.100 / 3.950 (kabum, amazon). The result has 2 offers in the order 3950 amazon, 4100 kabum, and `price == "3950"`.
  - `test_snapshot_since_uses_start_of_current_price_run`:
    - history for kabum is `[[T0-3h,"4200","u"],[T0-2h,"4100","u"],[T0-1h,"4100","u"]]`;
    - the current offer is kabum at 4100;
    - expected `since == (T0-2h).isoformat()`.
  - `test_snapshot_empty_offers_still_has_checked_at`: `build_snapshot([], {}, cfg, T0) == {"checked_at": T0.isoformat(), "offers": []}`.
  - `test_snapshot_changed_rules`, which covers four cases:
    - `None` gives True;
    - the same offers at +60 s give False;
    - the same offers at +300 s give True;
    - a different price gives True.
  - In `tests/test_run.py`, `test_run_once_does_not_commit_identical_offers_every_check`:
    - the `MemoryStore` gains `snapshot=None`, `load_snapshot()` and a `save(..., snapshot=None)` that stores it;
    - the same source runs at T0, T0+45 s and T0+90 s;
    - `saves` grows only on the first run;
    - at T0+300 s it grows again, from the heartbeat.
  - In `tests/test_store.py`, `test_save_writes_offers_json_and_load_snapshot_reads_it`.
- [ ] **Step 2: Run** `python -m pytest -q`. Expected: the new tests FAIL because they cannot import `ps5watch.snapshot`.
- [ ] **Step 3: Implement** `snapshot.py` and the `DataStore` and `run_once` changes described in the Interfaces block. `run_once` builds the snapshot from `offers` after `record_history`, so `since` sees the current point.
- [ ] **Step 4: Run** `python -m pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit** `feat: publish current offers snapshot (offers.json) with 5-min heartbeat`.

### Task 3: Dark live dashboard

**Files:**
- Modify: `site/index.html`, `site/app.js` (full rewrite)
- Reference: `.superpowers/brainstorm/layout-v2.html` (approved look)

**Interfaces:**
- Consumes:
  - `offers.json` (the Task 2 shape);
  - `history.json` (`{model: {store: [[time, price, url?], ...]}}`).
- Produces: nothing for other tasks. `scripts/publish_site.py` already copies `index.html` and `app.js`.

- [ ] **Step 1: Write `site/index.html`.** It uses a dark theme with CSS tokens taken from `layout-v2.html`, plus a light variant under `prefers-color-scheme: light`. Its sections are:
  - `#live`, the status bar;
  - `#heroes`;
  - `#now`, with filter chips Todos / Digital / Com leitor / Sem combos and a table;
  - `#lows`, a table;
  - `#charts`.

  Chart.js 4.4.1 comes from cdnjs, as today.
- [ ] **Step 2: Write `site/app.js`.** Pure helpers come first, as plain functions so they can be checked in the console:
  - `fetchJson(name, etagCache)`
    - Fetches from the API with `If-None-Match`.
    - On 304 it returns the cached body.
    - On 403/429 or an error it fetches the same-origin `name` with `cache: "no-store"` and sets the `slow` flag.
  - `safeUrl(u)` returns `u` only if `u.startsWith("https://")`, else `null`.
  - `episodes(history)`
    - Merges consecutive points with equal price per (model, store).
    - Returns `{model, store, price, url, start, end|null}`, where `end` is the next different point's time and `null` means the last run, "ainda no ar".
    - Sorted by price; top 10.
  - `heroFor(model, offers)` returns the cheapest offer and its gap to 4000.
    - Labels: "Faltam R$ X para o alerta de R$ 4.000"; below 4000 "Abaixo do alerta!"; below 3600 "ALERTA MÁXIMO".
    - Border classes: `near` when the price is ≤ 4300, `hit` when it is < 4000.

  Rendering: every node is built with `document.createElement` and `textContent`; `href` comes only from `safeUrl`.

  Timers: offers every 30 s, history every 300 s, and a 1 s tick for the "há X s" text and the stale check (> 600 s → red bar "Vigia parado? Última checagem há X min").
- [ ] **Step 3: Verify in the browser with real data.**
  - Copy the live data into a temp folder next to the site: run `gh api ... offers.json/history.json` and save the output beside copies of `site/index.html` and `app.js`.
  - Serve the folder with `python -m http.server` through `.claude/launch.json` and open it in the browser pane.
  - Check:
    - the heroes, both tables, the filters and the charts render;
    - the links open the stores;
    - `safeUrl("javascript:alert(1)") === null` in the console;
    - old 2-element points show no button;
    - no console errors.

  `offers.json` will not exist on the data branch until Task 2 is live, so build one with `build_snapshot` from the current `history.json` for this check.
- [ ] **Step 4: Commit** `feat: dark live dashboard with offer links and rankings`.

### Task 4: Ship and verify live

- [ ] **Step 1: Run** `python -m pytest -q`. Expected: all pass. Then push `main`.
- [ ] **Step 2:** Wait for a `watch` run on the new commit to succeed. Then confirm that `offers.json` exists on the `data` branch: `gh api repos/jomasii/pswatch/contents/offers.json?ref=data -H "Accept: application/vnd.github.raw"`.
- [ ] **Step 3:** Open https://jomasii.github.io/pswatch/ in the browser pane. Confirm the live bar reads "há X s" and is not red, a link opens a store, and there are no console errors.
- [ ] **Step 4:** Update `docs/resumo-da-sessao.md` with the new panel and commit `docs: session summary with live dashboard`.
