import re
import time
import json
import heapq
import hashlib
import urllib.parse
from collections import defaultdict

import requests
from bs4 import BeautifulSoup
from readability import Document
import trafilatura


USER_AGENT = "YaleCourseSelectionResearchBot/1.0 (contact: you@example.com)"
TIMEOUT_S = 8.0
DELAY_S = 0.01

OUTPUT_JSONL = "focused_yale_academic_crawl.jsonl"

MAX_PAGES = 1000000
MAX_DEPTH = 6
MIN_TEXT_CHARS = 200
HOST_PAGE_CAP = 1000000

ALLOW_ALL_YALE_SUBDOMAINS = True
ALLOWED_QUERY_KEYS = set()

ALLOWED_HOSTS = {
    "www.yale.edu",
    "yale.edu",
    "news.yale.edu",
    "afamstudies.yale.edu",
    "african.macmillan.yale.edu",
    "americanstudies.yale.edu",
    "anthropology.yale.edu",
    "applied.math.yale.edu",
    "archaeology.yale.edu",
    "arthistory.yale.edu",
    "astronomy.yale.edu",
    "cbb.yale.edu",
    "ceas.yale.edu",
    "chem.yale.edu",
    "classics.yale.edu",
    "cogsci.yale.edu",
    "complit.yale.edu",
    "cs.yale.edu",
    "earth.yale.edu",
    "eall.yale.edu",
    "earlymodern.yale.edu",
    "economics.yale.edu",
    "eeb.yale.edu",
    "engineering.yale.edu",
    "english.yale.edu",
    "environment.yale.edu",
    "erm.yale.edu",
    "filmstudies.yale.edu",
    "french.yale.edu",
    "german.yale.edu",
    "hshm.yale.edu",
    "history.yale.edu",
    "humanities.yale.edu",
    "italian.yale.edu",
    "jackson.yale.edu",
    "jewishstudies.yale.edu",
    "law.yale.edu",
    "ling.yale.edu",
    "macmillan.yale.edu",
    "math.yale.edu",
    "mbb.yale.edu",
    "mcdb.yale.edu",
    "medicine.yale.edu",
    "medieval.yale.edu",
    "nelc.yale.edu",
    "nursing.yale.edu",
    "philosophy.yale.edu",
    "physics.yale.edu",
    "politicalscience.yale.edu",
    "psychology.yale.edu",
    "religiousstudies.yale.edu",
    "slavic.yale.edu",
    "sociology.yale.edu",
    "som.yale.edu",
    "span-port.yale.edu",
    "statistics.yale.edu",
    "tdps.yale.edu",
    "wgss.yale.edu",
    "www.architecture.yale.edu",
    "yalemusic.yale.edu",
    "ysph.yale.edu",
    "biology.yale.edu",
    "linguistics.yale.edu",
}

POSITIVE_TERMS = [
    "department",
    "program",
    "center",
    "institute",
    "seminar",
    "colloquium",
    "discussion",
    "debate",
    "undergraduate",
    "graduate",
    "areas of study",
    "course",
    "courses",
    "students",
    "advising",
    "profile",
    "about",
    "directory",
    "email",
    "fellow",
    "people",
    "news",
    "project",
]

VERY_POSITIVE_TERMS = [
    "office",
    "biography",
    "publications",
    "research interests",
    "research areas",
    "research website",
    "research ",
    "lab ",
    "expert",
    "professor",
    "professor of",
    "faculty",
]

NEGATIVE_TERMS = [
    "archive",
    "collection",
    "museum",
    "gallery",
    "exhibit",
    "exhibition",
    "finding aid",
    "donate",
    "giving",
    "login",
    "signin",
    "register",
    "feed",
    "rss",
    "wp-json",
    "xmlrpc",
]

SEED_URLS = [
    "https://www.yale.edu/academics",
    "https://news.yale.edu/",
    "https://medicine.yale.edu/",
    "https://law.yale.edu/",
    "https://environment.yale.edu/",
    "https://som.yale.edu/",
    "https://engineering.yale.edu/",
    "https://economics.yale.edu/",
    "https://english.yale.edu/",
    "https://history.yale.edu/",
    "https://politicalscience.yale.edu/",
    "https://psychology.yale.edu/",
    "https://physics.yale.edu/",
    "https://chem.yale.edu/",
    "https://biology.yale.edu/",
    "https://statistics.yale.edu/",
    "https://philosophy.yale.edu/",
    "https://linguistics.yale.edu/",
    "https://sociology.yale.edu/",
    "https://anthropology.yale.edu/",
]


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def doc_id(url: str) -> str:
    return sha256_hex(url)[:24]


def host_from_url(url: str) -> str:
    return urllib.parse.urlsplit(url).netloc.lower().split("@")[-1]


def is_yale_domain(url: str) -> bool:
    host = host_from_url(url)
    return host == "yale.edu" or host.endswith(".yale.edu")


def host_allowed(url: str) -> bool:
    host = host_from_url(url)
    return host in ALLOWED_HOSTS or (ALLOW_ALL_YALE_SUBDOMAINS and is_yale_domain(url))


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url.strip())
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower().split("@")[-1]
    netloc = re.sub(r":(80|443)$", "", netloc)

    path = parsed.path or "/"
    path = re.sub(r"/{2,}", "/", path)
    path = re.sub(r"/index\.(html?|php)$", "/", path, flags=re.I)
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
    query_pairs = [(k, v) for k, v in query_pairs if k in ALLOWED_QUERY_KEYS]
    query_pairs.sort()
    query = urllib.parse.urlencode(query_pairs)

    return urllib.parse.urlunsplit((scheme, netloc, path, query, ""))


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def text_hash(text: str) -> str:
    text = re.sub(r"\s+", " ", text.lower()).strip()
    return sha256_hex(text)


def looks_like_html(resp: requests.Response) -> bool:
    ct = (resp.headers.get("Content-Type") or "").lower()
    return "text/html" in ct or "application/xhtml+xml" in ct


def is_probably_bad_url(url: str) -> bool:
    u = url.lower()

    if re.search(r"\.(pdf|jpg|jpeg|png|gif|svg|zip|docx?|xlsx?|pptx?|mp4|mp3)$", u):
        return True

    if re.search(r"[?&](page|paged|sort|filter|facet|search|q)=", u):
        return True

    if re.search(r"/page/\d+", u):
        return True

    return any(term in u for term in NEGATIVE_TERMS)


def count_matches(text: str, terms: list[str]) -> int:
    text = text.lower()
    return sum(1 for term in terms if term in text)


def relevance_score(url: str, title: str, text: str) -> int:
    sample = f"{url}\n{title}\n{text[:8000]}".lower()
    score = 0
    score += 4 * count_matches(sample, POSITIVE_TERMS)
    score -= 5 * count_matches(sample, NEGATIVE_TERMS)

    score += 10 * count_matches(sample, VERY_POSITIVE_TERMS)

    return score


def link_priority(url: str, anchor: str = "") -> int:
    score = 0
    host = host_from_url(url)

    if host in ALLOWED_HOSTS:
        score += 8

    u = url.lower()
    a = anchor.lower()

    score += 3 * count_matches(u, POSITIVE_TERMS)
    score += 3 * count_matches(a, POSITIVE_TERMS)

    score += 5 * count_matches(u, VERY_POSITIVE_TERMS)
    score += 5 * count_matches(a, VERY_POSITIVE_TERMS)

    score -= 4 * count_matches(u, NEGATIVE_TERMS)
    score -= 4 * count_matches(a, NEGATIVE_TERMS)

    return score


def extract_text_and_title(html: str, url: str) -> tuple[str, str]:
    try:
        _, text, _ = (
            trafilatura.baseline(
                html,
            )
            or ""
        )

        meta = trafilatura.extract_metadata(html, default_url=url)
        title = meta.title.strip() if meta and meta.title else ""
    except Exception:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript", "template"]):
            tag.decompose()
        title = soup.title.get_text(strip=True) if soup.title else ""
        text = soup.get_text(separator="\n")

    return normalize_whitespace(text), title


def extract_links(html: str, base_url: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    out = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue

        url = normalize_url(urllib.parse.urljoin(base_url, href))
        anchor = a.get_text(" ", strip=True)
        out.append((url, anchor))

    return out


class Frontier:
    def __init__(self):
        self.heap = []
        self.counter = 0

    def push(self, priority: int, url: str, depth: int):
        heapq.heappush(self.heap, (-priority, self.counter, url, depth))
        self.counter += 1

    def pop(self):
        neg_priority, _, url, depth = heapq.heappop(self.heap)
        return -neg_priority, url, depth

    def __len__(self):
        return len(self.heap)


def crawl_yale_focused(
    seed_urls=SEED_URLS,
    output_jsonl_path=OUTPUT_JSONL,
    max_pages=MAX_PAGES,
    max_depth=MAX_DEPTH,
    delay_s=DELAY_S,
    timeout_s=TIMEOUT_S,
):
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    frontier = Frontier()
    seen_enqueued = set()
    seen_fetched = set()
    seen_text_hashes = set()
    host_counts = defaultdict(int)

    pages_fetched = 0
    pages_written = 0

    for url in seed_urls:
        url = normalize_url(url)
        if is_yale_domain(url) and host_allowed(url) and not is_probably_bad_url(url):
            frontier.push(max(20, link_priority(url)), url, 0)
            seen_enqueued.add(url)

    with open(output_jsonl_path, "w", encoding="utf-8") as f:
        while frontier and pages_written < max_pages:
            _, url, depth = frontier.pop()

            if depth > max_depth:
                continue
            if url in seen_fetched:
                continue
            if not is_yale_domain(url) or not host_allowed(url):
                continue
            if is_probably_bad_url(url):
                continue

            try:
                resp = session.get(url, timeout=timeout_s, allow_redirects=True)
                time.sleep(delay_s)
            except Exception:
                continue

            if resp.status_code != 200 or not looks_like_html(resp):
                continue

            final_url = normalize_url(resp.url)
            if final_url in seen_fetched:
                continue
            if not is_yale_domain(final_url) or not host_allowed(final_url):
                continue
            if is_probably_bad_url(final_url):
                continue

            seen_fetched.add(final_url)
            pages_fetched += 1

            host = host_from_url(final_url)
            host_counts[host] += 1

            html = resp.text
            text, title = extract_text_and_title(html, final_url)

            if len(text) < MIN_TEXT_CHARS:
                continue

            h = text_hash(text)
            if h in seen_text_hashes:
                continue
            seen_text_hashes.add(h)

            score = relevance_score(final_url, title, text)

            if score >= 10:
                record = {
                    "id": doc_id(final_url),
                    "url": final_url,
                    "title": title,
                    "text": text,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                pages_written += 1
                print(f"[KEEP {pages_written}] depth={depth} score={score} {final_url}")
            else:
                print(f"[SKIP] depth={depth} score={score} {final_url}")

            if depth < max_depth and score >= 12:
                for link, anchor in extract_links(html, final_url):
                    if link in seen_enqueued:
                        continue
                    if not is_yale_domain(link) or not host_allowed(link):
                        continue
                    if is_probably_bad_url(link):
                        continue

                    child_score = link_priority(link, anchor)
                    if child_score < 8:
                        continue

                    host = host_from_url(link)
                    penalty = host_counts[host] / 80

                    seen_enqueued.add(link)
                    frontier.push(
                        child_score + score // 12 - depth - penalty,
                        link,
                        depth + 1,
                    )

    print(
        f"Done. Fetched={pages_fetched}, wrote={pages_written}, output={output_jsonl_path}"
    )


if __name__ == "__main__":
    crawl_yale_focused()
