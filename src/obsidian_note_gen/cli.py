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
import urllib.request
import urllib.error
from typing import List

API_URL = os.environ.get("API_URL", "http://192.168.50.4:8787/infer")
NOTES_DIR = os.environ.get("NOTES_DIR", os.path.expanduser("~/Notes"))
PER_REQUEST_DELAY_SECONDS = int(os.environ.get("PER_REQUEST_DELAY_SECONDS", "120"))
DELAY_BETWEEN_CALLS_SECONDS = int(os.environ.get("DELAY_BETWEEN_CALLS_SECONDS", "30"))

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


def iso_now():
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")


def slug_file(s):
    return (
        re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-"))
        or "note"
    )


def slug_tag(s):
    return re.sub(
        r"-{2,}",
        "-",
        re.sub(
            r"[^a-z0-9]+", "-", s.lower().replace("&", " and ").replace("+", " and ")
        ).strip("-"),
    )


def escape_yaml(s):
    return s.replace('"', '\\"')


def first_token_word(s):
    tok = re.sub(r"[^A-Za-z0-9]+", " ", s).strip().split()
    return tok[0].lower() if tok else "topic"


def ensure_dir(p):
    os.makedirs(p, exist_ok=True)


def atomic_write(path: str, data: str):
    ensure_dir(os.path.dirname(path))
    base = os.path.basename(path)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=f"{base}.",
        dir=os.path.dirname(path),
        delete=False,
    ) as tf:
        tf.write(data)
        tmp = tf.name
    os.replace(tmp, path)


def http_json_post(url: str, payload: dict, timeout: int = 120) -> dict:
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
    env = http_json_post(API_URL, {"prompt": prompt})
    out = env.get("output", "")
    return out if isinstance(out, str) else json.dumps(out)


def build_prompt_meta(subject: str) -> str:
    return f"""You will ONLY return strict JSON. No markdown or extra text.

Subject: {subject}

TASK:
1) "title": a concise title.
2) "topic": a ONE-WORD topic (no spaces).
3) "topics": pick 2–4 distinct items from TOPICS (exact string match; avoid near-duplicates).
4) "tags": 1–3 short extra tags (1–2 words each), semantically distinct from "topics".

TOPICS = {json.dumps(TOPIC_LIST)}

OUTPUT:
{{
  "title": "Concise Title",
  "topic": "OneWordTopic",
  "topics": ["Item from TOPICS", "..."],
  "tags": ["short-tag-1", "short-tag-2"]
}}"""


def build_prompt_body(
    subject: str, one_word_topic: str, topics: list[str], tags: list[str]
) -> str:
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


def parse_meta_output(raw: str):
    try:
        o = json.loads(raw)
        return (
            o.get("title", ""),
            o.get("topic", ""),
            list(o.get("topics", [])),
            list(o.get("tags", [])),
        )
    except Exception:
        return "", "", [], []


def sanitize_topics(tops: list[str]) -> list[str]:
    out = []
    seen = set()
    for t in tops:
        if t in TOPIC_LIST and t not in seen:
            out.append(t)
            seen.add(t)
        if len(out) >= 4:
            break
    return out


def fallback_topic_for_subject(subject: str) -> str:
    s = subject.lower()
    checks = [
        (
            ("ai", "llm", "data", "internet", "comput", "info"),
            "Computers & Information",
        ),
        (("philosophy", "ethic", "logic", "epistem"), "Philosophy"),
        (
            ("psychology", "adhd", "mental", "therapy", "self-help"),
            "Psychology & Self-Help",
        ),
        (("religion", "spiritual", "theolog", "mytholog"), "Religion & Spirituality"),
        (("sociolog", "anthropolog", "culture", "gender"), "Social Sciences"),
        (
            ("politic", "policy", "government", "law", "election"),
            "Politics & Government",
        ),
        (
            ("business", "startup", "market", "econom", "finance", "invest"),
            "Economics & Business",
        ),
        (("education", "teaching", "curriculum", "pedagog"), "Education & Teaching"),
        (("linguist", "grammar", "language", "translate"), "Language & Linguistics"),
        (("science", "scientific method"), "Science (General)"),
        (("math", "algebra", "calculus", "statistic"), "Mathematics"),
        (("physics", "astronomy", "cosmo", "quantum"), "Physics & Astronomy"),
        (("chemistry", "chemical", "compound", "reagent"), "Chemistry"),
        (("biology", "genetic", "zoolog", "ecolog", "flora", "fauna"), "Biology"),
        (("medicine", "health", "clinic", "nutrition", "sleep"), "Medicine & Health"),
        (
            ("engineer", "robotic", "civil", "electrical", "mechanical", "technology"),
            "Engineering & Technology",
        ),
        (("art", "design", "photo", "architec"), "Arts & Design"),
        (
            ("literature", "writing", "poetry", "novel", "criticism"),
            "Literature & Writing",
        ),
        (("history", "geograph", "cartograph", "histor"), "History & Geography"),
        (("travel", "touris", "hobby", "sport", "recreat"), "Travel & Recreation"),
    ]
    for needles, label in checks:
        if any(n in s for n in needles):
            return label
    return "Computers & Information"


def build_yaml_tags(
    topics: list[str], extra_tags: list[str], topic_word: str
) -> list[str]:
    vals = [*topics, *extra_tags]
    slugs = []
    seen = set()
    for v in vals:
        sv = slug_tag(str(v))
        if sv and sv not in seen:
            slugs.append(sv)
            seen.add(sv)
    return slugs or [slug_tag(topic_word or "topic")]


def render_markdown(subject, title, one_word_topic, topics, tag_slugs, body) -> str:
    now = iso_now()
    title_esc = escape_yaml(title or subject)
    topics_json = json.dumps(topics, ensure_ascii=False)
    yaml_tags = ", ".join(tag_slugs)
    front = (
        f"---\n"
        f'title: "{title_esc}"\n'
        f'created: "{now}"\n'
        f'topic: "{one_word_topic or first_token_word(subject)}"\n'
        f"topics: {topics_json}\n"
        f"tags: [{yaml_tags}]\n"
        f"---\n\n"
    )
    return front + (body or "").rstrip() + "\n"


def write_note(subject: str, content: str) -> str:
    notes_dir = os.environ.get("NOTES_DIR", NOTES_DIR)
    path = os.path.join(notes_dir, slug_file(subject) + ".md")
    atomic_write(path, content)
    return path


def process_subject(subject: str) -> str | None:
    subject = subject.strip()
    if not subject:
        return None
    meta_raw = api_infer(build_prompt_meta(subject))
    title, topic, topics, tags = parse_meta_output(meta_raw)
    if not title:
        title = subject
    if not topic or " " in topic:
        topic = first_token_word(subject)
    topics = sanitize_topics(topics) or [fallback_topic_for_subject(subject)]
    time.sleep(int(os.environ.get("DELAY_BETWEEN_CALLS_SECONDS", "30")))
    body = (
        api_infer(build_prompt_body(subject, topic, topics, tags))
        or "(Model returned no body text.)"
    )
    tag_slugs = build_yaml_tags(topics, tags, topic)
    md = render_markdown(subject, title, topic, topics, tag_slugs, body)
    return write_note(subject, md)


def process_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        first = True
        for row in reader:
            if not row:
                continue
            subj = (row[0] or "").strip()
            if not subj or subj.startswith("#"):
                continue
            p = process_subject(subj)
            if p:
                print(f"Created → {p}")
            if not first:
                time.sleep(int(os.environ.get("PER_REQUEST_DELAY_SECONDS", "120")))
            first = False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Two-call Obsidian note generator")
    ap.add_argument("subject", nargs="*", help="Subject")
    ap.add_argument("--file", "-f", help="CSV/text (first column used)")
    args = ap.parse_args(argv)
    notes_dir = os.environ.get("NOTES_DIR", NOTES_DIR)
    os.makedirs(notes_dir, exist_ok=True)
    if args.file:
        process_file(args.file)
        return 0
    subject = " ".join(args.subject).strip()
    if not subject:
        ap.print_help()
        return 2
    p = process_subject(subject)
    if p:
        print(f"Created → {p}")
    else:
        print("No output")
    return 0


if __name__ == "__main__":
    sys.exit(main())
