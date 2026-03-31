# 한국어 단어 학습 · Korean Vocabulary App

A flashcard app for the SNU (Seoul National University) Korean Series levels 1–6.

## Setup

### 1. Extract vocabulary

```bash
cd ~/Projects/korean-vocab
python3 extract_vocab.py
```

This reads the Anki deck at `~/Downloads/Seoul_National_University_SNU_Korean_Series_level_1-6.apkg`, extracts all Korean/English pairs, and saves them to `vocab.db`.

> Safe to re-run — memorized status is preserved.

### 2. Run the web app

```bash
python3 app.py
```

Open **http://localhost:5001** in your browser.

Requires Flask:
```bash
pip3 install flask
```

## How It Works

- Shows one Korean word at a time; click the card to reveal the English
- **Got it ✓** — marks the word as memorized (won't show again)
- **Review Again** — keeps it in the rotation
- Progress bar tracks how many words you've memorized
- When all words are memorized, shows a completion screen with option to reset

## Mac Notifications (every 30 min)

### Install

```bash
launchctl load ~/Library/LaunchAgents/com.andrew.korean-vocab.plist
```

You'll get a native Mac notification every 30 minutes showing a random word. Clicking opens the app.

### Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.andrew.korean-vocab.plist
```

### Test notification manually

```bash
bash ~/Projects/korean-vocab/notify.sh
```

## Files

| File | Description |
|------|-------------|
| `extract_vocab.py` | Extracts vocab from Anki deck into `vocab.db` |
| `app.py` | Flask web app (port 5001) |
| `notify.sh` | Mac notification script |
| `vocab.db` | Local SQLite database (created by extract script) |
| `~/Library/LaunchAgents/com.andrew.korean-vocab.plist` | LaunchAgent for scheduled notifications |
