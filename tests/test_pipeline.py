import json
from datetime import date
from pathlib import Path

import pytest

from pipeline import changes, deadlines, news, run, validate
from pipeline.http import Fetcher
from pipeline.sources import feeds, federal_register, visa_bulletin, wait_times
from pipeline.util import duration_to_days, find_dates, parse_vb_date

FX = Path(__file__).parent / "fixtures"


def test_parse_vb_date():
    assert parse_vb_date("01JAN13") == "2013-01-01"
    assert parse_vb_date(" C ") == "C"
    assert parse_vb_date("U") == "U"
    assert parse_vb_date("15OCT99") == "1999-10-15"
    assert parse_vb_date("garbage") is None


def test_bulletin_url_uses_fiscal_year():
    assert visa_bulletin.bulletin_url(11, 2026).endswith("/visa-bulletin/2027/visa-bulletin-for-november-2026.html")
    assert visa_bulletin.bulletin_url(9, 2026).endswith("/visa-bulletin/2026/visa-bulletin-for-september-2026.html")


def test_find_latest_link_picks_newest():
    html = (FX / "visa_bulletin_index.html").read_text()
    url, (y, m) = visa_bulletin.find_latest_link(html)
    assert url.startswith("https://travel.state.gov/") and f"-{y}.html" in url


def test_parse_bulletin_tables():
    charts = visa_bulletin.parse_bulletin((FX / "visa_bulletin.html").read_text())
    assert charts["eb"]["fad"]["EB-2"]["in"] == "2013-01-01"
    assert charts["eb"]["fad"]["EB-1"]["all"] == "C"
    assert charts["eb"]["dff"]["EB-2"]["in"] == "2013-07-15"
    assert charts["eb"]["fad"]["Religious workers"]["all"] == "U"
    assert charts["fb"]["fad"]["F2A"]["mx"] == "2022-02-01"
    assert set(charts["eb"]["fad"]["EB-3"]) == {"all", "cn", "in", "mx", "ph"}


def test_bulletin_deltas():
    cur = visa_bulletin.parse_bulletin((FX / "visa_bulletin.html").read_text())
    prev = visa_bulletin.parse_bulletin((FX / "visa_bulletin_prev.html").read_text())
    d = visa_bulletin.compute_deltas(cur, prev)
    assert d["eb.fad.EB-2.in"] == 1.0
    assert d["eb.fad.EB-3.ph"] == -3.0
    assert d["eb.fad.EB-1.all"] == 0


def test_duration_to_days():
    assert duration_to_days("7.5 Months") == 228
    assert duration_to_days("2 weeks") == 14
    assert duration_to_days("45 Calendar Days") == 45
    assert duration_to_days("Same Day") == 0
    assert duration_to_days("NA") is None


def test_wait_times_parse():
    posts = wait_times.parse((FX / "wait_times.html").read_text())
    chennai = next(p for p in posts if p["post"] == "Chennai")
    assert chennai["h_next"] == {"text": "2.5 months", "days": 76}
    assert chennai["c_next"]["days"] is None
    assert len(posts) >= 20


def test_federal_register_item_deadlines():
    doc = json.loads((FX / "federal_register_0.json").read_text())["results"][0]
    item = federal_register.to_item(doc)
    assert item["kind"] == "proposed_rule"
    assert item["deadlines"][0]["type"] == "comments_close" and item["deadlines"][0]["confidence"] == "high"


def test_federal_register_params():
    p = federal_register.build_params({"agency": "state-department", "term": "visa"})
    assert ("conditions[agencies][]", "state-department") in p and ("conditions[term]", "visa") in p


def test_html_links_and_rss():
    items = feeds.parse_links((FX / "uscis_news.html").read_text(), "https://www.uscis.gov/newsroom/all-news",
                              r"/newsroom/(news-releases|alerts)/")
    assert len(items) == 4 and all(i["published"] for i in items)
    rss = """<rss><channel><item><title>Alert: new rule for F-1 students</title><link>https://x.gov/a</link>
             <pubDate>Mon, 02 Nov 2026 10:00:00 GMT</pubDate><description>&lt;p&gt;Hello&lt;/p&gt;</description></item></channel></rss>"""
    r = feeds.parse_rss(rss)
    assert r[0]["published"] == "2026-11-02" and r[0]["summary"] == "Hello"


def test_find_dates_and_extract():
    assert [d for d, _, _ in find_dates("Opens March 1, 2027 and closes Mar. 18, 2027.")] == ["2027-03-01", "2027-03-18"]
    item = {"id": "x", "title": "H-1B registration", "published": "2026-11-01", "deadlines": [],
            "summary": "The registration period opens March 1, 2027 and closes March 18, 2027. Comments are due by December 5, 2026."}
    deadlines.extract(item)
    got = {(d["date"], d["type"]) for d in item["deadlines"]}
    assert ("2027-03-01", "registration_opens") in got
    assert ("2027-03-18", "registration_closes") in got
    assert ("2026-12-05", "comments_close") in got


def test_tag_and_dedupe():
    a = {"id": "fr-1", "title": "USCIS Fee Schedule Adjustment for Employment Authorization", "summary": "", "kind": "final_rule",
         "published": "2026-10-30", "fr_doc": "2026-23001", "sources": [{"name": "FR", "url": "u1"}], "deadlines": []}
    b = {"id": "n-1", "title": "USCIS Announces Fee Schedule Adjustment for Employment Authorization", "summary": "", "kind": "agency_news",
         "published": "2026-10-31", "sources": [{"name": "USCIS", "url": "u2"}], "deadlines": []}
    c = {"id": "n-2", "title": "Civics test update", "summary": "", "kind": "agency_news", "published": "2026-10-31",
         "sources": [{"name": "USCIS", "url": "u3"}], "deadlines": []}
    stories = news.dedupe([b, a, c])
    assert len(stories) == 2
    merged = next(s for s in stories if s["id"] == "fr-1")
    assert [s["url"] for s in merged["sources"]] == ["u1", "u2"]
    assert "fees" in news.tag(merged)["tags"] and "gc" in merged["tags"]


def test_typical_dates():
    t = deadlines.typical_dates(date(2026, 11, 20))
    assert t[0]["date"] == "2026-12-15"
    assert any(x["date"] == "2027-03-01" for x in t)


def test_changes_text():
    vb = {"deltas": {"eb.fad.EB-2.in": 1.0, "eb.fad.EB-3.ph": -3.0, "eb.fad.EB-1.all": 0}}
    out = changes.visa_bulletin(vb)
    assert out[0]["text"] == "EB-3 Philippines moved back 3 months" and out[0]["tone"] == "bad"


def test_full_offline_run_is_valid(tmp_path):
    assert run.main(["--offline", str(FX), "--out", str(tmp_path)]) == 0
    errors, _ = validate.check(tmp_path)
    assert errors == []
    meta = json.loads((tmp_path / "news.json").read_text())["meta"]
    assert meta["sample"] is True
    st = json.loads((tmp_path / "status.json").read_text())["sources"]
    assert st["visa_bulletin"]["ok"] and st["federal_register"]["ok"]


def test_failed_source_keeps_previous_data(tmp_path, monkeypatch):
    run.main(["--offline", str(FX), "--out", str(tmp_path)])
    before = (tmp_path / "visa_bulletin" / "latest.json").read_text()

    def boom(*a, **k):
        raise ValueError("layout changed")
    monkeypatch.setattr(visa_bulletin, "parse_bulletin", boom)
    run.main(["--offline", str(FX), "--out", str(tmp_path), "--only", "visa_bulletin"])
    assert (tmp_path / "visa_bulletin" / "latest.json").read_text() == before


def test_fetcher_offline_missing_fixture(tmp_path):
    from pipeline.http import NoFixture
    with pytest.raises(NoFixture):
        Fetcher(tmp_path).get("x", "nothing")
