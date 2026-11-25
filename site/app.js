const MODELS = {
  slim_disc: "PS5 Slim com leitor de disco",
  slim_digital: "PS5 Slim Digital",
};
const LIMITS = [
  { label: "Alerta (R$ 4.000)", value: 4000, color: "#e0a100" },
  { label: "Alerta máximo (R$ 3.600)", value: 3600, color: "#d92d20" },
];
const PALETTE = ["#2563eb", "#16a34a", "#9333ea", "#ea580c", "#0891b2", "#be185d", "#4b5563"];

const brl = (n) => n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const fmtTime = (ms) =>
  new Date(ms).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });

function el(tag, attrs = {}, text = "") {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
  if (text) node.textContent = text;
  return node;
}

function renderModel(container, key, stores) {
  const card = el("div", { class: "card" });
  card.appendChild(el("h2", {}, MODELS[key]));

  const names = Object.keys(stores);
  if (names.length === 0) {
    card.appendChild(el("p", { class: "muted" }, "sem dados ainda"));
    container.appendChild(card);
    return;
  }

  const table = el("table");
  const head = el("tr");
  ["Loja", "Preço atual", "Menor do período"].forEach((t, i) =>
    head.appendChild(el("th", i ? { class: "num" } : {}, t))
  );
  table.appendChild(head);
  names
    .map((n) => {
      const pts = stores[n];
      const prices = pts.map((p) => Number(p[1]));
      return { name: n, current: prices[prices.length - 1], low: Math.min(...prices) };
    })
    .sort((a, b) => a.current - b.current)
    .forEach((row) => {
      const tr = el("tr");
      tr.appendChild(el("td", {}, row.name));
      tr.appendChild(el("td", { class: "num" }, brl(row.current)));
      tr.appendChild(el("td", { class: "num" }, brl(row.low)));
      table.appendChild(tr);
    });
  card.appendChild(table);

  const canvas = el("canvas");
  card.appendChild(canvas);
  container.appendChild(card);

  const series = names.map((n, i) => ({
    label: n,
    borderColor: PALETTE[i % PALETTE.length],
    backgroundColor: PALETTE[i % PALETTE.length],
    stepped: true,
    pointRadius: 2,
    data: stores[n].map((p) => ({ x: Date.parse(p[0]), y: Number(p[1]) })),
  }));
  const allX = series.flatMap((s) => s.data.map((d) => d.x));
  const xMin = Math.min(...allX);
  const xMax = Math.max(...allX);
  LIMITS.forEach((l) =>
    series.push({
      label: l.label,
      borderColor: l.color,
      borderDash: [6, 4],
      pointRadius: 0,
      data: [{ x: xMin, y: l.value }, { x: xMax, y: l.value }],
    })
  );

  new Chart(canvas, {
    type: "line",
    data: { datasets: series },
    options: {
      parsing: false,
      scales: {
        x: { type: "linear", ticks: { callback: (v) => fmtTime(v), maxTicksLimit: 6 } },
        y: { ticks: { callback: (v) => brl(v) } },
      },
      plugins: { tooltip: { callbacks: { title: (items) => fmtTime(items[0].parsed.x) } } },
    },
  });
}

async function main() {
  const status = document.getElementById("status");
  const container = document.getElementById("models");
  let history = {};
  try {
    const res = await fetch("history.json", { cache: "no-store" });
    if (res.ok) history = await res.json();
  } catch (e) {
    /* sem dados */
  }
  const times = Object.values(history).flatMap((m) =>
    Object.values(m).flatMap((pts) => pts.map((p) => Date.parse(p[0])))
  );
  status.textContent = times.length
    ? "Última atualização: " + fmtTime(Math.max(...times)) + " (preços à vista/Pix; só mudanças são registradas)"
    : "Sem dados ainda.";
  Object.keys(MODELS).forEach((key) => renderModel(container, key, history[key] || {}));
}

main();
