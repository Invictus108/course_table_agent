import json

# load json

with open('yale_subject_pages_raw_text.json', 'r', encoding="utf-8") as f:
    data = json.load(f)

import re

def stitch_course_lists(lines: list[str]) -> list[str]:
    stitched = []
    for ln in lines:
        # bare comma line
        if ln == "," and stitched:
            stitched[-1] += ","
            continue

        # bare course number (e.g. "3602")
        if re.fullmatch(r"\d{3,4}", ln) and stitched:
            stitched[-1] += f" {ln}"
            continue

        stitched.append(ln)

    return stitched

def clean_yale_blob(raw: str) -> str:
    # Normalize line breaks + strip
    raw = raw.replace("\r\n", "\n").replace("\r", "\n").strip()

    # Split into non-empty lines (keep structure)
    lines = [ln.strip() for ln in raw.split("\n")]
    lines = [ln for ln in lines if ln]

    # 1) Drop everything after footer marker(s)
    footer_markers = [
        "Print Options",
        "Send Page to Printer",
        "Download Page (PDF)",
        "Download 2025-26 YCPS PDF",
        "Privacy policy",
        "Copyright ©",
    ]
    def first_index_of_any(markers):
        for i, ln in enumerate(lines):
            for m in markers:
                if m.lower() in ln.lower():
                    return i
        return None

    stop = first_index_of_any(footer_markers)
    if stop is not None and stop > 0:
        lines = lines[:stop]

    # 2) Drop top navigation/header junk by starting at first “content marker”
    # (ordered from strongest to weakest)
    start_markers = [
        "Directors of undergraduate studies",
        "Director of undergraduate studies",
        "Certificate director",
        "General Information",
        "Overview",
        "Requirements of the Major",
        "Requirements of the Certificate",
        "Summary of Requirements",
        "SUMMARY OF MAJOR REQUIREMENTS",
        # certificates sometimes have a lowercase "requirements" heading
        "requirements",
    ]

    start = 0
    for i, ln in enumerate(lines):
        if any(ln.lower().startswith(m.lower()) or ln.lower() == m.lower() for m in start_markers):
            start = i
            break
    lines = lines[start:]

    # 3) Optionally drop trailing “View Courses” / roadmap junk (before footer)
    tail_markers = [
        "View Courses",
        "Roadmap Library",
        "View ",  # catches "View African Studies Courses" etc.
    ]
    # Stop at the first "View ..." line *only if* it's clearly a navigation CTA.
    for i, ln in enumerate(lines):
        if ln == "View Courses" or ln.startswith("View ") or ln.endswith(" Roadmap Library") or ln == "Roadmap Library":
            # don't cut too early if it appears at the very top (rare)
            if i > 20:
                lines = lines[:i]
                break

    # 4) Remove obvious boilerplate lines anywhere in the remaining text
    drop_exact = {
        "Skip to Content",
        "AZ Index",
        "Catalog Home",
        "Institution Home",
        "Bulletin of Yale University",
        "Menu",
        "Search Bulletin",
        "A–Z Index",
        "Print/Download Options",
        "Bulletin Archive",
        "Yale University Publications",
        "YCPS Archive",
        ". Click to change.",
        "Current Edition:",
        "Catalog Navigation",
        "The Undergraduate Curriculum",
        "Academic Regulations",
        "Majors by Disciplines",
        "Majors in Yale College",
        "Major Roadmaps",
        "Certificates in Yale College",
        "Yale College and Departmental Attributes",
        "Subjects of Instruction",
        "Yale",
        "Accessibility at Yale",
        "All rights reserved",
        "Contact Us",
        "Facebook",
        "Twitter",
        "YouTube",
        "Sina Weibo",
        "Tumblr",
        "Close this window",
    }
    cleaned = []
    for ln in lines:
        if ln in drop_exact:
            continue
        # drop archive year list lines like "2024-2025", "2019-2020", etc.
        if re.fullmatch(r"\d{4}-\d{4}", ln):
            continue
        cleaned.append(ln)

    # 5) Light whitespace cleanup inside lines
    cleaned = [re.sub(r"\s+", " ", ln).strip() for ln in cleaned]
    cleaned = stitch_course_lists(cleaned)

    # Re-join with newlines so headings still look like headings
    return "\n".join(cleaned).strip()


for i in data["pages"]:
    print(i["subject"])
    i["text"] = clean_yale_blob(i["text"])

print(data)

with open("yale_subject_pages_cleaned.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)