from sentence_transformers import SentenceTransformer
import pandas as pd
import numpy as np
import torch
import re

# GPU check
print("CUDA available:", torch.cuda.is_available())
print("CUDA device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None")


import re

# obvious one-line boilerplate
SINGLE_LINE_DROP = re.compile(
    r"^(skip to main content|menu|search|show all breadcrumbs|breadcrumb|home|main|"
    r"accessibility.*|privacy.*|copyright.*|all rights reserved.*|\||"
    r"pagination navigation|past events|view past events)$",
    re.IGNORECASE
)

def looks_like_menu_line(ln: str) -> bool:
    """
    Heuristic: short, title-like, no punctuation, common for nav/menu items.
    """
    if len(ln) > 50:
        return False
    if re.search(r"[.!?;:]", ln):
        return False
    if re.fullmatch(r"[A-Za-z0-9&+/\-\s]+", ln) is None:
        return False

    words = ln.split()
    return 1 <= len(words) <= 5

def remove_menu_blocks(lines):
    """
    Remove long contiguous runs of menu-like lines.
    """
    out = []
    i = 0
    n = len(lines)

    while i < n:
        if looks_like_menu_line(lines[i]):
            j = i
            while j < n and looks_like_menu_line(lines[j]):
                j += 1

            # long run => nav/menu
            if (j - i) >= 10:
                i = j
                continue

        out.append(lines[i])
        i += 1

    return out

def low_signal(text: str) -> bool:
    """
    Detects nav-heavy or repetitive chunks after cleaning.
    """
    words = re.findall(r"[a-zA-Z]+", text.lower())
    if len(words) < 80:
        return True
    return (len(set(words)) / len(words)) < 0.30

def clean_text(text: str) -> str:
    """
    Aggressively clean crawled Yale page text for RAG.
    """

    # strip Passage prefix if present
    if text.startswith("Passage:"):
        text = text[len("Passage:"):].strip()

    # split into non-empty lines
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    cleaned = []
    prev = None

    for ln in lines:
        # drop obvious boilerplate lines
        if SINGLE_LINE_DROP.match(ln):
            continue

        # drop video / icon junk
        if "does not support the video tag" in ln.lower():
            continue
        if "\uf2a2" in ln or "\uf2a0" in ln:
            continue

        # drop very short lines (<= 3 words)
        if len(ln.split()) <= 3:
            continue

        # drop exact duplicates
        if ln == prev:
            continue

        cleaned.append(ln)
        prev = ln

    # remove large nav/menu blocks
    cleaned = remove_menu_blocks(cleaned)

    # rejoin
    result = "\n".join(cleaned).strip()

    # final low-signal filter
    if low_signal(result):
        return ""

    return result


model = SentenceTransformer(
    "BAAI/bge-large-en-v1.5",
    device="cuda" 
)

print("MODEL DEVICE: ", model.device)

import json
passages = []

with open("../scrapers/yale_crawl.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            obj = json.loads(line)
            passages.append(obj["title"]*5 + " " + obj["text"]) # weight title because it is descriptive 

# Chunking config
CHUNK_SIZE = 2000
OVERLAP = 300
i = 0

chunks = []
for p in passages:
    p = clean_text(p)
    if len(p) < 200:
        print("dropping")
        print(p)
        print()
        continue
    if i % 1000 == 0:
        pass #print(p)
    i += 1
    if len(p) <= CHUNK_SIZE:
        chunks.append(f"Passage: {p}")
    else:
        for i in range(0, len(p), CHUNK_SIZE - OVERLAP):
            chunk = p[i : i + CHUNK_SIZE]



# Encode in batches (CRITICAL)
embeddings = model.encode(
    chunks,
    batch_size=32,
    normalize_embeddings=True,
    show_progress_bar=True
)

# Save efficiently
np.savez(
    "embeddings_with_text.npz",
    embeddings=embeddings.astype("float32"),
    texts=np.array(chunks, dtype=object)
)



