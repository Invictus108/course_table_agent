import { fetchWorksheets, fetchCoursesForSeason, makeWorksheetKey, getAllCoursesBySeasons, getUserData, removeCourses, addCourses } from "./utils.js"

const API_ROUTE = "http://127.0.0.1:5001"

const worksheetSelect = document.getElementById("worksheetSelect");
const statusEl = document.getElementById("status");
const coursesEl = document.getElementById("courses");
const promptEl = document.getElementById("prompt");
const submitButton = document.getElementById("submit");
const messagesEl = document.getElementById("messages");

let userData = null;
let chat = []

let courseCache = [];
let crns = []
let season = null;
let worksheetNumber = null;


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

  courseCache = [];
  crns = []

  const items = ws.courses.map((entry) => {
    if (entry.hidden === false) {
      const crn = entry?.crn;
      const hidden = entry?.hidden;
      const found = typeof crn === "number" ? crnMap.get(crn) : null;

      const title = found?.title || `Unknown course (CRN ${crn})`;
      const code = found?.course_code ? `${found.course_code}` : "";
      const sec = found?.section ? `S${found.section}` : "";

      season = ws.season;
      worksheetNumber = ws.worksheetNumber
      courseCache.push({
        crn,
        title,
        code,
        section: found?.section ?? null,
        hidden
      });

      crns.push(crn);

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
    userData = await getUserData();
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

async function submit() {
  try {
    submitButton.disabled = true;

    const promptText = (promptEl?.value ?? "").trim();
    if (!promptText) {
      setStatus("Please enter a prompt.", true);
      return;
    }

    if (!userData) {
      setStatus("User data not loaded yet. Please refresh.", true);
      return;
    }
    
    pushMessage("user", promptText);
    promptEl.value = "";

    const yearToLabel = (y) => {
      const map = {
        2029: "freshman",
        2028: "sophomore",
        2027: "junior",
        2026: "senior",
      };
      return map[y];
    };

    const payload = {
      netId: userData.netId,
      year: yearToLabel(userData.year),
      major: userData.major,
      courses: courseCache,
      prompt: promptText,
    };

    setStatus("Submitting…");

    const res = await fetch(API_ROUTE, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok) {
      const msg =
        (data && (data.error || data.message)) ||
        text ||
        `Request failed (${res.status})`;
      throw new Error(msg);
    }

    for (const a of data.actions){

      if (a.type == "update_worksheet") {
        const new_crns = a.args.selected;

        // find course that have been removed or added
        const removed_crns = crns.filter(crn => !new_crns.includes(crn));
        const added_crns = new_crns.filter(crn => !crns.includes(crn));
        crns = new_crns;

        if (removed_crns.length > 0) {
          removeCourses(removed_crns, { season, worksheetNumber });
        }

        if (added_crns.length > 0) {
          addCourses(added_crns, { season, worksheetNumber });
        }    

        // why is this lagging
        // set small delay
        setTimeout(async () => {
          try {
            // rerender the course list
            const { seasons, worksheets } = await fetchWorksheets();
            const seasonMaps = await getAllCoursesBySeasons(seasons);

            renderWorksheetDropdown(worksheets);
            worksheetSelect.disabled = false;

            // Default: first worksheet
            const currentKey = worksheetSelect.value;
            const current = worksheets.find((w) => makeWorksheetKey(w.season, w.worksheetNumber) === currentKey);
            if (current) renderWorksheetCourses(current, seasonMaps);

          } catch (err) {
            console.error(err);
          }
        }, 1000);

        


      }
      if (a.type == "create_worksheet") {
        const new_ws_crns = a.args.ids;
        const name = a.args.name;

        //TODO: create new worksheet
        //TODO: update season, worksheet number, crns, and course cache
        console.log("New worksheet: ",name, new_ws_crns);
      }
     
    }

    setStatus("Submitted successfully.");
    pushMessage("ai", data?.message ?? "(no response)");
    console.log("Submit response:", data);

    return data;
  } catch (err) {
    console.error(err);
    setStatus(err?.message || String(err), true);
    pushMessage("ai", `Error: ${err?.message || String(err)}`);
  } finally {
    submitButton.disabled = false;
  }
}


submitButton.addEventListener("click", submit);

function renderMessages() {
  if (!messagesEl) return;

  messagesEl.innerHTML = chat
    .map((m) => {
      const cls = m.role === "user" ? "msg msg-user" : "msg msg-ai";
      const html = (m.role === "ai") ? DOMPurify.sanitize(marked.parse(m.text)) : escapeHtml(m.text)
      // Use textContent-safe escaping, then inject as HTML
      // (newlines are handled by CSS white-space: pre-wrap)
      return `<div class="${cls}">${html}</div>`;
    })
    .join("");

  // auto-scroll to bottom
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function pushMessage(role, text) {
  chat.push({ role, text: String(text ?? "") });
  renderMessages();
}