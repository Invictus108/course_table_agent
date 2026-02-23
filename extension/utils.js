const BASE_URL = "https://api.coursetable.com"
const USER_DATA_URL = BASE_URL + "/api/user/info"
const WORKSHEETS_URL = BASE_URL + "/api/user/worksheets";
const GRAPHQL_URL = BASE_URL + "/ferry/v1/graphql";

export async function getUserData() {
  const res = await fetch(USER_DATA_URL, {
    method: "GET",
    credentials: "include",
    headers: {
      "accept": "*/*",
      "origin": "https://coursetable.com",
      "referer": "https://coursetable.com/"
    }
  })

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

export function makeWorksheetKey(season, worksheetNumber) {
  return `${season}::${worksheetNumber}`;
}

export async function getAllCoursesBySeasons(seasons) {
  const coursesBySeason = []
  await Promise.all(
      seasons.map(async (season) => {
        const courses = await fetchCoursesForSeason(season);
        coursesBySeason[season] = courses;
      })
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
            section: lst?.section ?? ""
          });
        }
      }
    }

    seasonMaps.set(season, crnMap);
  }

  return seasonMaps;
}
