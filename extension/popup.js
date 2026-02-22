const WORKSHEETS_URL = "https://api.coursetable.com/api/user/worksheets";
const GRAPHQL_URL = "https://api.coursetable.com/ferry/v1/graphql";

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

// GraphQL query (parameterized)
const COURSES_BY_SEASON_QUERY = `
  query CoursesBySeason($season: String!) {
    courses(where: {season_code: {_eq: $season}}) {
      title
      credits
      listings {
        crn
        course_code
        section
      }
    }
  }
`;

async function fetchWorksheets() {
  const res = await fetch(WORKSHEETS_URL, {
    method: "GET",
    credentials: "include",
    headers: {
      "accept": "*/*",
      "origin": "https://coursetable.com",
      "referer": "https://coursetable.com/"
    }
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Worksheets request failed: HTTP ${res.status}\n${text}`);
  }
  const d = await res.json()
  return d.data;
}

async function fetchCoursesForSeason(seasonCode) {
  const res = await fetch(GRAPHQL_URL, {
    method: "POST",
    credentials: "include",
    headers: {
      "content-type": "application/json",
      "accept": "*/*",
      "origin": "https://coursetable.com",
      "referer": "https://coursetable.com/"
    },
    body: JSON.stringify({
      query: COURSES_BY_SEASON_QUERY,
      variables: { season: seasonCode }
    })
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`GraphQL failed for season ${seasonCode}: HTTP ${res.status}\n${text}`);
  }

  const json = await res.json();
  if (json.errors?.length) {
    throw new Error(`GraphQL errors for season ${seasonCode}:\n${JSON.stringify(json.errors, null, 2)}`);
  }
  return json.data?.courses || [];
}

function buildWorksheetIndex(worksheetsData) {
  const seasons = Object.keys(worksheetsData || {});
  const worksheets = [];

  for (const season of seasons) {
    const byNumber = worksheetsData[season] || {};
    for (const worksheetNumberStr of Object.keys(byNumber)) {
      const worksheetNumber = Number(worksheetNumberStr);
      const ws = byNumber[worksheetNumberStr];
      worksheets.push({
        season,
        worksheetNumber,
        name: ws?.name ?? `Worksheet ${worksheetNumber}`,
        courses: Array.isArray(ws?.courses) ? ws.courses : []
      });
    }
  }

  // sort: newest season first (string season codes often sortable), then worksheet #
  worksheets.sort((a, b) => {
    if (a.season !== b.season) return String(b.season).localeCompare(String(a.season));
    return a.worksheetNumber - b.worksheetNumber;
  });

  return { seasons, worksheets };
}

function makeWorksheetKey(season, worksheetNumber) {
  return `${season}::${worksheetNumber}`;
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

function buildCrnToCourseTitleMap(coursesBySeason) {
  // Map: season -> Map(crn -> {title, course_code, section})
  const seasonMaps = new Map();

  for (const [season, courses] of Object.entries(coursesBySeason)) {
    const crnMap = new Map();

    for (const c of courses) {
      const title = c?.title ?? "Untitled";
      const listings = Array.isArray(c?.listings) ? c.listings : [];

      for (const lst of listings) {
        const crn = lst?.crn;
        if (typeof crn !== "number") continue;

        // If multiple listings share crn (unlikely), keep first
        if (!crnMap.has(crn)) {
          crnMap.set(crn, {
            title,
            course_code: lst?.course_code ?? "",
            section: lst?.section ?? ""
          });
        }
      }
    }

    seasonMaps.set(season, crnMap);
  }

  return seasonMaps;
}

function renderWorksheetCourses(ws, seasonMaps) {
  const crnMap = seasonMaps.get(ws.season) || new Map();

  if (!ws.courses.length) {
    metaEl.textContent = `Worksheet has 0 courses.`;
    setCoursesHtml("—");
    return;
  }

  metaEl.textContent = `Season ${ws.season} • Worksheet #${ws.worksheetNumber} • ${ws.courses.length} course(s)`;

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
    setStatus("Fetching worksheets…");

    const worksheetsData = await fetchWorksheets();
    const { seasons, worksheets } = buildWorksheetIndex(worksheetsData);

    if (worksheets.length === 0) {
      renderWorksheetDropdown([]);
      setCoursesHtml("—");
      setStatus("No worksheets found. Are you logged in?", true);
      return;
    }

    setStatus(`Found ${worksheets.length} worksheet(s) across ${seasons.length} season(s).\nFetching courses for each season…`);

    // Fetch all seasons in parallel (one GraphQL request per season)
    const coursesBySeason = {};
    await Promise.all(
      seasons.map(async (season) => {
        const courses = await fetchCoursesForSeason(season);
        coursesBySeason[season] = courses;
      })
    );

    const seasonMaps = buildCrnToCourseTitleMap(coursesBySeason);

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
