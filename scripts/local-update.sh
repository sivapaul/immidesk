#!/usr/bin/env bash
# Fetch sources that block cloud IPs (runner: local) from this machine and push the data.
# Use from cron if you are not using a self-hosted runner:
#   17 */6 * * * cd /path/to/immidesk && scripts/local-update.sh >> /tmp/immidesk-local.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."
git pull -q --rebase origin main
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt
python -m pipeline.run --runner local "$@"
python -m pipeline.validate
scripts/commit-data.sh "data: local sources"
