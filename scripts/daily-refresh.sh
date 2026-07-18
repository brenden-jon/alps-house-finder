#!/bin/zsh
# Daily refresh: scrape -> score -> export -> push (which triggers the Pages deploy).
set -e
REPO="/Users/bjongman/Library/CloudStorage/Dropbox/Molta/Coding folder/alps-house-finder"
cd "$REPO"
scrapers/.venv/bin/alpsfinder refresh
if ! git diff --quiet -- data/export; then
  git add data/export
  git commit -m "data refresh $(date +%F)"
  git push origin main || echo "push failed (no remote yet?)"
fi
