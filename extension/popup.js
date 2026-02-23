import { fetchWorksheets, fetchCoursesForSeason, makeWorksheetKey, getAllCoursesBySeasons, getUserData } from "./utils.js"

const worksheetSelect = document.getElementById("worksheetSelect");
const statusEl = document.getElementById("status");
const coursesEl = document.getElementById("courses");
const metaEl = document.getElementById("meta");

function setStatus(msg, isError = false) {
  statusEl.textContent = msg;
  statusEl.className = "status" + (isError ? " error" : "");
}

function setCoursesHtml(html) {
  coursesEl.innerHTML = html;
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (m) => {
    switch (m) {
      case "&": return "&amp;";
      case "<": return "&lt;";
      case ">": return "&gt;";
      case '"': return "&quot;";
      case "'": return "&#039;";
      default: return m;
    }
  });
}

function renderWorksheetDropdown(worksheets) {
  worksheetSelect.innerHTML = "";
  for (const ws of worksheets) {
    const opt = document.createElement("option");
    opt.value = makeWorksheetKey(ws.season, ws.worksheetNumber);
    opt.textContent = `${ws.season} — #${ws.worksheetNumber}: ${ws.name}`;
    worksheetSelect.appendChild(opt);
  }
  worksheetSelect.disabled = worksheets.length === 0;
}

function renderWorksheetCourses(ws, seasonMaps) {
  const crnMap = seasonMaps.get(ws.season) || new Map();

  if (!ws.courses.length) {
    setCoursesHtml("—");
    return;
  }

  const items = ws.courses.map((entry) => {
    if (entry.hidden === false) {
      const crn = entry?.crn;
      const hidden = entry?.hidden;
      const found = typeof crn === "number" ? crnMap.get(crn) : null;

      const title = found?.title || `Unknown course (CRN ${crn})`;
      const code = found?.course_code ? `${found.course_code}` : "";
      const sec = found?.section ? `S${found.section}` : "";

      const badges = [];
      if (code) badges.push(`<span class="pill">${escapeHtml(code)}${sec ? " " + escapeHtml(sec) : ""}</span>`);
      if (hidden === true) badges.push(`<span class="pill">hidden</span>`);
      if (hidden === null) badges.push(`<span class="pill">hidden:null</span>`);

      return `<li>${escapeHtml(title)} ${badges.join(" ")}</li>`;
    } else {
      return "";
    }
  });

  setCoursesHtml(`<ul>${items.join("")}</ul>`);
}

async function init() {
  try {
    const userData = await getUserData();
    console.log(userData);
    setStatus("Fetching worksheets…");

    const { seasons, worksheets } = await fetchWorksheets();

    if (worksheets.length === 0) {
      renderWorksheetDropdown([]);
      setCoursesHtml("—");
      setStatus("No worksheets found. Are you logged in?", true);
      return;
    }

    setStatus(`Found ${worksheets.length} worksheet(s) across ${seasons.length} season(s).\nFetching courses for each season…`);

    // Fetch all seasons in parallel (one GraphQL request per season)
    const seasonMaps = await getAllCoursesBySeasons(seasons);

    renderWorksheetDropdown(worksheets);
    worksheetSelect.disabled = false;

    // Default: first worksheet
    const currentKey = worksheetSelect.value;
    const current = worksheets.find((w) => makeWorksheetKey(w.season, w.worksheetNumber) === currentKey);
    if (current) renderWorksheetCourses(current, seasonMaps);

    setStatus("Ready.");

    worksheetSelect.addEventListener("change", () => {
      const key = worksheetSelect.value;
      const ws = worksheets.find((w) => makeWorksheetKey(w.season, w.worksheetNumber) === key);
      if (ws) renderWorksheetCourses(ws, seasonMaps);
    });
  } catch (err) {
    console.error(err);
    renderWorksheetDropdown([]);
    setCoursesHtml("—");
    setStatus(err?.message || String(err), true);
  }
}

document.addEventListener("DOMContentLoaded", init);
