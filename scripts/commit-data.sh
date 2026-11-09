#!/usr/bin/env bash
set -euo pipefail
msg="${1:-data: update}"
git config user.name >/dev/null || git config user.name "immidesk-bot"
git config user.email >/dev/null || git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add web/public/data
if git diff --cached --quiet; then
  echo "no data changes"
  exit 0
fi
git commit -q -m "$msg $(date -u +%Y-%m-%dT%H:%MZ)"
for i in 1 2 3; do
  git pull -q --rebase -X theirs origin main && git push -q origin HEAD:main && exit 0
  sleep $((i * 5))
done
echo "push failed" >&2
exit 1
