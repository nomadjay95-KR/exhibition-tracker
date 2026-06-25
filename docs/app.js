"use strict";

const SOURCES = ["COEX", "SETEC", "KINTEX", "DDP"];
const SOURCE_COLORS = {
  COEX: "var(--coex)",
  SETEC: "var(--setec)",
  KINTEX: "var(--kintex)",
  DDP: "var(--ddp)",
};

const state = {
  events: [],
  search: "",
  sources: new Set(SOURCES), // 활성 출처 (전부 활성=필터 없음)
  status: "all",
  relevantOnly: false,
};

// 오늘 날짜 (YYYY-MM-DD, 로컬 기준)
function todayStr() {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}
const TODAY = todayStr();

function statusOf(ev) {
  if (ev.end_date && ev.end_date < TODAY) return "ended";
  if (ev.start_date && ev.start_date > TODAY) return "upcoming";
  return "ongoing";
}

const STATUS_LABEL = { ongoing: "진행중", upcoming: "예정", ended: "종료" };

function formatDate(start, end) {
  if (!start) return "";
  if (!end || end === start) return start.replace(/-/g, ".");
  return `${start.replace(/-/g, ".")} – ${end.replace(/-/g, ".")}`;
}

// ---------- 렌더링 ----------
function buildSourceFilters() {
  const wrap = document.getElementById("source-filters");
  SOURCES.forEach((src) => {
    const btn = document.createElement("button");
    btn.className = "chip";
    btn.dataset.source = src;
    btn.dataset.active = "true";
    btn.style.setProperty("--chip-color", SOURCE_COLORS[src]);
    btn.innerHTML = `<span class="dot"></span>${src}`;
    btn.addEventListener("click", () => {
      if (state.sources.has(src)) state.sources.delete(src);
      else state.sources.add(src);
      // 전부 비활성으로 만들면 전체 표시로 복귀
      if (state.sources.size === 0) SOURCES.forEach((s) => state.sources.add(s));
      btn.dataset.active = state.sources.has(src) ? "true" : "false";
      render();
    });
    wrap.appendChild(btn);
  });
}

function cardEl(ev) {
  const card = document.createElement("a");
  card.className = "card";
  card.href = ev.url || "#";
  if (ev.url) {
    card.target = "_blank";
    card.rel = "noopener";
  }

  const st = statusOf(ev);
  const cover = document.createElement("div");
  cover.className = "card-cover";

  if (ev.image_url) {
    const img = document.createElement("img");
    img.src = ev.image_url;
    img.alt = ev.name;
    img.loading = "lazy";
    img.addEventListener("error", () => {
      // 이미지 로드 실패 시 플레이스홀더로 대체
      cover.classList.add("placeholder");
      cover.style.setProperty("--ph-color", colorValue(ev.source));
      img.remove();
      const ph = document.createElement("span");
      ph.textContent = ev.source;
      cover.appendChild(ph);
    });
    cover.appendChild(img);
  } else {
    cover.classList.add("placeholder");
    cover.style.setProperty("--ph-color", colorValue(ev.source));
    const ph = document.createElement("span");
    ph.textContent = ev.source;
    cover.appendChild(ph);
  }

  const badge = document.createElement("span");
  badge.className = "source-badge";
  badge.style.setProperty("--badge-color", colorValue(ev.source));
  badge.textContent = ev.source;
  cover.appendChild(badge);

  const status = document.createElement("span");
  status.className = `status-badge ${st}`;
  status.textContent = STATUS_LABEL[st];
  cover.appendChild(status);

  const body = document.createElement("div");
  body.className = "card-body";
  body.innerHTML = `
    <h3 class="card-title">${escapeHtml(ev.name)}</h3>
    <div class="card-meta">
      <span class="date">${formatDate(ev.start_date, ev.end_date)}</span>
      <span class="venue">${escapeHtml(ev.venue || "")}</span>
    </div>
  `;

  card.appendChild(cover);
  card.appendChild(body);
  return card;
}

// CSS 변수(var(--coex))를 실제 색상 값으로 변환
function colorValue(source) {
  const v = getComputedStyle(document.documentElement)
    .getPropertyValue("--" + source.toLowerCase())
    .trim();
  return v || "#bcbcbc";
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function filtered() {
  const q = state.search.trim().toLowerCase();
  return state.events.filter((ev) => {
    if (!state.sources.has(ev.source)) return false;
    if (state.relevantOnly && !ev.relevant) return false;
    if (state.status !== "all" && statusOf(ev) !== state.status) return false;
    if (q) {
      const hay = (ev.name + " " + (ev.venue || "")).toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function render() {
  const list = filtered();
  const gallery = document.getElementById("gallery");
  const empty = document.getElementById("empty");
  const count = document.getElementById("result-count");

  gallery.innerHTML = "";
  count.textContent = `${list.length}개 행사`;

  if (list.length === 0) {
    empty.hidden = false;
    return;
  }
  empty.hidden = true;

  const frag = document.createDocumentFragment();
  list.forEach((ev) => frag.appendChild(cardEl(ev)));
  gallery.appendChild(frag);
}

// ---------- 이벤트 바인딩 ----------
function bindControls() {
  document.getElementById("search").addEventListener("input", (e) => {
    state.search = e.target.value;
    render();
  });

  document.querySelectorAll("#status-filters .chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.status = btn.dataset.status;
      document.querySelectorAll("#status-filters .chip").forEach((b) => {
        b.dataset.active = b === btn ? "true" : "false";
      });
      render();
    });
  });

  document.getElementById("relevant-only").addEventListener("change", (e) => {
    state.relevantOnly = e.target.checked;
    render();
  });
}

// ---------- 초기화 ----------
async function init() {
  buildSourceFilters();
  bindControls();

  try {
    const resp = await fetch("exhibitions.json", { cache: "no-cache" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    state.events = data.events || [];

    const updated = document.getElementById("updated");
    if (data.generated_at) {
      const dt = new Date(data.generated_at);
      updated.textContent = `최종 업데이트: ${dt.toLocaleString("ko-KR")} · 총 ${state.events.length}건`;
    }
  } catch (err) {
    document.getElementById("result-count").textContent =
      "데이터를 불러오지 못했습니다. (exhibitions.json 확인 필요)";
    console.error("데이터 로드 실패:", err);
    return;
  }

  render();
}

init();
