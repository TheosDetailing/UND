#!/usr/bin/env python3
"""
Obsidian Note Generator (Two-Call, Robust, No 3rd-Party Deps)

Usage:
  python3 obsidian_note_gen.py "Subject here"
  python3 obsidian_note_gen.py --file subjects.csv      # one subject per line; if CSV, first column is used
  python3 obsidian_note_gen.py --help

Config:
  Edit API_URL and NOTES_DIR below (or override via environment variables).
"""

from __future__ import annotations
import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from typing import List, Tuple, Dict, Any, Optional

# =========================
# User-configurable defaults
# (override at runtime via env vars: API_URL, NOTES_DIR, PER_REQUEST_DELAY_SECONDS, DELAY_BETWEEN_CALLS_SECONDS)
# =========================
API_URL = os.environ.get("API_URL", "http://192.168.50.4:8787/infer")
NOTES_DIR = os.environ.get(
    "NOTES_DIR",
    "/Users/theonai/Library/Mobile Documents/com~apple~CloudDocs/LLM/Index LLM",
)
PER_REQUEST_DELAY_SECONDS = int(os.environ.get("PER_REQUEST_DELAY_SECONDS", "120"))  # batch spacing
DELAY_BETWEEN_CALLS_SECONDS = int(os.environ.get("DELAY_BETWEEN_CALLS_SECONDS", "30"))  # meta → body

# Fixed, real-world 20 broad topics (DDC/BISAC-informed)
TOPIC_LIST: List[str] = [
    "Computers & Information",
    "Philosophy",
    "Psychology & Self-Help",
    "Religion & Spirituality",
    "Social Sciences",
    "Politics & Government",
    "Economics & Business",
    "Education & Teaching",
    "Language & Linguistics",
    "Science (General)",
    "Mathematics",
    "Physics & Astronomy",
    "Chemistry",
    "Biology",
    "Medicine & Health",
    "Engineering & Technology",
    "Arts & Design",
    "Literature & Writing",
    "History & Geography",
    "Travel & Recreation",
]


# -------------------------
# Utilities
# -------------------------
def iso_now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")


def slug_file(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s or "note"


def slug_tag(s: str) -> str:
    s = s.lower().replace("&", " and ").replace("+", " and ")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s


def escape_yaml(s: str) -> str:
    return s.replace('"', '\\"')


def first_token_word(s: str) -> str:
    # for fallback one-word topic
    tok = re.sub(r"[^A-Za-z0-9]+", " ", s).strip().split()
    return tok[0].lower() if tok else "topic"


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def atomic_write(path: str, data: str) -> None:
    ensure_dir(os.path.dirname(path))
    base = os.path.basename(path)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix=f"{base}.", dir=os.path.dirname(path), delete=False
    ) as tf:
        tf.write(data)
        tmp_name = tf.name
    os.replace(tmp_name, path)


# -------------------------
# Model interaction
# -------------------------
def http_json_post(url: str, payload: Dict[str, Any], timeout: int = 120) -> Dict[str, Any]:
    req = urllib.request.Request(
        url=url,
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload).encode("utf-8"),
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", "replace")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"ok": False, "output": "", "raw": body}


def api_infer(prompt: str) -> str:
    """Call your local API and return the .output string (or empty)."""
    envelope = http_json_post(API_URL, {"prompt": prompt})
    out = envelope.get("output", "")
    if isinstance(out, str):
        return out
    # some models might return JSON already
    try:
        return json.dumps(out)
    except Exception:
        return ""


# -------------------------
# Prompt builders
# -------------------------
def build_prompt_meta(subject: str) -> str:
    topics_json = json.dumps(TOPIC_LIST)
    return f"""You will ONLY return strict JSON. No markdown or extra text.

Subject: {subject}

TASK:
1) "title": a concise title.
2) "topic": a ONE-WORD topic (no spaces).
3) "topics": pick 2–4 distinct items from TOPICS (exact string match; avoid near-duplicates).
4) "tags": 1–3 short extra tags (1–2 words each), semantically distinct from "topics".

TOPICS = {topics_json}

OUTPUT:
{{
  "title": "Concise Title",
  "topic": "OneWordTopic",
  "topics": ["Item from TOPICS", "..."],
  "tags": ["short-tag-1", "short-tag-2"]
}}"""
}

def build_prompt_body(subject: str, one_word_topic: str, topics: List[str], tags: List[str]) -> str:
    return (
        "Return ONLY the body text (no JSON/YAML or code fences).\n\n"
        f"Subject: {subject}\n"
        f"One-word topic: {one_word_topic}\n"
        f"Chosen broad topics: {json.dumps(topics)}\n"
        f"Extra tags: {json.dumps(tags)}\n\n"
        "Write ~900–1300 words of cohesive, detailed prose:\n"
        "- Short paragraphs; light bullets only when helpful.\n"
        "- Include concrete facts, dates, definitions, trade-offs, practical implications.\n"
        "- Optional parenthetical source mentions (author/site + year). No URLs."
    )


# -------------------------
# Parsing / Validation
# -------------------------
def parse_meta_output(raw: str) -> Tuple[str, str, List[str], List[str]]:
    """
    Expecting JSON with keys: title, topic, topics (list), tags (list).
    Return (title, topic, topics_list, tags_list) with fallbacks.
    """
    title = ""
    topic = ""
    topics: List[str] = []
    tags: List[str] = []

    try:
        obj = json.loads(raw)
        title = obj.get("title") or ""
        topic = obj.get("topic") or ""
        topics_in = obj.get("topics") or []
        tags_in = obj.get("tags") or []
        if isinstance(topics_in, list):
            topics = [t for t in topics_in if isinstance(t, str)]
        if isinstance(tags_in, list):
            tags = [t for t in tags_in if isinstance(t, str)]
    except Exception:
        # raw might be not-JSON; leave fallbacks
        pass

    return title, topic, topics, tags


def sanitize_topics(topics: List[str]) -> List[str]:
    seen = set()
    clean: List[str] = []
    for t in topics:
        if t in TOPIC_LIST and t not in seen:
            clean.append(t)
            seen.add(t)
        if len(clean) >= 4:
            break
    return clean


def fallback_topic_for_subject(subject: str) -> str:
    s = subject.lower()
    checks = [
        (("ai", "llm", "data", "internet", "comput", "info"), "Computers & Information"),
        (("philosophy", "ethic", "logic", "epistem"), "Philosophy"),
        (("psychology", "adhd", "mental", "therapy", "self-help"), "Psychology & Self-Help"),
        (("religion", "spiritual", "theolog", "mytholog"), "Religion & Spirituality"),
        (("sociolog", "anthropolog", "culture", "gender"), "Social Sciences"),
        (("politic", "policy", "government", "law", "election"), "Politics & Government"),
        (("business", "startup", "market", "econom", "finance", "invest"), "Economics & Business"),
        (("education", "teaching", "curriculum", "pedagog"), "Education & Teaching"),
        (("linguist", "grammar", "language", "translate"), "Language & Linguistics"),
        (("science", "scientific method"), "Science (General)"),
        (("math", "algebra", "calculus", "statistic"), "Mathematics"),
        (("physics", "astronomy", "cosmo", "quantum"), "Physics & Astronomy"),
        (("chemistry", "chemical", "compound", "reagent"), "Chemistry"),
        (("biology", "genetic", "zoolog", "ecolog", "flora", "fauna"), "Biology"),
        (("medicine", "health", "clinic", "nutrition", "sleep"), "Medicine & Health"),
        (("engineer", "robotic", "civil", "electrical", "mechanical", "technology"), "Engineering & Technology"),
        (("art", "design", "photo", "architec"), "Arts & Design"),
        (("literature", "writing", "poetry", "novel", "criticism"), "Literature & Writing"),
        (("history", "geograph", "cartograph", "histor"), "History & Geography"),
        (("travel", "touris", "hobby", "sport", "recreat"), "Travel & Recreation"),
    ]
    for needles, label in checks:
        if any(n in s for n in needles):
            return label
    return "Computers & Information"


def build_yaml_tags(topics: List[str], extra_tags: List[str], topic_word: str) -> List[str]:
    vals = [*topics, *extra_tags]
    slugs: List[str] = []
    seen = set()
    for v in vals:
        sv = slug_tag(str(v))
        if sv and sv not in seen:
            slugs.append(sv)
            seen.add(sv)
    if not slugs:
        slugs.append(slug_tag(topic_word or "topic"))
    return slugs


# -------------------------
# Note writer
# -------------------------
def render_markdown(
    subject: str,
    title: str,
    one_word_topic: str,
    topics: List[str],
    tags_slugs: List[str],
    body: str,
) -> str:
    now = iso_now()
    title_esc = escape_yaml(title or subject)
    topics_json = json.dumps(topics, ensure_ascii=False)
    tags_inside = ", ".join(tags_slugs)
    front = (
        f"---\n"
        f'title: "{title_esc}"\n'
        f'created: "{now}"\n'
        f'topic: "{one_word_topic or first_token_word(subject)}"\n'
        f"topics: {topics_json}\n"
        f"tags: [{tags_inside}]\n"
        f"---\n\n"
    )
    return front + (body or "").rstrip() + "\n"


def write_note(subject: str, content: str) -> str:
    filename = slug_file(subject) + ".md"
    path = os.path.join(NOTES_DIR, filename)
    atomic_write(path, content)
    return path


# -------------------------
# Core pipeline
# -------------------------
def process_subject(subject: str) -> Optional[str]:
    subject = subject.strip()
    if not subject:
        return None

    # Call #1: metadata
    meta_prompt = build_prompt_meta(subject)
    raw_meta = api_infer(meta_prompt)
    title, topic, topics, tags = parse_meta_output(raw_meta)

    if not title:
        title = subject
    if not topic or " " in topic:
        topic = first_token_word(subject)

    topics = sanitize_topics(topics)
    if not topics:
        topics = [fallback_topic_for_subject(subject)]

    # wait between calls
    time.sleep(DELAY_BETWEEN_CALLS_SECONDS)

    # Call #2: body
    body_prompt = build_prompt_body(subject, topic, topics, tags)
    body = api_infer(body_prompt) or "(Model returned no body text.)"

    # Build tags
    tag_slugs = build_yaml_tags(topics, tags, topic)

    # Render + write
    md = render_markdown(subject, title, topic, topics, tag_slugs, body)
    path = write_note(subject, md)
    return path


def process_file(csv_path: str) -> List[str]:
    outputs: List[str] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        # If it's CSV with multiple columns, take the first; otherwise each line
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            subject = (row[0] or "").strip()
            if not subject or subject.startswith("#"):
                continue
            p = process_subject(subject)
            if p:
                outputs.append(p)
            # batch spacing
            time.sleep(PER_REQUEST_DELAY_SECONDS)
    return outputs


# -------------------------
# CLI
# -------------------------
def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Two-call Obsidian note generator (local API).")
    parser.add_argument("subject", nargs="*", help="Subject text for the note")
    parser.add_argument("--file", "-f", help="Path to a CSV/text file (first column used)")
    args = parser.parse_args(argv)

    ensure_dir(NOTES_DIR)

    if args.file:
        paths = process_file(args.file)
        for p in paths:
            print(f"Created → {p}")
        return 0

    subject = " ".join(args.subject).strip()
    if not subject:
        parser.print_help()
        return 2

    p = process_subject(subject)
    if p:
        print(f"Created → {p}")
        return 0
    print("Nothing created (empty subject?)")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except urllib.error.URLError as e:
        print(f"[Network error] Could not reach API at {API_URL}: {e}", file=sys.stderr)
        sys.exit(3)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)