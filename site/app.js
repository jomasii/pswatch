"use strict";

const API = "https://api.github.com/repos/jomasii/pswatch/contents/";
const RAW = "https://raw.githubusercontent.com/jomasii/pswatch/data/";
const BRANCH = "data";
// Sem login o GitHub permite 60 consultas/h por IP (respostas 304 também contam):
// 75 s dá 48/h e deixa folga; perto do limite a página espera o reset.
const OFFERS_EVERY_MS = 75 * 1000;
const HISTORY_EVERY_MS = 5 * 60 * 1000;
const RATE_RESERVE = 3;
const STALE_S = 900;
const ALERT = 4000;
const MAX_ALERT = 3600;
const NEAR = 4300;

const MODELS = { slim_digital: "PS5 Slim Digital", slim_disc: "PS5 Slim com leitor" };
const SHORT = { slim_digital: "Digital", slim_disc: "Com leitor" };
const STORE_NAMES = {
  amazon: "Amazon", kabum: "KaBuM!", "magazine luiza": "Magazine Luiza", magalu: "Magalu",
  "mercado livre": "Mercado Livre", americanas: "Americanas", "casas bahia": "Casas Bahia",
  "fast shop": "Fast Shop", carrefour: "Carrefour",
};
const FILTERS = [
  { id: "all", label: "Todos", test: () => true },
  { id: "slim_digital", label: "Digital", test: (o) => o.model === "slim_digital" },
  { id: "slim_disc", label: "Com leitor", test: (o) => o.model === "slim_disc" },
  { id: "nocombo", label: "Sem combos", test: (o) => !o.bundle },
];
const PALETTE = ["#58a6ff", "#3fb950", "#bc8cff", "#f0883e", "#39c5cf", "#ff7b72", "#8b949e"];

const state = { offers: null, history: {}, slow: false, filter: "all", etags: {}, charts: [], views: {}, apiPausedUntil: 0 };

// ---------- helpers puros ----------
const brl = (n) => Number(n).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const storeName = (s) => STORE_NAMES[s] || s;

function fmtWhen(iso) {
  const d = new Date(iso);
  const today = new Date();
  const time = d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  if (d.toDateString() === today.toDateString()) return time;
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) + " " + time;
}

function fmtAgo(seconds) {
  const s = Math.max(0, Math.round(seconds));
  if (s < 60) return `há ${s} s`;
  const m = Math.round(s / 60);
  if (m < 60) return `há ${m} min`;
  const h = Math.floor(m / 60);
  return `há ${h} h ${m % 60} min`;
}

function fmtDuration(ms) {
  const m = Math.round(ms / 60000);
  if (m < 60) return `~${Math.max(m, 1)} min`;
  const h = Math.round(m / 60);
  if (h < 48) return `~${h} h`;
  return `~${Math.round(h / 24)} dias`;
}

function safeUrl(u) {
  return typeof u === "string" && u.startsWith("https://") ? u : null;
}

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

function linkEl(url, text, cls) {
  const safe = safeUrl(url);
  if (!safe) return el("span", "muted", "—");
  const a = el("a", cls, text);
  a.href = safe;
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  return a;
}

// Junta pontos seguidos com o mesmo preço (por modelo e loja) em "episódios".
function episodes(history) {
  const out = [];
  for (const [model, stores] of Object.entries(history || {})) {
    if (!MODELS[model]) continue;
    for (const [store, points] of Object.entries(stores)) {
      if (!STORE_NAMES[store]) continue; // só lojas aceitas (mesma lista do alerta)
      let cur = null;
      for (const p of points) {
        const price = Number(p[1]);
        if (cur && cur.price === price) {
          if (!cur.url && p[2]) cur.url = p[2];
          cur.lastSeen = p[0];
          continue;
        }
        if (cur) cur.end = p[0];
        cur = { model, store, price, url: p[2] || null, start: p[0], end: null, lastSeen: p[0] };
        out.push(cur);
      }
    }
  }
  return out;
}

// Um item por modelo+loja+preço: quantas vezes apareceu, tempo total no ar e a vez mais recente.
// "Ainda no ar" só vale se a oferta estiver no offers.json de agora; uma loja que parou de
// aparecer (ex.: Mercado Livre pausado) conta até o último ponto registrado.
function lows(history, offers, now = Date.now()) {
  const current = new Map();
  for (const o of offers || []) current.set(`${o.model}|${o.store}|${Number(o.price)}`, o);
  const groups = new Map();
  for (const e of episodes(history)) {
    const key = `${e.model}|${e.store}|${e.price}`;
    const g = groups.get(key) || { model: e.model, store: e.store, price: e.price, times: 0, totalMs: 0, last: e.start, live: false, url: null };
    const live = e.end === null && current.has(key);
    const end = e.end ? Date.parse(e.end) : live ? now : Date.parse(e.lastSeen);
    g.times += 1;
    g.totalMs += end - Date.parse(e.start);
    if (e.start >= g.last) { g.last = e.start; g.live = live; }
    if (e.url) g.url = e.url;
    groups.set(key, g);
  }
  for (const [key, o] of current) {
    const g = groups.get(key);
    if (g && g.live) g.url = o.url;
  }
  return [...groups.values()].sort((a, b) => a.price - b.price || b.last.localeCompare(a.last)).slice(0, 10);
}

function heroFor(model, offers) {
  const mine = offers.filter((o) => o.model === model);
  if (!mine.length) return null;
  const best = mine.reduce((a, b) => (Number(b.price) < Number(a.price) ? b : a));
  const price = Number(best.price);
  let level = "";
  let gap = `Faltam ${brl(price - ALERT)} para o alerta de R$ 4.000`;
  if (price < MAX_ALERT) { level = "hit"; gap = "🚨 ALERTA MÁXIMO — abaixo de R$ 3.600"; }
  else if (price < ALERT) { level = "hit"; gap = "🔔 Abaixo do alerta de R$ 4.000!"; }
  else if (price <= NEAR) { level = "near"; gap = "⚠️ " + gap; }
  return { offer: best, level, gap };
}

// ---------- busca ----------
// Em teste local (localhost) lê só os arquivos da própria pasta.
const LOCAL = ["localhost", "127.0.0.1"].includes(location.hostname);

function noteRateLimit(res) {
  const remaining = Number(res.headers.get("X-RateLimit-Remaining"));
  const reset = Number(res.headers.get("X-RateLimit-Reset"));
  if (res.headers.get("X-RateLimit-Remaining") !== null && remaining <= RATE_RESERVE && reset) {
    state.apiPausedUntil = reset * 1000;
  }
}

async function fetchApi(name) {
  const headers = { Accept: "application/vnd.github.raw" };
  const cached = state.etags[name];
  if (cached) headers["If-None-Match"] = cached.etag;
  const res = await fetch(`${API}${name}?ref=${BRANCH}`, { headers, cache: "no-store" });
  noteRateLimit(res);
  if (res.status === 304 && cached) return cached.body;
  if (res.status === 404) return null;
  if (res.status === 403 || res.status === 429) {
    state.apiPausedUntil = Math.max(state.apiPausedUntil, Date.now() + 10 * 60 * 1000);
  }
  if (!res.ok) throw new Error(`API ${res.status}`);
  const body = await res.json();
  const etag = res.headers.get("ETag");
  if (etag) state.etags[name] = { etag, body };
  return body;
}

async function fetchPlain(url) {
  const res = await fetch(`${url}?t=${Date.now()}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// offers.json: API (quase ao vivo) → raw.githubusercontent (até ~5 min).
// history.json não precisa ser ao vivo: vai direto pelo raw, sem gastar consultas da API.
// O Pages publica só a página (index.html, app.js); os dados ficam no ramo data.
async function fetchJson(name, { live = false } = {}) {
  if (LOCAL) {
    try { return await fetchPlain(name); } catch (e) { return null; }
  }
  if (live && Date.now() >= state.apiPausedUntil) {
    try {
      const body = await fetchApi(name);
      state.slow = false;
      return body;
    } catch (e) { /* cai para as cópias */ }
  }
  if (live) state.slow = true;
  try { return await fetchPlain(RAW + name); } catch (e) { return null; }
}

// ---------- desenho ----------
function renderLive() {
  const box = document.getElementById("live");
  const text = document.getElementById("live-text");
  const checked = state.offers && state.offers.checked_at;
  if (!checked) {
    box.className = "stale";
    text.textContent = "Sem dados do vigia ainda";
    return;
  }
  const age = (Date.now() - Date.parse(checked)) / 1000;
  const slow = state.slow ? " · modo lento (limite do GitHub; pode atrasar até ~5 min)" : "";
  if (age > STALE_S) {
    box.className = "stale";
    text.textContent = `Vigia parado? Última checagem ${fmtAgo(age)}${slow}`;
  } else {
    box.className = "";
    text.textContent = `Ao vivo · última checagem ${fmtAgo(age)}${slow}`;
  }
}

function renderHeroes(offers) {
  const box = document.getElementById("heroes");
  box.replaceChildren();
  for (const model of Object.keys(MODELS)) {
    const h = heroFor(model, offers);
    const card = el("div", "hero" + (h && h.level ? " " + h.level : ""));
    card.append(el("div", "model", `${MODELS[model]} · menor agora`));
    if (!h) {
      card.append(el("div", "price", "—"), el("div", "store", "Nenhuma oferta no ar agora"));
    } else {
      const o = h.offer;
      const store = el("div", "store", `${storeName(o.store)} · à vista/Pix`);
      if (o.bundle) store.append(el("span", "tag combo", "combo"));
      if (o.promo) store.append(el("span", "tag promo", "cupom"));
      card.append(el("div", "price", brl(o.price)), store, el("div", "gap", h.gap), linkEl(o.url, "Abrir oferta →", "btn"));
    }
    box.append(card);
  }
}

function renderFilters() {
  const box = document.getElementById("filters");
  box.replaceChildren();
  for (const f of FILTERS) {
    const b = el("button", "chip" + (state.filter === f.id ? " on" : ""), f.label);
    b.type = "button";
    b.addEventListener("click", () => { state.filter = f.id; renderFilters(); renderNow(); });
    box.append(b);
  }
}

function table(headers) {
  const t = el("table");
  const tr = el("tr");
  headers.forEach(([label, cls]) => tr.append(el("th", cls || "", label)));
  t.append(tr);
  return t;
}

function renderNow() {
  const box = document.getElementById("now");
  const offers = (state.offers && state.offers.offers) || [];
  const test = FILTERS.find((f) => f.id === state.filter).test;
  const rows = offers.filter(test);
  box.replaceChildren();
  if (!rows.length) { box.append(el("div", "empty", "Nenhuma oferta no ar com esse filtro.")); return; }
  const t = table([["#"], ["Modelo"], ["Loja"], ["Pix", "num"], ["No ar desde"], ["Anúncio"], [""]]);
  rows.forEach((o, i) => {
    const tr = el("tr");
    const store = el("td", "", storeName(o.store));
    if (o.bundle) store.append(el("span", "tag combo", "combo"));
    if (o.promo) {
      const tag = el("span", "tag promo", "cupom");
      tag.title = o.promo;
      store.append(tag);
    }
    const linkTd = el("td");
    linkTd.append(linkEl(o.url, "Abrir →", "link"));
    tr.append(
      el("td", "rank", String(i + 1)), el("td", "", SHORT[o.model] || o.model), store,
      el("td", "num", brl(o.price)), el("td", "", o.since ? fmtWhen(o.since) : "—"),
      el("td", "title", o.promo ? `${o.title} · ${o.promo}` : o.title || ""), linkTd,
    );
    t.append(tr);
  });
  box.append(t);
}

function renderLows() {
  const box = document.getElementById("lows");
  const list = lows(state.history, state.offers && state.offers.offers);
  box.replaceChildren();
  if (!list.length) { box.append(el("div", "empty", "Sem histórico ainda.")); return; }
  const t = table([["#"], ["Modelo"], ["Loja"], ["Pix", "num"], ["Última vez"], ["Tempo no ar"], [""]]);
  list.forEach((g, i) => {
    const tr = el("tr");
    const linkTd = el("td");
    linkTd.append(g.url ? linkEl(g.url, "Abrir →", g.live ? "link" : "link old") : el("span", "muted", "sem link"));
    const times = g.times > 1 ? ` (${g.times} vezes)` : "";
    tr.append(
      el("td", "rank", String(i + 1)), el("td", "", SHORT[g.model]), el("td", "", storeName(g.store)),
      el("td", "num", brl(g.price)), el("td", "", fmtWhen(g.last)),
      el("td", g.live ? "" : "muted", (g.live ? "ainda no ar · " : "") + fmtDuration(g.totalMs) + times),
      linkTd,
    );
    t.append(tr);
  });
  box.append(t);
}

// ---------- gráficos: zoom e rolagem ----------
// O gráfico é recriado a cada 5 min (histórico novo); o recorte escolhido fica em state.views.
const MIN_RANGE_MS = 30 * 60 * 1000;
const DAY_MS = 24 * 3600 * 1000;

// Com zoom, o eixo do preço se ajusta só ao que está visível (linhas em degrau:
// conta também o último ponto antes da janela). Sem zoom, volta ao automático.
function fitY(chart) {
  const y = chart.options.scales.y;
  if (!chart.isZoomedOrPanned()) { delete y.min; delete y.max; chart.update("none"); return; }
  const { min, max } = chart.scales.x;
  const vals = [];
  for (const ds of chart.data.datasets) {
    if (ds.threshold) continue;
    let before = null;
    for (const p of ds.data) {
      if (p.x < min) before = p.y;
      else if (p.x <= max) vals.push(p.y);
    }
    if (before !== null) vals.push(before);
  }
  if (!vals.length) return;
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const pad = Math.max((hi - lo) * 0.08, 50);
  y.min = Math.floor((lo - pad) / 50) * 50;
  y.max = Math.ceil((hi + pad) / 50) * 50;
  chart.update("none");
}

function afterMove(model, chart) {
  fitY(chart);
  state.views[model] = chart.isZoomedOrPanned() ? { min: chart.scales.x.min, max: chart.scales.x.max } : null;
}

function chartTools(model, chart, xMax) {
  const bar = el("div", "chart-tools");
  const btn = (text, title, fn) => {
    const b = el("button", "", text);
    b.type = "button"; b.title = title;
    b.addEventListener("click", () => { fn(); afterMove(model, chart); });
    bar.append(b);
  };
  btn("◀", "Voltar no tempo", () => chart.pan({ x: chart.chartArea.width * 0.4 }, undefined, "none"));
  btn("−", "Afastar (zoom out)", () => chart.zoom({ x: 1 / 1.5 }, "none"));
  btn("+", "Aproximar (zoom in)", () => chart.zoom({ x: 1.5 }, "none"));
  btn("▶", "Avançar no tempo", () => chart.pan({ x: -chart.chartArea.width * 0.4 }, undefined, "none"));
  btn("24h", "Últimas 24 horas", () => chart.zoomScale("x", { min: xMax - DAY_MS, max: xMax }, "none"));
  btn("Tudo", "Ver todo o período", () => chart.resetZoom("none"));
  return bar;
}

function renderCharts() {
  const box = document.getElementById("charts");
  state.charts.forEach((c) => c.destroy());
  state.charts = [];
  box.replaceChildren();
  if (typeof Chart === "undefined") return;
  const zoomOk = !!Chart.registry.plugins.get("zoom");
  const css = getComputedStyle(document.documentElement);
  const muted = css.getPropertyValue("--muted").trim();
  const grid = css.getPropertyValue("--line-soft").trim();
  for (const model of Object.keys(MODELS)) {
    const stores = (state.history || {})[model] || {};
    const card = el("div", "chart-card");
    const head = el("div", "chart-head");
    head.append(el("h3", "", MODELS[model]));
    card.append(head);
    const holder = el("div", "chart-box");
    const canvas = el("canvas");
    holder.append(canvas);
    card.append(holder);
    box.append(card);
    const names = Object.keys(stores);
    if (!names.length) { holder.replaceChildren(el("div", "empty", "Sem dados ainda.")); continue; }
    const series = names.map((n, i) => ({
      label: storeName(n), borderColor: PALETTE[i % PALETTE.length], backgroundColor: PALETTE[i % PALETTE.length],
      stepped: true, pointRadius: 0, borderWidth: 2,
      data: stores[n].map((p) => ({ x: Date.parse(p[0]), y: Number(p[1]) })).concat(
        stores[n].length ? [{ x: Date.now(), y: Number(stores[n][stores[n].length - 1][1]) }] : []),
    }));
    const xs = series.flatMap((s) => s.data.map((d) => d.x));
    const [xMin, xMax] = [Math.min(...xs), Math.max(...xs)];
    [[ALERT, "#d29922", "Alerta R$ 4.000"], [MAX_ALERT, "#f85149", "Máximo R$ 3.600"]].forEach(([v, c, l]) =>
      series.push({ label: l, borderColor: c, borderDash: [6, 4], pointRadius: 0, borderWidth: 1.5, threshold: true,
        data: [{ x: xMin, y: v }, { x: xMax, y: v }] }));
    const done = ({ chart }) => afterMove(model, chart);
    const chart = new Chart(canvas, {
      type: "line",
      data: { datasets: series },
      options: {
        parsing: false, maintainAspectRatio: false, animation: false,
        interaction: { mode: "nearest", intersect: false },
        scales: {
          x: { type: "linear", ticks: { color: muted, maxTicksLimit: 6, callback: (v) => fmtWhen(new Date(v).toISOString()) }, grid: { color: grid } },
          y: { ticks: { color: muted, callback: (v) => brl(v) }, grid: { color: grid } },
        },
        plugins: {
          legend: { labels: { color: muted, boxWidth: 12 } },
          tooltip: { callbacks: {
            title: (items) => fmtWhen(new Date(items[0].parsed.x).toISOString()),
            label: (item) => `${item.dataset.label}: ${brl(item.parsed.y)}`,
          } },
          zoom: {
            limits: { x: { min: "original", max: "original", minRange: MIN_RANGE_MS } },
            pan: { enabled: true, mode: "x", onPanComplete: done },
            zoom: { mode: "x", onZoomComplete: done, wheel: { enabled: true, modifierKey: "ctrl" }, pinch: { enabled: true } },
          },
        },
      },
    });
    state.charts.push(chart);
    if (!zoomOk) continue;
    head.append(chartTools(model, chart, xMax));
    canvas.addEventListener("dblclick", () => { chart.resetZoom("none"); afterMove(model, chart); });
    const view = state.views[model];
    if (view) { chart.zoomScale("x", view, "none"); fitY(chart); }
    card.append(el("p", "chart-hint", "Arraste para os lados para rolar · Ctrl + roda do mouse (ou pinça) para zoom · duplo clique mostra tudo"));
  }
}

function renderOffers() {
  const offers = (state.offers && state.offers.offers) || [];
  renderHeroes(offers);
  renderNow();
  renderLows();
  renderLive();
}

// ---------- laço ----------
async function refreshOffers() {
  const doc = await fetchJson("offers.json", { live: true });
  if (doc && Array.isArray(doc.offers)) state.offers = doc;
  renderOffers();
}

async function refreshHistory() {
  const doc = await fetchJson("history.json");
  if (doc && typeof doc === "object") state.history = doc;
  renderLows();
  renderCharts();
}

function start() {
  renderFilters();
  refreshOffers();
  refreshHistory();
  setInterval(refreshOffers, OFFERS_EVERY_MS);
  setInterval(refreshHistory, HISTORY_EVERY_MS);
  setInterval(renderLive, 1000);
}

start();
