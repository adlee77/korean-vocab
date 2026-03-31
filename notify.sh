#!/bin/bash
# Korean vocab reminder notification

DB_PATH="$HOME/Projects/korean-vocab/vocab.db"

# Pick a random non-memorized word
RESULT=$(sqlite3 "$DB_PATH" "SELECT korean, english FROM vocab WHERE memorized=0 ORDER BY RANDOM() LIMIT 1;" 2>/dev/null)

if [ -z "$RESULT" ]; then
  RESULT=$(sqlite3 "$DB_PATH" "SELECT korean, english FROM vocab ORDER BY RANDOM() LIMIT 1;" 2>/dev/null)
fi

if [ -z "$RESULT" ]; then
  exit 0
fi

KOREAN=$(echo "$RESULT" | cut -d'|' -f1)
ENGLISH=$(echo "$RESULT" | cut -d'|' -f2)

osascript <<EOF
tell application "System Events"
  display notification "${ENGLISH}" with title "Korean Study Time 🇰🇷" subtitle "${KOREAN}" sound name "default"
end tell
EOF

# Open the app in browser
open "http://localhost:5001"
