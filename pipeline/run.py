import argparse
import sys
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from . import changes, deadlines, llm, news
from .http import Fetcher, NoFixture
from .sources import dol_flag, federal_register, feeds, uscis_times, visa_bulletin, wait_times
from .util import now_iso, read_json, write_json

ROOT = Path(__file__).resolve().parent.parent


class Ctx:
    def __init__(self, out, fetcher, cfg, force, only, runner="all"):
        self.out = Path(out)
        self.fetcher = fetcher
        self.cfg = cfg
        self.force = force
        self.only = only
        self.runner = runner
        self.runners = {k: v.get("runner", "cloud") for k, v in cfg["core"].items()}
        self.runners.update({f["id"]: f.get("runner", "cloud") for f in cfg.get("feeds", [])})
        self.sample = fetcher.offline
        self.status = read_json(self.out / "status.json", {}).get("sources", {}) if not self.sample else {}

    def meta(self, **extra):
        return {"generated_at": now_iso(), "sample": self.sample, **extra}

    def due(self, sid, min_hours):
        if self.force or self.sample:
            return True
        if self.only and sid not in self.only:
            return False
        last = (self.status.get(sid) or {}).get("last_success")
        if not last:
            return True
        return datetime.now(timezone.utc) - datetime.fromisoformat(last) >= timedelta(hours=min_hours or 0)

    def record(self, sid, name, url, ok, error=None, count=None):
        st = self.status.setdefault(sid, {})
        st.update({"name": name, "url": url, "last_attempt": now_iso(), "ok": ok, "error": error})
        if ok:
            st["last_success"] = st["last_attempt"]
            st["count"] = count


def run_source(ctx, sid, name, url, min_hours, fn):
    if ctx.only and sid not in ctx.only:
        return None
    if ctx.runner != "all" and ctx.runners.get(sid, "cloud") != ctx.runner:
        return None
    if not ctx.due(sid, min_hours):
        print(f"skip  {sid} (fresh)")
        return None
    try:
        result = fn()
        ctx.record(sid, name, url, True, count=result.pop("_count", None) if isinstance(result, dict) else None)
        print(f"ok    {sid}")
        return result
    except NoFixture:
        print(f"skip  {sid} (no sample fixture)")
        return None
    except Exception as e:
        ctx.record(sid, name, url, False, error=f"{type(e).__name__}: {e}"[:300])
        print(f"FAIL  {sid}: {e}", file=sys.stderr)
        if "--debug" in sys.argv:
            traceback.print_exc()
        return None


def seed_sample_history(ctx):
    """Sample mode only: write a fake previous snapshot so deltas show up."""
    from .sources.uscis_times import _open_db_bytes, summarize
    try:
        cur = visa_bulletin.find_latest_link(ctx.fetcher.get("", "visa_bulletin_index"))[1]
        y, m = cur
        prev = {"month": f"{y - (m == 1):04d}-{(m - 2) % 12 + 1:02d}", "url": "", "meta": ctx.meta(),
                "charts": visa_bulletin.parse_bulletin(ctx.fetcher.get("", "visa_bulletin_prev"))}
        write_json(ctx.out / "visa_bulletin" / f"{prev['month']}.json", prev)
    except Exception:
        pass
    old = (date.today() - timedelta(days=30)).isoformat()
    try:
        path = _open_db_bytes(ctx.fetcher.get("", "uscis_times_prev", binary=True), "x.db")
        write_json(ctx.out / "processing_times" / "history" / f"{old}.json", {"forms": summarize(path)})
        Path(path).unlink(missing_ok=True)
    except Exception:
        pass
    try:
        write_json(ctx.out / "wait_times" / "history" / f"{old}.json", {"posts": wait_times.parse(ctx.fetcher.get("", "wait_times_prev"))})
    except Exception:
        pass


def do_visa_bulletin(ctx):
    c = ctx.cfg["core"]["visa_bulletin"]
    res = run_source(ctx, "visa_bulletin", c["name"], c["url"], c["min_hours"], lambda: visa_bulletin.scrape(ctx.fetcher))
    if res:
        y, m = map(int, res["month"].split("-"))
        prev_key = f"{y - (m == 1):04d}-{(m - 2) % 12 + 1:02d}"
        prev = read_json(ctx.out / "visa_bulletin" / f"{prev_key}.json")
        res["deltas"] = visa_bulletin.compute_deltas(res["charts"], prev["charts"] if prev else None)
        res["previous_month"] = prev_key if prev else None
        res["meta"] = ctx.meta(source_url=res["url"])
        write_json(ctx.out / "visa_bulletin" / f"{res['month']}.json", res)
        write_json(ctx.out / "visa_bulletin" / "latest.json", res)
    return read_json(ctx.out / "visa_bulletin" / "latest.json")


def _snapshot(ctx, folder, res, deltas_fn, keep_days=120):
    today = date.today().isoformat()
    hist = ctx.out / folder / "history"
    snaps = sorted(hist.glob("*.json")) if hist.exists() else []
    target = (date.today() - timedelta(days=30)).isoformat()
    base = None
    for p in snaps:
        if p.stem < today:
            base = p
            if p.stem >= target:
                break
    prev = read_json(base) if base else None
    res["deltas"] = deltas_fn(res, prev)
    res["compared_to"] = base.stem if base else None
    write_json(hist / f"{today}.json", {k: v for k, v in res.items() if k not in ("deltas", "meta")})
    write_json(ctx.out / folder / "latest.json", res)
    cutoff = (date.today() - timedelta(days=keep_days)).isoformat()
    for p in snaps:
        if p.stem < cutoff:
            p.unlink()


def do_uscis_times(ctx):
    c = ctx.cfg["core"]["uscis_times"]
    res = run_source(ctx, "uscis_times", c["name"], c["url"], c["min_hours"], lambda: uscis_times.scrape(ctx.fetcher))
    if res:
        res["meta"] = ctx.meta(source_url="https://egov.uscis.gov/processing-times/", via=res["release"]["url"])
        _snapshot(ctx, "processing_times", res, uscis_times.compute_deltas)
    return read_json(ctx.out / "processing_times" / "latest.json")


def do_wait_times(ctx):
    c = ctx.cfg["core"]["wait_times"]
    res = run_source(ctx, "wait_times", c["name"], c["url"], c["min_hours"], lambda: wait_times.scrape(ctx.fetcher))
    if res:
        res["meta"] = ctx.meta(source_url=res["url"])
        _snapshot(ctx, "wait_times", res, wait_times.compute_deltas)
    return read_json(ctx.out / "wait_times" / "latest.json")


def do_dol(ctx):
    c = ctx.cfg["core"]["dol_flag"]
    res = run_source(ctx, "dol_flag", c["name"], c["url"], c["min_hours"], lambda: dol_flag.scrape(ctx.fetcher))
    if res:
        res["meta"] = ctx.meta(source_url=res["url"])
        write_json(ctx.out / "dol" / "latest.json", res)


def do_news(ctx):
    fresh = []
    c = ctx.cfg["core"]["federal_register"]

    def fr():
        r = federal_register.scrape(ctx.fetcher)
        r["_count"] = len(r["items"])
        return r
    res = run_source(ctx, "federal_register", c["name"], c["url"], c["min_hours"], fr)
    if res:
        fresh += res["items"]
    for src in ctx.cfg.get("feeds", []):
        if src.get("enabled", True) is False:
            continue

        def fd(src=src):
            r = feeds.scrape(ctx.fetcher, src)
            items = [news.tag(i) for i in r["items"]]
            if src.get("require_match"):
                items = [i for i in items if set(i["tags"]) - set(src.get("tags", []))]
            r["items"] = items
            r["_count"] = len(items)
            return r
        r = run_source(ctx, src["id"], src["name"], src["url"], src.get("min_hours", 6), fd)
        if r:
            fresh += r["items"]

    prev = (read_json(ctx.out / "news_raw.json") or {}).get("items", [])
    raw = news.merge_with_previous(fresh, prev)
    budget = {"left": int(__import__("os").environ.get("IMMIDESK_LLM_MAX", "40"))}
    for it in raw:
        if llm.enabled():
            llm.extract(it, budget)
    write_json(ctx.out / "news_raw.json", {"meta": ctx.meta(), "items": raw})

    stories = news.dedupe([dict(i, deadlines=list(i.get("deadlines", []))) for i in raw])
    for s in stories:
        news.tag(s)
        deadlines.extract(s)
        llm.apply(s)
        s.pop("preset_tags", None)
        s.pop("llm", None)
    stories.sort(key=lambda s: s.get("published") or "", reverse=True)
    write_json(ctx.out / "news.json", {"meta": ctx.meta(), "items": stories})
    write_json(ctx.out / "deadlines.json", {"meta": ctx.meta(), "items": deadlines.build(stories)})


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fetch immigration data into JSON for the ImmiDesk site.")
    ap.add_argument("--out", default=str(ROOT / "web" / "public" / "data"))
    ap.add_argument("--offline", metavar="FIXTURES_DIR", help="read fixtures instead of the network (sample data)")
    ap.add_argument("--force", action="store_true", help="ignore min_hours and fetch everything")
    ap.add_argument("--only", help="comma-separated source ids")
    ap.add_argument("--runner", choices=["all", "cloud", "local"], default="all",
                    help="run only sources tagged for this runner in sources.yaml")
    ap.add_argument("--config", default=str(ROOT / "sources.yaml"))
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args(argv)
    cfg = yaml.safe_load(Path(a.config).read_text(encoding="utf-8"))
    out = Path(a.out)
    if not a.offline and (read_json(out / "status.json") or {}).get("meta", {}).get("sample"):
        import shutil
        print("removing sample data before the first live run")
        shutil.rmtree(out)
    ctx = Ctx(a.out, Fetcher(a.offline), cfg, a.force, set(a.only.split(",")) if a.only else None, a.runner)

    if ctx.sample:
        seed_sample_history(ctx)
    vb = do_visa_bulletin(ctx)
    pt = do_uscis_times(ctx)
    wt = do_wait_times(ctx)
    do_dol(ctx)
    do_news(ctx)
    write_json(ctx.out / "changes.json", {"meta": ctx.meta(), "items": changes.build(vb, pt, wt)})

    all_ids = list(cfg["core"]) + [f["id"] for f in cfg.get("feeds", []) if f.get("enabled", True) is not False]
    max_age = {k: v.get("max_age_hours") for k, v in cfg["core"].items()}
    max_age.update({f["id"]: f.get("max_age_hours", 72) for f in cfg.get("feeds", [])})
    for sid in all_ids:
        if sid in ctx.status:
            ctx.status[sid]["max_age_hours"] = max_age.get(sid)
            ctx.status[sid]["verify"] = next((f.get("verify", False) for f in cfg.get("feeds", []) if f["id"] == sid), False)
    write_json(ctx.out / "status.json", {"meta": ctx.meta(), "sources": ctx.status})
    failed = [k for k, v in ctx.status.items() if not v.get("ok")]
    print(f"done: {len(ctx.status) - len(failed)} ok, {len(failed)} failed{': ' + ', '.join(failed) if failed else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
