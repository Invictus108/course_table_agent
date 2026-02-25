import json
import random
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


INDEX_URL = "https://catalog.yale.edu/ycps/subjects-of-instruction/"
OUT_PATH = "yale_subject_pages_raw_text.json"

# “short delay” + a little jitter so you don’t look like a perfectly-timed bot
BASE_DELAY_SECONDS = 0.8
JITTER_SECONDS = 0.6


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }
    )

    retry = Retry(
        total=7,
        connect=7,
        read=7,
        backoff_factor=0.9,  # exponential backoff
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def fetch_html(session: requests.Session, url: str) -> str:
    r = session.get(url, timeout=30)
    r.raise_for_status()
    return r.text


def extract_subject_links(index_html: str, index_url: str) -> list[dict]:
    """
    Yale index page: #textcontainer contains the list; you said the classes/links
    you want are always in <li> elements.
    """
    soup = BeautifulSoup(index_html, "html.parser")
    container = soup.select_one("#textcontainer")
    if not container:
        raise ValueError('Could not find #textcontainer on index page.')

    targets = []
    seen = set()

    for li in container.select("li"):
        a = li.select_one("a[href]")
        if not a:
            continue
        href = (a.get("href") or "").strip()
        if not href:
            continue

        url = urljoin(index_url, href)
        if url in seen:
            continue
        seen.add(url)

        targets.append({"name": a.get_text(strip=True) or None, "url": url})

    return targets


def html_to_raw_text(page_html: str) -> str:
    """
    "Raw text" (not HTML). Minimal cleanup: drop script/style/noscript,
    then take all visible-ish text from the page.
    """
    soup = BeautifulSoup(page_html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # This grabs essentially all text on the page (nav, footer, etc. too).
    return soup.get_text("\n", strip=True)


def scrape_all() -> None:
    session = make_session()

    index_html = fetch_html(session, INDEX_URL)
    subjects = extract_subject_links(index_html, INDEX_URL)

    results = []
    failed = []

    for i, subj in enumerate(subjects, start=1):
        url = subj["url"]
        try:
            page_html = fetch_html(session, url)
            text = html_to_raw_text(page_html)

            results.append(
                {
                    "subject": subj["name"],
                    "url": url,
                    "text": text,
                }
            )
            print(f"[{i}/{len(subjects)}] OK  {url}  ({len(text)} chars)")
        except requests.RequestException as e:
            print(f"[{i}/{len(subjects)}] FAIL {url} -> {e}")
            failed.append({"subject": subj["name"], "url": url, "error": str(e)})

        time.sleep(BASE_DELAY_SECONDS + random.random() * JITTER_SECONDS)

    payload = {
        "index_url": INDEX_URL,
        "count": len(results),
        "failed_count": len(failed),
        "pages": results,
        "failed": failed,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\nWrote {OUT_PATH} with {len(results)} pages ({len(failed)} failed).")


if __name__ == "__main__":
    scrape_all()