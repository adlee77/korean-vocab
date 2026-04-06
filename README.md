# 한국어 단어 학습 · Korean Vocabulary App

A flashcard app for the SNU (Seoul National University) Korean Series levels 1–6.
Built as a static HTML/CSS/JS app backed by Supabase for auth and data storage.
Deployable to Netlify with zero build steps.

---

## Supabase Setup

### 1. Create tables

In the [Supabase SQL editor](https://app.supabase.com), open your project and run **schema.sql**:

```sql
-- paste contents of schema.sql
```

### 2. Seed vocabulary

Run **seed.sql** in the same SQL editor (may need to split into batches if the editor times out).
This inserts all 2,877 vocabulary words from the SNU Korean Series.

---

## Netlify Deploy

1. Push this repo to GitHub.
2. Go to [Netlify](https://app.netlify.com) → **Add new site** → **Import from Git**.
3. Select the repo. Build settings are auto-detected from `netlify.toml`:
   - **Publish directory:** `.` (repo root)
   - No build command needed.
4. Deploy.

The app is a single `index.html` file — no build step, no dependencies beyond the Supabase JS SDK loaded from CDN.

---

## How It Works

### Flashcards
- Shows one Korean word at a time; tap/click (or press Space/→) to reveal the English
- **Got it ✓** — marks the word as memorized (won't show again until reset); also press Enter
- **Next →** — skips without marking
- Filter by level (1A · 1B · 2A · 2B · 3 · 4) and word type (Vocab · Grammar · Phrases)
- Progress bar tracks memorized / total for the active filter
- Words shuffle randomly, weighted toward least-recently-seen this session

### Word Management
- Browse all 2,877 words with search and filter
- **Hide** — removes a word from your deck (reversible)
- **Restore** — brings it back
- **Unmemorize** — resets a word to the active rotation

### Auth
- Email/password auth via Supabase Auth
- Each user's progress is stored separately in `user_progress` and `user_deleted`

---

## Files

| File | Description |
|------|-------------|
| `index.html` | The entire app — HTML, CSS, and JS |
| `schema.sql` | Supabase table definitions and RLS policies |
| `seed.sql` | INSERT statements for all vocabulary words |
| `netlify.toml` | Netlify deploy config |
| `vocab.json` | Source vocabulary data (reference only) |
