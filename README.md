# ImmiDesk

US immigration data from official sources, on one public page: Visa Bulletin movement, USCIS processing times, Department of Labor queues, visa appointment wait times, new rules and news, and the dates that matter.

No accounts, no server, no personal data. Scrapers run on GitHub Actions, commit JSON to this repo, and a static React site reads it.

Not legal advice. Not affiliated with any government agency.

## How it works

```
sources.yaml ──► pipeline/ (Python, GitHub Actions every 4h)
                   ├─ visa_bulletin      travel.state.gov HTML tables
                   ├─ uscis_times        daily dataset from github.com/jzebedee/uscis
                   ├─ wait_times         travel.state.gov global wait times table
                   ├─ dol_flag           flag.dol.gov tables
                   ├─ federal_register   official API (rules, comment deadlines, effective dates)
                   └─ feeds              State, USCIS, SEVP, DHS, CBP, DOL, White House, embassies
                 ─► dedupe + tag + deadline extraction ─► validate ─► commit
web/public/data/*.json ──► web/ (React + Vite) ──► GitHub Pages
```

- **Failures are isolated.** If one source breaks, the others still update and the site keeps that source's last good data. `status.json` records every attempt, and the site's footer shows each source's health.
- **Validation gates the commit.** `pipeline.validate` checks every file against a schema. Schema errors fail the run and nothing is committed. Stale sources open a `data-stale` GitHub issue.
- **Deadlines** come from three places: structured Federal Register fields (`comments_close_on`, `effective_on`), pattern matching on dates near words like "effective", "comments due" or "registration opens", and optional AI extraction when `ANTHROPIC_API_KEY` is set. Each date carries a confidence label shown on the site.
- **USCIS processing times** are read from the daily SQLite release published by [jzebedee/uscis](https://github.com/jzebedee/uscis), because USCIS blocks requests from cloud IPs. Please credit and consider sponsoring that project.

## Run it locally

Requires Python 3.11+ and Node 20+.

```bash
pip install -r requirements.txt
python -m pytest -q

# sample data from fixtures (marked as sample on the site)
python -m pipeline.run --offline tests/fixtures
python -m pipeline.validate

cd web
npm install
npm run dev          # http://localhost:5173
```

Windows PowerShell uses the same commands. To fetch live data instead of samples, run `python -m pipeline.run --force`. The first live run deletes any sample data automatically.

Useful flags: `--runner cloud|local` runs only sources tagged for that runner, `--only visa_bulletin,wait_times` runs a subset, `--debug` prints full tracebacks, `--out DIR` writes somewhere else.

## Deploy on GitHub Pages

1. Push this repo to GitHub (default branch `main`).
2. Settings → Pages → Source: **GitHub Actions**.
3. Settings → Actions → General → Workflow permissions: **Read and write**.
4. Actions → **Update data** → Run workflow (tick *force* the first time). When it finishes, **Deploy site** publishes to `https://<you>.github.io/<repo>/`.
5. Optional: add an `ANTHROPIC_API_KEY` repository secret to turn on AI deadline extraction (capped at 40 new items per run via `IMMIDESK_LLM_MAX`).

Using a custom domain? Set a repository variable `SITE_BASE` to `/` (Settings → Secrets and variables → Actions → Variables), add the domain under Settings → Pages, and point DNS at GitHub Pages.

Set `IMMIDESK_USER_AGENT` in the workflow to include your repo URL so site owners can reach you.

## Sites that block GitHub Actions

travel.state.gov (Visa Bulletin, wait times, visa news), dol.gov and embassy sites return HTTP 403 to cloud servers. These sources are tagged `runner: local` in `sources.yaml` and fetched from a computer you own, on a normal home connection. Everything else runs in GitHub Actions. If no local runner is set up, those sections show as unavailable and the rest of the site keeps updating.

**Option A: self-hosted runner (logs stay in GitHub Actions).** On a personal Linux, macOS or WSL machine that stays on:

1. Repo → Settings → Actions → Runners → **New self-hosted runner**, pick your OS and run the commands it shows. When asked for labels, add `immidesk`.
2. Install it as a service so it survives reboots: `sudo ./svc.sh install && sudo ./svc.sh start`.
3. Repo → Settings → Secrets and variables → Actions → Variables → add `LOCAL_RUNNER` = `true`.
4. Settings → Actions → General → set *Fork pull request workflows* to require approval for all outside collaborators. The local job only runs on the schedule and manual runs, never on pull requests.

**Option B: cron.** Clone the repo on that machine with push access and add:

```
17 */6 * * * cd ~/immidesk && scripts/local-update.sh >> /tmp/immidesk-local.log 2>&1
```

Use a personal machine, not a work laptop.

## Add a news source

Add an entry under `feeds` in `sources.yaml`:

```yaml
- id: my_source
  name: Display name
  type: html_links          # or rss
  url: https://example.gov/news
  href_pattern: '/news/\d{4}/'   # which links count as articles
  kind: agency_news         # final_rule, proposed_rule, notice, presidential, agency_news, court, legislation, law_firm, media
  tags: [students]          # optional, always applied
  require_match: true       # keep only items that match an immigration topic
  store: headline_only      # for media and law firms
  min_hours: 6
```

Then run `python -m pipeline.run --only my_source --debug` and check `web/public/data/news.json`.

## Before going live: verify these

Entries marked `verify: true` in `sources.yaml` have URL patterns written from each site's known URL structure but not yet checked against the live page, because the build environment couldn't reach those sites. Run each once with `--only <id> --debug`, and fix `href_pattern` if it finds nothing. Also confirm on the first live run:

- The Visa Bulletin index page still links to bulletins as `visa-bulletin-for-<month>-<year>.html`.
- The wait times page serves its table in HTML (if it loads by JavaScript, the parser needs the underlying JSON URL instead).
- The jzebedee/uscis release asset name (the parser accepts `.db`, `.db.gz`, `.db.zst` and `.zip`).
- uscis.gov and some DHS sites may block GitHub Actions IPs. Blocked sources show as Failing in the footer while everything else keeps working.

## Data files

| File | Contents |
|---|---|
| `visa_bulletin/latest.json`, `YYYY-MM.json` | Both charts, both preference groups, five countries, deltas vs the previous month |
| `processing_times/latest.json`, `history/` | Range per form across offices, change vs about 30 days ago |
| `wait_times/latest.json`, `history/` | Every post, all five columns as text and days, changes |
| `dol/latest.json` | PERM and prevailing wage tables |
| `news.json` | Deduplicated stories with tags, sources and deadlines |
| `deadlines.json` | Upcoming and recent dates with confidence labels |
| `changes.json` | This month's headline changes |
| `status.json` | Per-source health |

All of it is public and can be reused.

## Roadmap

- Phase 2: "My desk" (priority date, receipt numbers and deadlines saved in the browser only)
- Phase 3: optional accounts for alerts and cross-device sync
- Later: USCIS Case Status API if production access is approved

## License

MIT. Government data is public domain. News headlines link to their publishers.
