#!/usr/bin/env python3
"""Extract Korean vocabulary from SNU Anki deck into local SQLite DB."""

import os
import re
import shutil
import sqlite3
import zipfile
import json
from html.parser import HTMLParser

APKG_PATH = os.path.expanduser("~/Downloads/Seoul_National_University_SNU_Korean_Series_level_1-6.apkg")
EXTRACT_DIR = "/tmp/anki_extract"
DB_PATH = os.path.expanduser("~/Projects/korean-vocab/vocab.db")
FIELD_SEP = "\x1f"


class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return "".join(self.fed)


def strip_html(text):
    if not text:
        return ""
    s = HTMLStripper()
    s.feed(text)
    result = s.get_data()
    # Normalize whitespace and HTML entities
    result = result.replace("\xa0", " ").replace("&nbsp;", " ")
    result = re.sub(r"\s+", " ", result).strip()
    return result


def extract_apkg():
    if os.path.exists(EXTRACT_DIR):
        shutil.rmtree(EXTRACT_DIR)
    os.makedirs(EXTRACT_DIR)
    print(f"Extracting {APKG_PATH} ...")
    with zipfile.ZipFile(APKG_PATH, "r") as z:
        z.extractall(EXTRACT_DIR)
    print(f"Extracted to {EXTRACT_DIR}")


def get_model_map(anki_db):
    """Build a map of mid -> model_name from the col table."""
    cur = anki_db.cursor()
    cur.execute("SELECT models FROM col LIMIT 1")
    row = cur.fetchone()
    if not row:
        return {}
    models_json = row[0]
    models = json.loads(models_json)
    model_map = {}
    for mid, model in models.items():
        model_map[int(mid)] = model.get("name", "")
    return model_map


def parse_notes(anki_db, model_map):
    """Parse all notes and return list of (korean, english, tags)."""
    cur = anki_db.cursor()
    cur.execute("SELECT mid, flds, tags FROM notes")
    rows = cur.fetchall()

    vocab = []
    skipped = 0

    for mid, flds, tags in rows:
        fields = flds.split(FIELD_SEP)
        model_name = model_map.get(int(mid), "").lower()

        tags = tags.strip()

        if "language" in model_name:
            # field[0]=korean, field[1]=audio, field[2]=english
            korean = strip_html(fields[0]) if len(fields) > 0 else ""
            english = strip_html(fields[2]) if len(fields) > 2 else ""
        else:
            # Basic: field[0]=front (korean), field[1]=back (english)
            korean = strip_html(fields[0]) if len(fields) > 0 else ""
            english = strip_html(fields[1]) if len(fields) > 1 else ""

        # Skip if either is empty or if korean looks like pure HTML/audio
        if not korean or not english:
            skipped += 1
            continue

        # Skip entries that are just audio tags or numbers with no Korean
        if not any("\uac00" <= c <= "\ud7a3" or "\u3131" <= c <= "\u318e" for c in korean):
            skipped += 1
            continue

        vocab.append((korean, english, tags))

    print(f"Parsed {len(vocab)} valid notes, skipped {skipped}")
    return vocab


def build_local_db(vocab):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vocab (
            id INTEGER PRIMARY KEY,
            korean TEXT,
            english TEXT,
            tags TEXT,
            memorized INTEGER DEFAULT 0,
            last_shown INTEGER DEFAULT 0
        )
    """)

    # Only insert new records (preserve memorized status on re-run)
    cur.execute("SELECT korean FROM vocab")
    existing = {row[0] for row in cur.fetchall()}

    inserted = 0
    for korean, english, tags in vocab:
        if korean not in existing:
            cur.execute(
                "INSERT INTO vocab (korean, english, tags) VALUES (?, ?, ?)",
                (korean, english, tags),
            )
            inserted += 1

    conn.commit()
    total = cur.execute("SELECT COUNT(*) FROM vocab").fetchone()[0]
    conn.close()
    print(f"Inserted {inserted} new records. Total in DB: {total}")


def main():
    extract_apkg()

    anki_db_path = os.path.join(EXTRACT_DIR, "collection.anki21")
    if not os.path.exists(anki_db_path):
        # Try .anki2
        anki_db_path = os.path.join(EXTRACT_DIR, "collection.anki2")

    print(f"Opening Anki DB: {anki_db_path}")
    anki_db = sqlite3.connect(anki_db_path)

    model_map = get_model_map(anki_db)
    print(f"Found {len(model_map)} note models: {list(model_map.values())}")

    vocab = parse_notes(anki_db, model_map)
    anki_db.close()

    build_local_db(vocab)
    print(f"\nDone! vocab.db saved to {DB_PATH}")


if __name__ == "__main__":
    main()
