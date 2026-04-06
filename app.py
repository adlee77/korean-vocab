#!/usr/bin/env python3
"""Korean vocabulary flashcard app."""

import os
import random
import sqlite3
import time
from functools import wraps

from flask import Flask, jsonify, render_template_string, request, session, redirect, url_for, flash
import hashlib

def generate_password_hash(password):
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260000)
    return f"pbkdf2:sha256:{salt}:{h.hex()}"

def check_password_hash(stored, password):
    try:
        _, _, salt, h = stored.split(':', 3)
        check = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260000)
        return check.hex() == h
    except Exception:
        return False
import secrets

DB_PATH = os.path.expanduser("~/Projects/korean-vocab/vocab.db")
SECRET_KEY_PATH = os.path.expanduser("~/Projects/korean-vocab/.secret_key")

app = Flask(__name__)

# Load or generate secret key
if os.path.exists(SECRET_KEY_PATH):
    with open(SECRET_KEY_PATH, "r") as f:
        app.secret_key = f.read().strip()
else:
    key = secrets.token_hex(32)
    with open(SECRET_KEY_PATH, "w") as f:
        f.write(key)
    app.secret_key = key


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at INTEGER DEFAULT (strftime('%s','now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_progress (
            user_id INTEGER NOT NULL,
            vocab_id INTEGER NOT NULL,
            memorized INTEGER DEFAULT 0,
            last_shown INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, vocab_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    try:
        conn.execute("ALTER TABLE vocab ADD COLUMN word_type TEXT")
    except sqlite3.OperationalError:
        pass
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_deleted (
            user_id INTEGER NOT NULL,
            vocab_id INTEGER NOT NULL,
            deleted_at INTEGER DEFAULT (strftime('%s','now')),
            PRIMARY KEY (user_id, vocab_id)
        )
    """)
    conn.commit()
    conn.close()


def migrate_andrews_progress():
    conn = get_db()
    row = conn.execute("SELECT id FROM users WHERE email=?", ("andrewimg@gmail.com",)).fetchone()
    if not row:
        conn.close()
        return
    user_id = row["id"]
    already = conn.execute(
        "SELECT COUNT(*) FROM user_progress WHERE user_id=? AND memorized=1", (user_id,)
    ).fetchone()[0]
    expected = conn.execute("SELECT COUNT(*) FROM vocab WHERE memorized=1").fetchone()[0]
    if already >= expected:
        conn.close()
        return
    # Copy memorized words from vocab table into user_progress
    memorized_rows = conn.execute(
        "SELECT id, last_shown FROM vocab WHERE memorized=1"
    ).fetchall()
    for v in memorized_rows:
        conn.execute(
            "INSERT OR IGNORE INTO user_progress (user_id, vocab_id, memorized, last_shown) VALUES (?,?,1,?)",
            (user_id, v["id"], v["last_shown"]),
        )
    conn.commit()
    conn.close()


def migrate_word_types():
    conn = get_db()
    conn.execute('UPDATE vocab SET word_type = "grammar" WHERE tags LIKE "%Korean_grammar%"')
    conn.execute(
        'UPDATE vocab SET word_type = "phrase" WHERE word_type IS NULL AND '
        '(tags LIKE "%Korean_pattern_practice%" OR tags LIKE "%Korean_plain_polite%" '
        'OR tags LIKE "%Korean_formal_polite%" OR tags LIKE "%Korean_intimate%")'
    )
    conn.execute('UPDATE vocab SET word_type = "vocab" WHERE word_type IS NULL')
    conn.commit()
    conn.close()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sign In · Korean Vocab</title>
<style>
  :root {
    --navy: #0d1b2e; --navy-light: #1e3352; --gold: #c9a84c; --gold-light: #e8c97a;
    --white: #f0f4ff; --muted: #8899bb; --card-bg: #162340; --card-border: #1e3a5f; --radius: 16px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--navy); color: var(--white); min-height: 100vh;
    display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px 16px;
  }
  h1 { font-size: 1.6rem; font-weight: 700; color: var(--gold-light); margin-bottom: 8px; text-align: center; }
  .subtitle { color: var(--muted); font-size: 0.9rem; text-align: center; margin-bottom: 28px; }
  .card {
    background: var(--card-bg); border: 1px solid var(--card-border); border-radius: var(--radius);
    padding: 36px 32px; width: 100%; max-width: 400px;
  }
  .flash { padding: 10px 14px; border-radius: 8px; margin-bottom: 18px; font-size: 0.88rem; font-weight: 500; }
  .flash-error { background: rgba(224,82,82,0.15); border: 1px solid rgba(224,82,82,0.4); color: #e08080; }
  .flash-success { background: rgba(201,168,76,0.15); border: 1px solid rgba(201,168,76,0.4); color: var(--gold-light); }
  label { display: block; font-size: 0.82rem; color: var(--muted); margin-bottom: 6px; font-weight: 500; letter-spacing: 0.04em; }
  input {
    width: 100%; padding: 12px 14px; background: var(--navy-light); border: 1px solid var(--card-border);
    border-radius: 10px; color: var(--white); font-size: 0.97rem; outline: none;
    transition: border-color 0.15s; margin-bottom: 18px;
  }
  input:focus { border-color: var(--gold); }
  button[type=submit] {
    width: 100%; padding: 14px; background: var(--gold); color: var(--navy); border: none;
    border-radius: var(--radius); font-size: 1rem; font-weight: 700; cursor: pointer; transition: background 0.15s;
  }
  button[type=submit]:hover { background: var(--gold-light); }
  .link { text-align: center; margin-top: 18px; font-size: 0.85rem; color: var(--muted); }
  .link a { color: var(--gold); text-decoration: none; }
  .link a:hover { color: var(--gold-light); }
</style>
</head>
<body>
<h1>한국어 단어 학습</h1>
<p class="subtitle">Sign in to track your progress</p>
<div class="card">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}
      <div class="flash flash-{{ cat }}">{{ msg }}</div>
    {% endfor %}
  {% endwith %}
  <form method="POST" action="/login">
    <label>Email</label>
    <input type="email" name="email" required autocomplete="email" placeholder="you@example.com">
    <label>Password</label>
    <input type="password" name="password" required autocomplete="current-password" placeholder="••••••••">
    <button type="submit">Sign In</button>
  </form>
  <div class="link">Don't have an account? <a href="/register">Register</a></div>
</div>
</body>
</html>"""

REGISTER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Register · Korean Vocab</title>
<style>
  :root {
    --navy: #0d1b2e; --navy-light: #1e3352; --gold: #c9a84c; --gold-light: #e8c97a;
    --white: #f0f4ff; --muted: #8899bb; --card-bg: #162340; --card-border: #1e3a5f; --radius: 16px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--navy); color: var(--white); min-height: 100vh;
    display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px 16px;
  }
  h1 { font-size: 1.6rem; font-weight: 700; color: var(--gold-light); margin-bottom: 8px; text-align: center; }
  .subtitle { color: var(--muted); font-size: 0.9rem; text-align: center; margin-bottom: 28px; }
  .card {
    background: var(--card-bg); border: 1px solid var(--card-border); border-radius: var(--radius);
    padding: 36px 32px; width: 100%; max-width: 400px;
  }
  .flash { padding: 10px 14px; border-radius: 8px; margin-bottom: 18px; font-size: 0.88rem; font-weight: 500; }
  .flash-error { background: rgba(224,82,82,0.15); border: 1px solid rgba(224,82,82,0.4); color: #e08080; }
  .flash-success { background: rgba(201,168,76,0.15); border: 1px solid rgba(201,168,76,0.4); color: var(--gold-light); }
  label { display: block; font-size: 0.82rem; color: var(--muted); margin-bottom: 6px; font-weight: 500; letter-spacing: 0.04em; }
  input {
    width: 100%; padding: 12px 14px; background: var(--navy-light); border: 1px solid var(--card-border);
    border-radius: 10px; color: var(--white); font-size: 0.97rem; outline: none;
    transition: border-color 0.15s; margin-bottom: 18px;
  }
  input:focus { border-color: var(--gold); }
  button[type=submit] {
    width: 100%; padding: 14px; background: var(--gold); color: var(--navy); border: none;
    border-radius: var(--radius); font-size: 1rem; font-weight: 700; cursor: pointer; transition: background 0.15s;
  }
  button[type=submit]:hover { background: var(--gold-light); }
  .link { text-align: center; margin-top: 18px; font-size: 0.85rem; color: var(--muted); }
  .link a { color: var(--gold); text-decoration: none; }
  .link a:hover { color: var(--gold-light); }
</style>
</head>
<body>
<h1>한국어 단어 학습</h1>
<p class="subtitle">Create an account to get started</p>
<div class="card">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}
      <div class="flash flash-{{ cat }}">{{ msg }}</div>
    {% endfor %}
  {% endwith %}
  <form method="POST" action="/register">
    <label>Email</label>
    <input type="email" name="email" required autocomplete="email" placeholder="you@example.com">
    <label>Password</label>
    <input type="password" name="password" required autocomplete="new-password" placeholder="••••••••">
    <label>Confirm Password</label>
    <input type="password" name="confirm" required autocomplete="new-password" placeholder="••••••••">
    <button type="submit">Create Account</button>
  </form>
  <div class="link">Already have an account? <a href="/login">Sign in</a></div>
</div>
</body>
</html>"""

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>한국어 단어 학습 · Korean Vocab</title>
<style>
  :root {
    --navy: #0d1b2e;
    --navy-mid: #132338;
    --navy-light: #1e3352;
    --gold: #c9a84c;
    --gold-light: #e8c97a;
    --gold-dim: #7a6130;
    --white: #f0f4ff;
    --muted: #8899bb;
    --card-bg: #162340;
    --card-border: #1e3a5f;
    --success: #4caf79;
    --success-dim: #2d7a50;
    --review: #e05252;
    --review-dim: #8a3030;
    --radius: 16px;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--navy);
    color: var(--white);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 24px 16px;
  }

  header {
    text-align: center;
    margin-bottom: 20px;
  }

  header h1 {
    font-size: 1.6rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    color: var(--gold-light);
  }

  header h1 span {
    color: var(--muted);
    font-size: 1rem;
    font-weight: 400;
    display: block;
    margin-top: 4px;
  }

  .user-bar {
    margin-top: 10px;
    font-size: 0.78rem;
    color: var(--muted);
  }

  .user-bar a {
    color: var(--muted);
    text-decoration: underline;
    margin-left: 10px;
  }

  .user-bar a:hover {
    color: var(--gold);
  }

  /* Level filter */
  .filter-wrap {
    display: flex;
    gap: 8px;
    margin-bottom: 10px;
    flex-wrap: wrap;
    justify-content: center;
    width: 100%;
    max-width: 520px;
  }

  .filter-wrap:last-of-type {
    margin-bottom: 24px;
  }

  .filter-btn {
    padding: 6px 16px;
    border-radius: 100px;
    border: 1px solid var(--card-border);
    background: var(--navy-light);
    color: var(--muted);
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
    letter-spacing: 0.04em;
  }

  .filter-btn:hover {
    border-color: var(--gold-dim);
    color: var(--gold-light);
  }

  .filter-btn.active {
    background: var(--gold-dim);
    border-color: var(--gold);
    color: var(--gold-light);
  }

  /* Progress bar */
  .progress-wrap {
    width: 100%;
    max-width: 520px;
    margin-bottom: 28px;
  }

  .progress-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.78rem;
    color: var(--muted);
    margin-bottom: 8px;
  }

  .progress-label strong {
    color: var(--gold);
  }

  .progress-bar {
    background: var(--navy-light);
    border-radius: 100px;
    height: 8px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--gold-dim), var(--gold));
    border-radius: 100px;
    transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  }

  /* Card */
  .card-container {
    width: 100%;
    max-width: 520px;
    perspective: 1200px;
  }

  .card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: var(--radius);
    padding: 48px 36px;
    text-align: center;
    cursor: pointer;
    min-height: 260px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    position: relative;
    user-select: none;
  }

  .card:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.5);
  }

  .card:active {
    transform: translateY(0);
  }

  .card-level {
    position: absolute;
    top: 16px;
    right: 18px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--gold-dim);
    background: rgba(201,168,76,0.1);
    border: 1px solid rgba(201,168,76,0.2);
    padding: 3px 10px;
    border-radius: 100px;
  }

  .card-front {
    font-size: 3.2rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: var(--white);
    line-height: 1.2;
  }

  .card-hint {
    margin-top: 16px;
    font-size: 0.82rem;
    color: var(--muted);
    opacity: 0.7;
  }

  .card-back {
    margin-top: 20px;
    font-size: 1.25rem;
    color: var(--gold-light);
    font-weight: 500;
    opacity: 0;
    transform: translateY(8px);
    transition: opacity 0.3s ease, transform 0.3s ease;
    max-width: 380px;
    line-height: 1.5;
  }

  .card.revealed .card-back {
    opacity: 1;
    transform: translateY(0);
  }

  .card.revealed .card-hint {
    display: none;
  }

  .card-divider {
    width: 48px;
    height: 2px;
    background: var(--card-border);
    border-radius: 2px;
    margin: 18px auto 0;
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  .card.revealed .card-divider {
    opacity: 1;
  }

  /* Buttons */
  .actions {
    display: flex;
    gap: 12px;
    margin-top: 24px;
    width: 100%;
    max-width: 520px;
    opacity: 0;
    transform: translateY(10px);
    transition: opacity 0.3s ease, transform 0.3s ease;
    pointer-events: none;
  }

  .actions.visible {
    opacity: 1;
    transform: translateY(0);
    pointer-events: all;
  }

  .btn {
    flex: 1;
    padding: 15px 20px;
    border-radius: var(--radius);
    border: none;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s, transform 0.12s;
    letter-spacing: 0.01em;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }

  .btn:active { transform: scale(0.97); }

  .btn-got-it {
    background: var(--success);
    color: #fff;
  }

  .btn-got-it:hover { background: #5bc88a; }

  .btn-review {
    background: var(--navy-light);
    color: var(--white);
    border: 1px solid var(--card-border);
  }

  .btn-review:hover { background: #243d5e; }

  /* Completion screen */
  .completion {
    text-align: center;
    padding: 48px 24px;
  }

  .completion .trophy {
    font-size: 5rem;
    margin-bottom: 20px;
    display: block;
  }

  .completion h2 {
    font-size: 2rem;
    color: var(--gold-light);
    margin-bottom: 12px;
  }

  .completion p {
    color: var(--muted);
    font-size: 1rem;
    margin-bottom: 28px;
  }

  .btn-reset {
    background: var(--gold);
    color: var(--navy);
    padding: 14px 36px;
    border-radius: var(--radius);
    border: none;
    font-size: 1rem;
    font-weight: 700;
    cursor: pointer;
    transition: background 0.15s;
  }

  .btn-reset:hover { background: var(--gold-light); }

  /* Loading */
  .loading {
    color: var(--muted);
    font-size: 1rem;
    margin-top: 60px;
  }

  /* Fade transition */
  .fade-out { animation: fadeOut 0.2s ease forwards; }
  .fade-in  { animation: fadeIn  0.3s ease forwards; }

  @keyframes fadeOut { to { opacity: 0; transform: scale(0.97); } }
  @keyframes fadeIn  { from { opacity: 0; transform: scale(0.97); } to { opacity: 1; transform: scale(1); } }
</style>
</head>
<body>

<header>
  <h1>한국어 단어 학습<span>Korean Vocabulary · SNU Series</span></h1>
  <div class="user-bar">{{ user_email }}<a href="/settings/words">Manage Words</a><a href="/logout">Logout</a></div>
</header>

<div class="filter-wrap" id="filter-wrap">
  <button class="filter-btn active" data-level="all" onclick="setFilter('all')">All</button>
  <button class="filter-btn" data-level="1A" onclick="setFilter('1A')">SNU 1A</button>
  <button class="filter-btn" data-level="1B" onclick="setFilter('1B')">SNU 1B</button>
  <button class="filter-btn" data-level="2A" onclick="setFilter('2A')">SNU 2A</button>
  <button class="filter-btn" data-level="2B" onclick="setFilter('2B')">SNU 2B</button>
</div>

<div class="filter-wrap" id="type-filter-wrap">
  <button class="filter-btn active" data-type="all" onclick="setTypeFilter('all')">All Types</button>
  <button class="filter-btn" data-type="vocab" onclick="setTypeFilter('vocab')">Vocab</button>
  <button class="filter-btn" data-type="grammar" onclick="setTypeFilter('grammar')">Grammar</button>
  <button class="filter-btn" data-type="phrase" onclick="setTypeFilter('phrase')">Phrases</button>
</div>

<div class="progress-wrap">
  <div class="progress-label">
    <span>Progress</span>
    <span><strong id="prog-mem">0</strong> / <span id="prog-total">0</span> memorized</span>
  </div>
  <div class="progress-bar">
    <div class="progress-fill" id="prog-fill" style="width:0%"></div>
  </div>
</div>

<div class="card-container" id="card-container">
  <div class="loading">Loading vocabulary...</div>
</div>

<div class="actions" id="actions">
  <button class="btn btn-review" onclick="submitAnswer(false)">Next →</button>
  <button class="btn btn-got-it" onclick="submitAnswer(true)">Got it ✓</button>
</div>

<script>
let currentId = null;
let revealed = false;
let activeFilter = 'all';
let activeType = 'all';

function setFilter(level) {
  activeFilter = level;
  document.querySelectorAll('#filter-wrap .filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.level === level);
  });
  loadCard();
}

function setTypeFilter(type) {
  activeType = type;
  document.querySelectorAll('#type-filter-wrap .filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.type === type);
  });
  loadCard();
}

async function loadCard() {
  revealed = false;
  document.getElementById('actions').classList.remove('visible');

  const params = new URLSearchParams();
  if (activeFilter !== 'all') params.set('level', activeFilter);
  if (activeType !== 'all') params.set('type', activeType);
  const qs = params.toString();
  const url = qs ? `/api/next?${qs}` : '/api/next';
  const res = await fetch(url);
  const data = await res.json();

  updateProgress(data.memorized, data.total);

  const container = document.getElementById('card-container');

  if (data.done) {
    const filterLabel = activeFilter === 'all' ? 'all' : `SNU ${activeFilter}`;
    container.innerHTML = `
      <div class="completion fade-in">
        <span class="trophy">🏆</span>
        <h2>완료! All Done!</h2>
        <p>You've memorized all <strong>${data.total}</strong> ${filterLabel} words.<br>Amazing work — 잘했어요!</p>
        <button class="btn-reset" onclick="resetFilter()">Start Over</button>
      </div>`;
    return;
  }

  currentId = data.id;

  const levelTag = extractLevel(data.tags);

  container.innerHTML = `
    <div class="card fade-in" id="card" onclick="revealCard()">
      ${levelTag ? `<div class="card-level">${levelTag}</div>` : ''}
      <div class="card-front">${escHtml(data.korean)}</div>
      <div class="card-divider"></div>
      <div class="card-back">${escHtml(data.english)}</div>
      <div class="card-hint">tap to reveal · space=next · enter=got it</div>
    </div>`;
}

function revealCard() {
  if (revealed) return;
  revealed = true;
  const card = document.getElementById('card');
  card.classList.add('revealed');
  document.getElementById('actions').classList.add('visible');
}

document.addEventListener('keydown', (e) => {
  if (e.key === ' ' || e.key === 'ArrowRight') {
    e.preventDefault();
    if (!revealed) revealCard();
    else submitAnswer(false);
  } else if (e.key === 'Enter') {
    e.preventDefault();
    if (!revealed) revealCard();
    else submitAnswer(true);
  }
});

async function submitAnswer(memorized) {
  if (!currentId) return;
  const card = document.getElementById('card');
  if (card) card.classList.add('fade-out');

  await fetch('/api/answer', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({id: currentId, memorized})
  });

  setTimeout(loadCard, 200);
}

async function resetFilter() {
  const level = activeFilter === 'all' ? null : activeFilter;
  await fetch('/api/reset', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({level})
  });
  loadCard();
}

function updateProgress(mem, total) {
  document.getElementById('prog-mem').textContent = mem;
  document.getElementById('prog-total').textContent = total;
  const pct = total > 0 ? (mem / total * 100) : 0;
  document.getElementById('prog-fill').style.width = pct + '%';
}

function extractLevel(tags) {
  if (!tags) return '';
  const m = tags.match(/SNU\\.lvl\\.(\\d[AB]?)/i);
  if (m) return 'SNU Lv.' + m[1].toUpperCase();
  const m2 = tags.match(/level[_\\s-]?(\\d)/i);
  if (m2) return 'Level ' + m2[1];
  return '';
}

function escHtml(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

loadCard();
</script>
</body>
</html>
"""

SETTINGS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Word Management · Korean Vocab</title>
<style>
  :root {
    --navy: #0d1b2e; --navy-mid: #132338; --navy-light: #1e3352;
    --gold: #c9a84c; --gold-light: #e8c97a; --gold-dim: #7a6130;
    --white: #f0f4ff; --muted: #8899bb;
    --card-bg: #162340; --card-border: #1e3a5f; --radius: 16px;
    --success: #4caf79; --blue: #4c8fcf; --purple: #9b6fc9;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--navy); color: var(--white); min-height: 100vh; padding: 24px 16px;
  }
  header {
    display: flex; align-items: center; justify-content: space-between;
    max-width: 900px; margin: 0 auto 24px; flex-wrap: wrap; gap: 12px;
  }
  header h1 { font-size: 1.4rem; font-weight: 700; color: var(--gold-light); }
  .header-links { display: flex; gap: 16px; font-size: 0.82rem; }
  .header-links a { color: var(--muted); text-decoration: underline; }
  .header-links a:hover { color: var(--gold); }
  .stats {
    max-width: 900px; margin: 0 auto 20px;
    font-size: 0.85rem; color: var(--muted);
  }
  .stats span { margin-right: 16px; }
  .stats strong { color: var(--gold); }
  .controls {
    max-width: 900px; margin: 0 auto 16px; display: flex; flex-direction: column; gap: 10px;
  }
  .search-input {
    width: 100%; padding: 10px 14px; background: var(--card-bg);
    border: 1px solid var(--card-border); border-radius: 10px;
    color: var(--white); font-size: 0.95rem; outline: none; transition: border-color 0.15s;
  }
  .search-input:focus { border-color: var(--gold); }
  .filter-row { display: flex; gap: 8px; flex-wrap: wrap; }
  .filter-btn {
    padding: 5px 14px; border-radius: 100px; border: 1px solid var(--card-border);
    background: var(--navy-light); color: var(--muted); font-size: 0.8rem;
    font-weight: 600; cursor: pointer; transition: all 0.15s; letter-spacing: 0.04em;
  }
  .filter-btn:hover { border-color: var(--gold-dim); color: var(--gold-light); }
  .filter-btn.active { background: var(--gold-dim); border-color: var(--gold); color: var(--gold-light); }
  .table-wrap {
    max-width: 900px; margin: 0 auto;
    background: var(--card-bg); border: 1px solid var(--card-border); border-radius: var(--radius);
    overflow: hidden;
  }
  table { width: 100%; border-collapse: collapse; }
  th {
    text-align: left; padding: 12px 16px; font-size: 0.75rem;
    font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase;
    color: var(--muted); border-bottom: 1px solid var(--card-border); background: var(--navy-mid);
  }
  td { padding: 11px 16px; font-size: 0.88rem; border-bottom: 1px solid rgba(30,58,95,0.5); vertical-align: middle; }
  tr:last-child td { border-bottom: none; }
  tr.deleted td { opacity: 0.45; }
  tr.deleted .korean-cell { text-decoration: line-through; }
  .korean-cell { font-size: 1.1rem; font-weight: 600; color: var(--white); }
  .english-cell { color: var(--muted); max-width: 260px; }
  .badge {
    display: inline-block; padding: 2px 9px; border-radius: 100px;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em;
  }
  .badge-vocab { background: rgba(76,143,207,0.2); color: #7db8e8; border: 1px solid rgba(76,143,207,0.35); }
  .badge-grammar { background: rgba(76,175,121,0.2); color: #7dcca0; border: 1px solid rgba(76,175,121,0.35); }
  .badge-phrase { background: rgba(155,111,201,0.2); color: #c09ee0; border: 1px solid rgba(155,111,201,0.35); }
  .badge-level { background: rgba(201,168,76,0.15); color: var(--gold-light); border: 1px solid rgba(201,168,76,0.3); }
  .badge-memorized { background: rgba(201,168,76,0.15); color: var(--gold-light); border: 1px solid rgba(201,168,76,0.3); }
  .actions-cell { display: flex; gap: 6px; flex-wrap: wrap; }
  .act-btn {
    padding: 4px 10px; border-radius: 8px; border: 1px solid var(--card-border);
    background: var(--navy-light); color: var(--muted); font-size: 0.75rem;
    font-weight: 600; cursor: pointer; transition: all 0.15s; white-space: nowrap;
  }
  .act-btn:hover { border-color: var(--gold-dim); color: var(--gold-light); }
  .act-btn.danger:hover { border-color: rgba(224,82,82,0.5); color: #e08080; }
  .act-btn.restore { border-color: rgba(76,175,121,0.4); color: #7dcca0; }
  .act-btn.restore:hover { border-color: var(--success); color: var(--success); }
  .empty { padding: 48px; text-align: center; color: var(--muted); font-size: 0.9rem; }
</style>
</head>
<body>

<header>
  <h1>Word Management</h1>
  <div class="header-links">
    <a href="/">← Back to Flashcards</a>
    <a href="/logout">Logout</a>
  </div>
</header>

<div class="stats" id="stats">Loading...</div>

<div class="controls">
  <input class="search-input" id="search" type="text" placeholder="Search Korean or English…">
  <div class="filter-row" id="type-filters">
    <button class="filter-btn active" data-type="all">All Types</button>
    <button class="filter-btn" data-type="vocab">Vocab</button>
    <button class="filter-btn" data-type="grammar">Grammar</button>
    <button class="filter-btn" data-type="phrase">Phrases</button>
  </div>
  <div class="filter-row" id="level-filters">
    <button class="filter-btn active" data-level="all">All Levels</button>
    <button class="filter-btn" data-level="1A">1A</button>
    <button class="filter-btn" data-level="1B">1B</button>
    <button class="filter-btn" data-level="2A">2A</button>
    <button class="filter-btn" data-level="2B">2B</button>
  </div>
</div>

<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th>Korean</th>
        <th>English</th>
        <th>Type</th>
        <th>Level</th>
        <th>Status</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody id="words-body">
      <tr><td colspan="6" class="empty">Loading words…</td></tr>
    </tbody>
  </table>
</div>

<script>
let allWords = [];
let activeType = 'all';
let activeLevel = 'all';
let searchTerm = '';
let searchTimer = null;

function extractLevel(tags) {
  if (!tags) return '';
  const m = tags.match(/SNU\\.lvl\\.(\\d[AB]?)/i);
  return m ? m[1].toUpperCase() : '';
}

function escHtml(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}

async function loadWords() {
  const res = await fetch('/api/words?per_page=9999');
  const data = await res.json();
  allWords = data.words || [];
  updateStats();
  renderTable();
}

function updateStats() {
  const total = allWords.length;
  const memorized = allWords.filter(w => w.memorized).length;
  const hidden = allWords.filter(w => w.deleted).length;
  document.getElementById('stats').innerHTML =
    `<span><strong>${total}</strong> total</span>` +
    `<span><strong>${memorized}</strong> memorized</span>` +
    `<span><strong>${hidden}</strong> hidden</span>`;
}

function renderTable() {
  const q = searchTerm.toLowerCase();
  const filtered = allWords.filter(w => {
    if (activeType !== 'all' && w.word_type !== activeType) return false;
    if (activeLevel !== 'all') {
      const lvl = extractLevel(w.tags);
      if (lvl !== activeLevel) return false;
    }
    if (q && !w.korean.toLowerCase().includes(q) && !w.english.toLowerCase().includes(q)) return false;
    return true;
  });

  const tbody = document.getElementById('words-body');
  if (!filtered.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty">No words match.</td></tr>';
    return;
  }

  tbody.innerHTML = filtered.map(w => {
    const lvl = extractLevel(w.tags);
    const typeClass = w.word_type === 'grammar' ? 'badge-grammar' : w.word_type === 'phrase' ? 'badge-phrase' : 'badge-vocab';
    const typeLabel = w.word_type || 'vocab';

    let actions = '';
    if (w.deleted) {
      actions = `<button class="act-btn restore" onclick="restoreWord(${w.id})">Restore</button>`;
    } else {
      if (w.memorized) {
        actions += `<button class="act-btn" onclick="unmemorizeWord(${w.id})">Unmemorize</button>`;
      }
      actions += `<button class="act-btn danger" onclick="hideWord(${w.id})">Hide</button>`;
    }

    const statusBadge = w.memorized ? '<span class="badge badge-memorized">Memorized</span>' : '';
    const rowClass = w.deleted ? 'deleted' : '';

    return `<tr class="${rowClass}" id="row-${w.id}">
      <td class="korean-cell">${escHtml(w.korean)}</td>
      <td class="english-cell">${escHtml(w.english)}</td>
      <td><span class="badge ${typeClass}">${escHtml(typeLabel)}</span></td>
      <td>${lvl ? `<span class="badge badge-level">${escHtml(lvl)}</span>` : ''}</td>
      <td>${statusBadge}</td>
      <td><div class="actions-cell">${actions}</div></td>
    </tr>`;
  }).join('');
}

async function hideWord(id) {
  await fetch(`/api/words/${id}/delete`, {method: 'POST'});
  const w = allWords.find(x => x.id === id);
  if (w) w.deleted = 1;
  updateStats();
  renderTable();
}

async function restoreWord(id) {
  await fetch(`/api/words/${id}/restore`, {method: 'POST'});
  const w = allWords.find(x => x.id === id);
  if (w) w.deleted = 0;
  updateStats();
  renderTable();
}

async function unmemorizeWord(id) {
  await fetch(`/api/words/${id}/unmemorize`, {method: 'POST'});
  const w = allWords.find(x => x.id === id);
  if (w) w.memorized = 0;
  updateStats();
  renderTable();
}

document.getElementById('type-filters').addEventListener('click', e => {
  const btn = e.target.closest('.filter-btn');
  if (!btn) return;
  activeType = btn.dataset.type;
  document.querySelectorAll('#type-filters .filter-btn').forEach(b => b.classList.toggle('active', b === btn));
  renderTable();
});

document.getElementById('level-filters').addEventListener('click', e => {
  const btn = e.target.closest('.filter-btn');
  if (!btn) return;
  activeLevel = btn.dataset.level;
  document.querySelectorAll('#level-filters .filter-btn').forEach(b => b.classList.toggle('active', b === btn));
  renderTable();
});

document.getElementById('search').addEventListener('input', e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    searchTerm = e.target.value;
    renderTable();
  }, 200);
});

loadWords();
</script>
</body>
</html>
"""


def level_filter_clause(level):
    """Return a WHERE fragment and params tuple for a given level filter."""
    if not level or level == "all":
        return "", []
    return "AND v.tags LIKE ?", [f"%SNU.lvl.{level}%"]


def type_filter_clause(word_type):
    """Return a WHERE fragment and params tuple for a word_type filter."""
    if not word_type or word_type == "all":
        return "", []
    return "AND v.word_type = ?", [word_type]


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_email"] = user["email"]
            return redirect(url_for("index"))
        flash("Invalid email or password.", "error")
    return render_template_string(LOGIN_HTML)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template_string(REGISTER_HTML)
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template_string(REGISTER_HTML)
        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            conn.close()
            flash("An account with that email already exists.", "error")
            return render_template_string(REGISTER_HTML)
        pw_hash = generate_password_hash(password)
        cur = conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?,?)", (email, pw_hash)
        )
        conn.commit()
        user_id = cur.lastrowid
        conn.close()
        session["user_id"] = user_id
        session["user_email"] = email
        return redirect(url_for("index"))
    return render_template_string(REGISTER_HTML)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template_string(HTML, user_email=session.get("user_email", ""))


@app.route("/api/next")
@login_required
def api_next():
    user_id = session["user_id"]
    level = request.args.get("level", "").strip()
    word_type = request.args.get("type", "").strip()
    lclause, lparams = level_filter_clause(level)
    tclause, tparams = type_filter_clause(word_type)
    filter_clause = f"{lclause} {tclause}".strip()
    filter_params = lparams + tparams

    conn = get_db()
    cur = conn.cursor()

    total = cur.execute(
        f"""SELECT COUNT(*) FROM vocab v
            LEFT JOIN user_deleted ud ON ud.vocab_id = v.id AND ud.user_id = ?
            WHERE ud.vocab_id IS NULL {filter_clause}""",
        [user_id] + filter_params,
    ).fetchone()[0]

    memorized = cur.execute(
        f"""SELECT COUNT(*) FROM user_progress up
            LEFT JOIN vocab v ON v.id = up.vocab_id
            LEFT JOIN user_deleted ud ON ud.vocab_id = v.id AND ud.user_id = ?
            WHERE up.user_id=? AND up.memorized=1 AND ud.vocab_id IS NULL {filter_clause}""",
        [user_id, user_id] + filter_params,
    ).fetchone()[0]

    if total == 0 or memorized == total:
        conn.close()
        return jsonify({"done": True, "memorized": memorized, "total": total})

    rows = cur.execute(
        f"""SELECT v.id, v.korean, v.english, v.tags FROM vocab v
            LEFT JOIN user_progress up ON up.vocab_id = v.id AND up.user_id = ?
            LEFT JOIN user_deleted ud ON ud.vocab_id = v.id AND ud.user_id = ?
            WHERE (up.memorized IS NULL OR up.memorized = 0) AND ud.vocab_id IS NULL {filter_clause}
            ORDER BY COALESCE(up.last_shown, 0) ASC LIMIT 50""",
        [user_id, user_id] + filter_params,
    ).fetchall()
    conn.close()

    if not rows:
        return jsonify({"done": True, "memorized": memorized, "total": total})

    row = random.choice(rows)
    return jsonify({
        "id": row["id"],
        "korean": row["korean"],
        "english": row["english"],
        "tags": row["tags"],
        "memorized": memorized,
        "total": total,
        "done": False,
    })


@app.route("/api/answer", methods=["POST"])
@login_required
def api_answer():
    user_id = session["user_id"]
    data = request.get_json()
    vocab_id = data.get("id")
    memorized = 1 if data.get("memorized") else 0

    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO user_progress (user_id, vocab_id, memorized, last_shown) VALUES (?,?,?,?)",
        (user_id, vocab_id, memorized, int(time.time())),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/reset", methods=["POST"])
@login_required
def api_reset():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    level = data.get("level", "").strip() if data.get("level") else ""

    conn = get_db()
    if not level or level == "all":
        conn.execute("UPDATE user_progress SET memorized=0 WHERE user_id=?", (user_id,))
    else:
        conn.execute(
            """UPDATE user_progress SET memorized=0
               WHERE user_id=? AND vocab_id IN (
                   SELECT id FROM vocab WHERE tags LIKE ?
               )""",
            (user_id, f"%SNU.lvl.{level}%"),
        )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/words")
@login_required
def api_words():
    user_id = session["user_id"]
    search = request.args.get("search", "").strip()
    word_type = request.args.get("type", "").strip()
    level = request.args.get("level", "").strip()
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(9999, max(1, int(request.args.get("per_page", 100))))
    offset = (page - 1) * per_page

    clauses = []
    params = [user_id, user_id]

    if search:
        clauses.append("AND (v.korean LIKE ? OR v.english LIKE ?)")
        params += [f"%{search}%", f"%{search}%"]
    if word_type and word_type != "all":
        clauses.append("AND v.word_type = ?")
        params.append(word_type)
    if level and level != "all":
        clauses.append("AND v.tags LIKE ?")
        params.append(f"%SNU.lvl.{level}%")

    extra = " ".join(clauses)
    params_paged = params + [per_page, offset]

    conn = get_db()
    rows = conn.execute(
        f"""SELECT v.id, v.korean, v.english, v.word_type, v.tags,
                   COALESCE(up.memorized, 0) AS memorized,
                   CASE WHEN ud.vocab_id IS NOT NULL THEN 1 ELSE 0 END AS deleted
            FROM vocab v
            LEFT JOIN user_progress up ON up.vocab_id = v.id AND up.user_id = ?
            LEFT JOIN user_deleted ud ON ud.vocab_id = v.id AND ud.user_id = ?
            WHERE 1=1 {extra}
            ORDER BY v.id ASC
            LIMIT ? OFFSET ?""",
        params_paged,
    ).fetchall()
    conn.close()

    words = [dict(r) for r in rows]
    return jsonify({"words": words})


@app.route("/api/words/<int:vocab_id>/delete", methods=["POST"])
@login_required
def api_word_delete(vocab_id):
    user_id = session["user_id"]
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO user_deleted (user_id, vocab_id) VALUES (?,?)",
        (user_id, vocab_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/words/<int:vocab_id>/restore", methods=["POST"])
@login_required
def api_word_restore(vocab_id):
    user_id = session["user_id"]
    conn = get_db()
    conn.execute(
        "DELETE FROM user_deleted WHERE user_id=? AND vocab_id=?",
        (user_id, vocab_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/words/<int:vocab_id>/unmemorize", methods=["POST"])
@login_required
def api_word_unmemorize(vocab_id):
    user_id = session["user_id"]
    conn = get_db()
    conn.execute(
        "UPDATE user_progress SET memorized=0 WHERE user_id=? AND vocab_id=?",
        (user_id, vocab_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/settings/words")
@login_required
def settings_words():
    return render_template_string(SETTINGS_HTML)


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"ERROR: vocab.db not found at {DB_PATH}")
        print("Run: python3 extract_vocab.py first")
        exit(1)
    init_db()
    migrate_andrews_progress()
    migrate_word_types()
    app.run(host="0.0.0.0", port=5001, debug=False)
