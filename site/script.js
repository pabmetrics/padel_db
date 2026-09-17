const fmt = new Intl.NumberFormat("es-ES");

async function getJSON(path) {
  const res = await fetch(path);
  if (!res.ok) return [];
  return res.json();
}

function empty(msg) {
  const div = document.createElement("div");
  div.className = "empty";
  div.textContent = msg;
  return div;
}

function table(headers, rows) {
  const wrap = document.createElement("div");
  wrap.className = "table-wrap-inner";
  const t = document.createElement("table");

  const thead = document.createElement("thead");
  const trh = document.createElement("tr");
  headers.forEach((h) => {
    const th = document.createElement("th");
    th.textContent = h.label;
    if (h.num) th.className = "num";
    trh.appendChild(th);
  });
  thead.appendChild(trh);
  t.appendChild(thead);

  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    row.forEach((cell) => tr.appendChild(cell));
    tbody.appendChild(tr);
  });
  t.appendChild(tbody);
  wrap.appendChild(t);
  return wrap;
}

function td(text, opts = {}) {
  const el = document.createElement("td");
  el.textContent = text;
  if (opts.num) el.classList.add("num");
  if (opts.cls) el.classList.add(opts.cls);
  return el;
}

function delta(value) {
  if (value === null || value === undefined) return td("—", { num: true });
  const signo = value > 0 ? "+" : "";
  return td(`${signo}${value}`, { num: true, cls: value > 0 ? "up" : value < 0 ? "down" : "" });
}

async function renderRanking() {
  const data = await getJSON("data/ranking_movimientos_semana.json");
  ["M", "F"].forEach((sexo) => {
    const target = document.getElementById(sexo === "M" ? "ranking-m" : "ranking-f");
    const filas = data
      .filter((r) => r.sexo === sexo && r.publicable)
      .sort((a, b) => Math.abs(b.posicion_diff_semana) - Math.abs(a.posicion_diff_semana))
      .slice(0, 20);
    if (!filas.length) {
      target.appendChild(empty("Sin movimientos publicables todavía."));
      return;
    }
    const rows = filas.map((r) => [
      td(r.jugador_nombre),
      td(String(r.posicion), { num: true }),
      delta(r.posicion_diff_semana),
      td(fmt.format(r.puntos), { num: true }),
      delta(r.puntos_diff_semana),
    ]);
    target.appendChild(
      table(
        [
          { label: "Jugador" },
          { label: "Pos.", num: true },
          { label: "Δ puestos", num: true },
          { label: "Puntos", num: true },
          { label: "Δ puntos", num: true },
        ],
        rows
      )
    );
  });
}

async function renderForma() {
  const data = await getJSON("data/forma_reciente.json");
  ["M", "F"].forEach((sexo) => {
    const target = document.getElementById(sexo === "M" ? "forma-m" : "forma-f");
    const filas = data
      .filter((r) => r.sexo === sexo && r.publicable)
      .sort((a, b) => b.pct_victorias_8sem - a.pct_victorias_8sem || b.partidos_8sem - a.partidos_8sem)
      .slice(0, 20);
    if (!filas.length) {
      target.appendChild(empty("Sin datos todavía."));
      return;
    }
    const rows = filas.map((r) => [
      td(r.jugador_nombre),
      td(String(r.partidos_8sem), { num: true }),
      td(String(r.victorias_8sem), { num: true }),
      td(`${r.pct_victorias_8sem}%`, { num: true }),
      td(`${r.racha_n} ${r.racha_tipo}`, { cls: r.racha_tipo === "victorias" ? "up" : "down" }),
    ]);
    target.appendChild(
      table(
        [
          { label: "Jugador" },
          { label: "Partidos", num: true },
          { label: "Victorias", num: true },
          { label: "% Victorias", num: true },
          { label: "Racha" },
        ],
        rows
      )
    );
  });
}

async function renderPerfil() {
  const data = await getJSON("data/perfil_top100.json");
  const resumen = document.getElementById("perfil-resumen");

  ["M", "F"].forEach((sexo) => {
    const filas = data.filter((r) => r.sexo === sexo).sort((a, b) => a.ranking - b.ranking);
    const target = document.getElementById(sexo === "M" ? "perfil-m" : "perfil-f");
    if (!filas.length) {
      target.appendChild(empty("Sin datos todavía."));
      return;
    }

    const edades = filas.map((r) => r.edad).filter((e) => e !== null);
    const media = edades.length ? (edades.reduce((a, b) => a + b, 0) / edades.length).toFixed(1) : "—";
    const card = document.createElement("div");
    card.className = "stat-card";
    card.innerHTML = `<div class="value">${media}</div><div class="label">Edad media top 100 ${sexo === "M" ? "masculino" : "femenino"}</div>`;
    resumen.appendChild(card);

    const rows = filas.map((r) => [
      td(String(r.ranking), { num: true }),
      td(r.jugador_nombre),
      td(r.nacionalidad || "—"),
      td(r.edad !== null ? String(r.edad) : "—", { num: true }),
      td(r.altura_cm ? `${r.altura_cm} cm` : "—", { num: true }),
      td(r.lado_pista === "drive" ? "Drive" : r.lado_pista === "backhand" ? "Revés" : "—"),
    ]);
    target.appendChild(
      table(
        [
          { label: "#", num: true },
          { label: "Jugador" },
          { label: "País" },
          { label: "Edad", num: true },
          { label: "Altura", num: true },
          { label: "Lado" },
        ],
        rows
      )
    );
  });
}

function setupTabs() {
  document.querySelectorAll(".table-tabs").forEach((tabGroup) => {
    const buttons = tabGroup.querySelectorAll(".tab-btn");
    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        buttons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const section = tabGroup.closest("section");
        section.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
        document.getElementById(btn.dataset.target).classList.add("active");
      });
    });
  });
}

setupTabs();
renderRanking();
renderForma();
renderPerfil();
