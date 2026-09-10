#!/usr/bin/env bash
set -euo pipefail
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add README.md assets
if git diff --cached --quiet; then exit 0; fi
git commit -m 'Refresh profile feeds and generated cards'
for attempt in 1 2 3; do
  git pull --rebase origin main
  if git push origin HEAD:main; then exit 0; fi
  sleep 3
done
exit 1
