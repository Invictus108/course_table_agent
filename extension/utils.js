const BASE_URL = "https://api.coursetable.com";
const USER_DATA_URL = BASE_URL + "/api/user/info";
const WORKSHEETS_URL = BASE_URL + "/api/user/worksheets";
const GRAPHQL_URL = BASE_URL + "/ferry/v1/graphql";
const UPDATE_WS_COURSES_URL = BASE_URL + "/api/user/updateWorksheetCourses";
const CREATE_WS_URL = BASE_URL + "/api/user/updateWorksheetMetadata";

export async function getUserData() {
  const res = await fetch(USER_DATA_URL, {
    method: "GET",
    credentials: "include",
    headers: {
      accept: "*/*",
      origin: "https://coursetable.com",
      referer: "https://coursetable.com/",
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Error: HTTP ${res.status}\n${text}`);
  }
  return res.json();
}

export async function fetchWorksheets() {
  const res = await fetch(WORKSHEETS_URL, {
    method: "GET",
    credentials: "include",
    headers: {
      accept: "*/*",
      origin: "https://coursetable.com",
      referer: "https://coursetable.com/",
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Worksheets request failed: HTTP ${res.status}\n${text}`);
  }
  const d = await res.json();
  return buildWorksheetIndex(d.data);
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

export async function fetchCoursesForSeason(seasonCode) {
  const res = await fetch(GRAPHQL_URL, {
    method: "POST",
    credentials: "include",
    headers: {
      "content-type": "application/json",
      accept: "*/*",
      origin: "https://coursetable.com",
      referer: "https://coursetable.com/",
    },
    body: JSON.stringify({
      query: COURSES_BY_SEASON_QUERY,
      variables: { season: seasonCode },
    }),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `GraphQL failed for season ${seasonCode}: HTTP ${res.status}\n${text}`,
    );
  }

  const json = await res.json();
  if (json.errors?.length) {
    throw new Error(
      `GraphQL errors for season ${seasonCode}:\n${JSON.stringify(json.errors, null, 2)}`,
    );
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
        courses: Array.isArray(ws?.courses) ? ws.courses : [],
      });
    }
  }

  // sort: newest season first (string season codes often sortable), then worksheet #
  worksheets.sort((a, b) => {
    if (a.season !== b.season)
      return String(b.season).localeCompare(String(a.season));
    return a.worksheetNumber - b.worksheetNumber;
  });

  return { seasons, worksheets };
}

export function makeWorksheetKey(season, worksheetNumber) {
  return `${season}::${worksheetNumber}`;
}

export async function getAllCoursesBySeasons(seasons) {
  const coursesBySeason = [];
  await Promise.all(
    seasons.map(async (season) => {
      const courses = await fetchCoursesForSeason(season);
      coursesBySeason[season] = courses;
    }),
  );
  return buildCrnToCourseTitleMap(coursesBySeason);
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
            section: lst?.section ?? "",
          });
        }
      }
    }

    seasonMaps.set(season, crnMap);
  }

  return seasonMaps;
}

async function updateWorksheetCourses(body) {
  console.log("updateWorksheetCourses", body);
  const res = await fetch(UPDATE_WS_COURSES_URL, {
    method: "POST",
    credentials: "include",
    headers: {
      "content-type": "application/json",
      accept: "*/*",
      origin: "https://coursetable.com",
      referer: "https://coursetable.com/",
    },
    body: JSON.stringify(body),
  });

  if (res.ok) {
    // 200: no body
    return { ok: true, error: null };
  }

  // 400: JSON error body (per spec), but still be defensive
  const text = await res.text().catch(() => "");
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch (_) {
    // ignore parse errors; we'll throw with raw text
  }

  // Prefer structured error if present
  const err = data?.error ?? null;

  // Build a good message (bulk: object; single: string)
  if (err && typeof err === "object") {
    // { "0": "ALREADY_BOOKMARKED", "3": "NOT_BOOKMARKED" }
    const details = Object.entries(err)
      .map(([i, code]) => `#${i}: ${code}`)
      .join(", ");
    throw new Error(
      `updateWorksheetCourses failed (HTTP ${res.status}): ${details}`,
    );
  }

  if (typeof err === "string") {
    throw new Error(
      `updateWorksheetCourses failed (HTTP ${res.status}): ${err}`,
    );
  }

  throw new Error(`updateWorksheetCourses failed: HTTP ${res.status}\n${text}`);
}

/**
 * Bulk-add CRNs to a worksheet.
 * Spec requires: season, worksheetNumber, crn, color, hidden
 */
function randomColor() {
  return `#${Math.floor(Math.random() * 0xffffff)
    .toString(16)
    .padStart(6, "0")}`;
}

export async function addCourses(add_crns, { season, worksheetNumber }) {
  console.log(season, worksheetNumber);
  const crns = Array.isArray(add_crns) ? add_crns : [];
  const updates = crns.map((crn) => ({
    action: "add",
    season,
    crn: Number(crn),
    worksheetNumber: Number(worksheetNumber),
    color: randomColor(),
    hidden: false,
  }));

  // If you're ever calling with 1 item, this still works.
  return updateWorksheetCourses(updates);
}

/**
 * Bulk-remove CRNs from a worksheet.
 * Spec requires: season, worksheetNumber, crn
 */
export async function removeCourses(remove_crns, { season, worksheetNumber }) {
  console.log(season, worksheetNumber);
  const crns = Array.isArray(remove_crns) ? remove_crns : [];
  const updates = crns.map((crn) => ({
    action: "remove",
    season,
    crn: Number(crn),
    worksheetNumber: Number(worksheetNumber),
  }));

  return updateWorksheetCourses(updates);
}

export async function createWorksheet(name, season, crns) {
  const res = await fetch(CREATE_WS_URL, {
    method: "POST",
    credentials: "include",
    headers: {
      "content-type": "application/json",
      accept: "*/*",
      origin: "https://coursetable.com",
      referer: "https://coursetable.com/",
    },
    body: JSON.stringify({
      action: "add",
      season: season,
      name: name,
    }),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Create worksheet failed: HTTP ${res.status}\n${text}`);
  }

  const { worksheetNumber } = await res.json();
  await addCourses(crns, { season, worksheetNumber });
}
