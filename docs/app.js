"use strict";

const SOURCES = ["COEX", "SETEC", "KINTEX", "DDP"];
const SOURCE_COLORS = {
  COEX: "var(--coex)",
  SETEC: "var(--setec)",
  KINTEX: "var(--kintex)",
  DDP: "var(--ddp)",
};

const _now = new Date();
const state = {
  events: [],
  search: "",
  sources: new Set(SOURCES), // 활성 출처 (전부 활성=필터 없음)
  status: "all",
  relevantOnly: true, // 기본: 관련 주제만 표시 (스위치로 전체 ↔ 관련 토글)
  view: "gallery", // "gallery" | "calendar"
  cal: { year: _now.getFullYear(), month: _now.getMonth() }, // month: 0-11
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

// 표시 순서: 진행중 → 예정 → 종료.
// 그룹 내부 — 진행중: 곧 끝나는 순, 예정: 곧 시작하는 순, 종료: 최근 종료 순.
const STATUS_RANK = { ongoing: 0, upcoming: 1, ended: 2 };

function compareEvents(a, b) {
  const ra = STATUS_RANK[statusOf(a)];
  const rb = STATUS_RANK[statusOf(b)];
  if (ra !== rb) return ra - rb;
  if (ra === 0) return (a.end_date || "").localeCompare(b.end_date || "");
  if (ra === 1) return (a.start_date || "").localeCompare(b.start_date || "");
  return (b.end_date || "").localeCompare(a.end_date || "");
}

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
  if (ev.url) {
    card.href = ev.url; // 평클릭은 모달, ⌘/Ctrl+클릭은 href로 새 탭
  } else {
    // URL이 없으면 링크 비활성 (클릭 시 맨 위로 튀는 것 방지)
    card.classList.add("no-link");
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
      img.remove();
      fillPlaceholder(cover, ev.source);
    });
    cover.appendChild(img);
  } else {
    fillPlaceholder(cover, ev.source);
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
  attachModalOpener(card, ev);
  return card;
}

// 클릭 시 요약 모달을 띄운다. ⌘/Ctrl/중간 클릭은 기존처럼 새 탭 직접 열기 허용.
function attachModalOpener(el, ev) {
  el.addEventListener("click", (e) => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) return;
    e.preventDefault();
    openModal(ev);
  });
}

// 이미지가 없거나 로드 실패한 카드를 절제된 아이콘 플레이스홀더로 채운다.
// 출처는 좌측 상단 배지로 이미 구분되므로 출처명을 크게 반복하지 않는다.
const PLACEHOLDER_ICON =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
  '<rect x="3" y="3" width="18" height="18" rx="2"/>' +
  '<circle cx="8.5" cy="8.5" r="1.6"/>' +
  '<path d="M21 15l-5-5L5 21"/></svg>';

function fillPlaceholder(cover, source) {
  cover.classList.add("placeholder");
  cover.style.setProperty("--ph-color", colorValue(source));
  const icon = document.createElement("div");
  icon.className = "ph-icon";
  icon.innerHTML = PLACEHOLDER_ICON;
  cover.appendChild(icon);
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
  document.getElementById("result-count").textContent = `${list.length}개 행사`;

  const gallery = document.getElementById("gallery");
  const empty = document.getElementById("empty");
  const calendar = document.getElementById("calendar");

  if (state.view === "calendar") {
    gallery.hidden = true;
    empty.hidden = true;
    calendar.hidden = false;
    renderCalendar(list);
  } else {
    calendar.hidden = true;
    gallery.hidden = false;
    renderGallery(list);
  }
}

function renderGallery(list) {
  const gallery = document.getElementById("gallery");
  const empty = document.getElementById("empty");
  gallery.innerHTML = "";
  if (list.length === 0) {
    empty.hidden = false;
    return;
  }
  empty.hidden = true;
  const frag = document.createDocumentFragment();
  list.forEach((ev) => frag.appendChild(cardEl(ev)));
  gallery.appendChild(frag);
}

// ---------- 캘린더 ----------
function pad2(n) {
  return String(n).padStart(2, "0");
}

function shiftMonth(delta) {
  let { year, month } = state.cal;
  month += delta;
  if (month < 0) { month = 11; year -= 1; }
  if (month > 11) { month = 0; year += 1; }
  state.cal = { year, month };
  render();
}

function renderCalendar(list) {
  const { year, month } = state.cal;
  document.getElementById("cal-label").textContent = `${year}년 ${month + 1}월`;

  const grid = document.getElementById("cal-grid");
  grid.innerHTML = "";

  const startWeekday = new Date(year, month, 1).getDay(); // 0=일
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const cells = [];
  for (let i = 0; i < startWeekday; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);

  const MAX_PER_DAY = 3;
  const frag = document.createDocumentFragment();

  cells.forEach((d) => {
    const cell = document.createElement("div");
    cell.className = "cal-cell";
    if (d === null) {
      cell.classList.add("empty");
      frag.appendChild(cell);
      return;
    }
    const dateStr = `${year}-${pad2(month + 1)}-${pad2(d)}`;
    if (dateStr === TODAY) cell.classList.add("today");

    const dayNum = document.createElement("div");
    dayNum.className = "cal-day";
    dayNum.textContent = d;
    cell.appendChild(dayNum);

    // 해당 날짜에 진행 중인 행사 (start <= date <= end)
    const dayEvents = list.filter(
      (e) => e.start_date <= dateStr && dateStr <= e.end_date
    );
    dayEvents.slice(0, MAX_PER_DAY).forEach((e) => {
      const chip = document.createElement(e.url ? "a" : "div");
      chip.className = "cal-event";
      chip.style.setProperty("--ev-color", colorValue(e.source));
      chip.textContent = e.name;
      chip.title = `[${e.source}] ${e.name}`;
      if (e.url) {
        chip.href = e.url;
      }
      attachModalOpener(chip, e);
      cell.appendChild(chip);
    });
    if (dayEvents.length > MAX_PER_DAY) {
      const more = document.createElement("div");
      more.className = "cal-more";
      more.textContent = `+${dayEvents.length - MAX_PER_DAY}개`;
      cell.appendChild(more);
    }
    frag.appendChild(cell);
  });

  grid.appendChild(frag);
}

// ---------- 행사 요약 모달 ----------
function openModal(ev) {
  const cover = document.getElementById("modal-cover");
  cover.className = "modal-cover";
  cover.innerHTML = "";
  cover.style.removeProperty("--ph-color");
  if (ev.image_url) {
    const img = document.createElement("img");
    img.src = ev.image_url;
    img.alt = ev.name;
    img.addEventListener("error", () => {
      img.remove();
      fillPlaceholder(cover, ev.source);
    });
    cover.appendChild(img);
  } else {
    fillPlaceholder(cover, ev.source);
  }

  const st = statusOf(ev);
  const badges = document.getElementById("modal-badges");
  badges.innerHTML = "";
  const src = document.createElement("span");
  src.className = "m-badge";
  src.style.background = colorValue(ev.source);
  src.textContent = ev.source;
  const status = document.createElement("span");
  status.className = "m-badge m-badge--status";
  status.textContent = STATUS_LABEL[st];
  badges.append(src, status);

  document.getElementById("modal-title").textContent = ev.name;
  document.getElementById("modal-meta").innerHTML =
    `<div><dt>기간</dt><dd>${escapeHtml(formatDate(ev.start_date, ev.end_date))}</dd></div>` +
    `<div><dt>장소</dt><dd>${escapeHtml(ev.venue || "-")}</dd></div>` +
    `<div><dt>출처</dt><dd>${escapeHtml(ev.source)}</dd></div>`;

  const cta = document.getElementById("modal-cta");
  if (ev.url) {
    cta.href = ev.url;
    cta.hidden = false;
  } else {
    cta.hidden = true;
  }

  document.getElementById("modal").hidden = false;
  document.body.style.overflow = "hidden";
}

function closeModal() {
  document.getElementById("modal").hidden = true;
  document.body.style.overflow = "";
}

function setupModal() {
  const overlay = document.getElementById("modal");
  document.getElementById("modal-close").addEventListener("click", closeModal);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !overlay.hidden) closeModal();
  });
}

// ---------- 다크모드 ----------
function setupTheme() {
  const btn = document.getElementById("theme-toggle");
  const isDark = () =>
    document.documentElement.getAttribute("data-theme") === "dark";
  const apply = (dark) => {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    btn.textContent = dark ? "☀️" : "🌙"; // 현재 다크면 해(밝게 전환), 라이트면 달
    btn.setAttribute("aria-label", dark ? "라이트모드 전환" : "다크모드 전환");
  };
  apply(isDark());
  btn.addEventListener("click", () => {
    const next = !isDark();
    apply(next);
    try {
      localStorage.setItem("theme", next ? "dark" : "light");
    } catch (e) {}
  });
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

  // 뷰 전환 (갤러리 / 캘린더)
  document.querySelectorAll(".view-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.view = btn.dataset.view;
      document.querySelectorAll(".view-btn").forEach((b) => {
        b.dataset.active = b === btn ? "true" : "false";
      });
      render();
    });
  });

  // 월 네비게이션
  document.getElementById("cal-prev").addEventListener("click", () => shiftMonth(-1));
  document.getElementById("cal-next").addEventListener("click", () => shiftMonth(1));
  document.getElementById("cal-today").addEventListener("click", () => {
    const now = new Date();
    state.cal = { year: now.getFullYear(), month: now.getMonth() };
    render();
  });
}

// ---------- 초기화 ----------
async function init() {
  setupTheme();
  setupModal();
  buildSourceFilters();
  bindControls();

  try {
    const resp = await fetch("exhibitions.json", { cache: "no-cache" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    state.events = (data.events || []).slice().sort(compareEvents);

    const updated = document.getElementById("updated");
    if (data.generated_at) {
      const dt = new Date(data.generated_at);
      const ampm = dt.getHours() < 12 ? "오전" : "오후";
      const h12 = dt.getHours() % 12 || 12;
      updated.textContent =
        `✨ ${dt.getMonth() + 1}월 ${dt.getDate()}일 ${ampm} ${h12}시 자로 업데이트됐어요!`;
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
