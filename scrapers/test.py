import re
import time
import json
import hashlib
import urllib.parse
import datetime as dt
from collections import deque

import requests
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
from readability import Document  # pip install readability-lxml
from lxml.html import fromstring  # pip install lxml


def normalize_url(url: str) -> str:
    """Normalize URL: remove fragments, trim trailing slash (except root), keep query."""
    url = url.strip()
    parsed = urllib.parse.urlsplit(url)
    parsed = parsed._replace(fragment="")
    # Normalize scheme/host to lowercase
    netloc = parsed.netloc.lower()
    scheme = parsed.scheme.lower() if parsed.scheme else "https"
    path = parsed.path or "/"
    # Remove default ports
    netloc = re.sub(r":(80|443)$", "", netloc)
    # Normalize multiple slashes
    path = re.sub(r"/{2,}", "/", path)
    # Trim trailing slash (except root)
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return urllib.parse.urlunsplit((scheme, netloc, path, parsed.query, ""))


def is_yale_domain(url: str) -> bool:
    """Allow yale.edu and subdomains (*.yale.edu)."""
    try:
        host = urllib.parse.urlsplit(url).netloc.lower()
        # remove credentials if any
        host = host.split("@")[-1]
        return host == "yale.edu" or host.endswith(".yale.edu")
    except Exception:
        return False


def looks_like_html(response: requests.Response) -> bool:
    ct = (response.headers.get("Content-Type") or "").lower()
    return "text/html" in ct or "application/xhtml+xml" in ct


def extract_text_and_title(html: str, base_url: str) -> tuple[str, str]:
    """
    Extract main-article text + a reasonable title using readability-lxml.
    Falls back to a simple BeautifulSoup full-page text extraction if needed.
    """
    # --- Readability pass (main content) ---
    try:
        doc = Document(html, url=base_url)

        title = (doc.short_title() or doc.title() or "").strip()
        main_html = doc.summary(html_partial=True)  # HTML of "best" content

        soup = BeautifulSoup(main_html, "html.parser")
        for tag in soup(["script", "style", "noscript", "template"]):
            tag.decompose()

        text = soup.get_text(separator="\n")

    except Exception:
        # --- Fallback: original "whole page" extraction ---
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "template"]):
            tag.decompose()

        title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
        text = soup.get_text(separator="\n")

    # --- Common cleanup ---
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    return text, title


def extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a.get("href")
        if not href:
            continue
        href = href.strip()

        # Skip mailto/tel/javascript
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue

        abs_url = urllib.parse.urljoin(base_url, href)
        abs_url = normalize_url(abs_url)

        links.append(abs_url)
    return links


class RobotsCache:
    def __init__(self, user_agent: str, timeout: float):
        self.user_agent = user_agent
        self.timeout = timeout
        self._cache: dict[str, RobotFileParser] = {}

    def allowed(self, url: str) -> bool:
        parts = urllib.parse.urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        if base not in self._cache:
            rp = RobotFileParser()
            rp.set_url(urllib.parse.urljoin(base, "/robots.txt"))
            try:
                rp.read()
            except Exception:
                # If robots.txt can't be fetched, behave conservatively: disallow crawling.
                # You can switch this to allow if you prefer, but disallow is safer.
                self._cache[base] = rp
                return False
            self._cache[base] = rp
        rp = self._cache[base]
        try:
            return rp.can_fetch(self.user_agent, url)
        except Exception:
            return False


def doc_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]


def crawl_yale(
    seed_urls: list[str],
    output_jsonl_path: str = "yale_crawl.jsonl",
    user_agent: str = "RAGResearchBot/1.0 (contact: you@example.com)",
    max_pages: int = 500,
    max_depth: int = 3,
    delay_s: float = 1.0,
    timeout_s: float = 15.0,
    allowed_path_prefixes: list[str] | None = None,
):
    """
    A polite crawler:
    - stays on yale.edu / *.yale.edu
    - respects robots.txt
    - bounded by max_pages and max_depth
    - writes JSONL for RAG
    """
    allowed_path_prefixes = allowed_path_prefixes or []

    def path_allowed(u: str) -> bool:
        if not allowed_path_prefixes:
            return True
        path = urllib.parse.urlsplit(u).path or "/"
        return any(path.startswith(pfx) for pfx in allowed_path_prefixes)

    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})

    robots = RobotsCache(user_agent=user_agent, timeout=timeout_s)

    queue = deque()
    seen = set()

    for s in seed_urls:
        u = normalize_url(s)
        if is_yale_domain(u) and path_allowed(u):
            queue.append((u, 0))
            seen.add(u)

    pages_written = 0

    with open(output_jsonl_path, "w", encoding="utf-8") as f:
        while queue and pages_written < max_pages:
            url, depth = queue.popleft()

            try:
                print(url)
                if depth > max_depth:
                    continue
                if not is_yale_domain(url) or not path_allowed(url):
                    continue

                # robots check
                if not robots.allowed(url):
                    continue

                try:
                    resp = session.get(url, timeout=timeout_s, allow_redirects=True)
                except Exception:
                    continue

                final_url = normalize_url(resp.url)
                if not is_yale_domain(final_url) or not path_allowed(final_url):
                    continue

                status = resp.status_code

                # Only store HTML pages; skip binaries/PDFs/etc for now
                if status == 200 and looks_like_html(resp):
                    html = resp.text
                    text, title = extract_text_and_title(html, final_url)

                    record = {
                        "id": doc_id(final_url),
                        "url": final_url,
                        "domain": "yale.edu",
                        "title": title,
                        "text": text,
                        "content_type": (resp.headers.get("Content-Type") or ""),
                        "status": status,
                        "fetched_at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    pages_written += 1

                    # Enqueue new links
                    if depth < max_depth:
                        for link in extract_links(html, final_url):
                            if link in seen:
                                continue
                            if not is_yale_domain(link):
                                continue
                            if not path_allowed(link):
                                continue
                            # Skip very “crawler-trappy” URLs with huge querystrings
                            if len(urllib.parse.urlsplit(link).query) > 200:
                                continue
                            seen.add(link)
                            queue.append((link, depth + 1))

                # Polite delay
                time.sleep(delay_s)
            except Exception as e:
                print(f"Error processing {url}: {e}")

    print(f"Done. Wrote {pages_written} pages to {output_jsonl_path}.")


if __name__ == "__main__":
    # Start with a small set of seeds; expand carefully.
    seeds = [
        "https://www.yale.edu/",
    ]

    crawl_yale(
        seed_urls=seeds,
        output_jsonl_path="clean_yale_crawl_v2.jsonl",
        max_pages=1000000,
        max_depth=10000,
        delay_s=0.1,
        # Optionally restrict to certain sections, e.g. only admissions pages:
        # allowed_path_prefixes=["/admissions", "/about"],
    )
