import re
from datetime import date, timedelta

from .util import find_dates

RULES = [
    ("comments_close", "Public comments close", re.compile(r"comments?\b.{0,60}\b(due|close|closes|must be (received|submitted)|deadline|by)\b|comment period", re.I)),
    ("effective", "Takes effect", re.compile(r"\beffective\b|takes? effect|go(es)? into effect|implementation date", re.I)),
    ("registration_opens", "Registration opens", re.compile(r"registration (period|window)?.{0,30}\b(open|opens|begin|begins|start|starts)\b", re.I)),
    ("registration_closes", "Registration closes", re.compile(r"registration (period|window)?.{0,30}\b(close|closes|end|ends)\b|\b(closes|ends) (on )?$", re.I)),
    ("filing_window", "Filing window", re.compile(r"filing (period|window|season)|file (on or after|no later than|by)|may (begin|start) filing", re.I)),
    ("expires", "Ends or expires", re.compile(r"\bexpir(es|ation|ing)\b|\bterminat(es|ion)\b|\bsunset\b|\bthrough\b|\buntil\b", re.I)),
    ("deadline", "Deadline", re.compile(r"\bdeadline\b|no later than|must (be postmarked|apply|register|submit)", re.I)),
]

SENT_RX = re.compile(r"(?<=[.!?])\s+")


def _classify(window):
    best = None
    for typ, label, rx in RULES:
        for m in rx.finditer(window):
            if best is None or m.end() > best[0]:
                best = (m.end(), typ, label)
    return best


def extract(item):
    text = f"{item['title']}. {item.get('summary', '')}"
    published = item.get("published")
    have = {(d["date"], d["type"]) for d in item.get("deadlines", [])}
    found = []
    for sent in SENT_RX.split(text):
        dates = find_dates(sent)
        prev_end = 0
        for d, start, end in dates:
            hit = _classify(sent[prev_end:start]) or _classify(sent)
            prev_end = end
            if not hit or d == published:
                continue
            _, typ, label = hit
            if (d, typ) in have:
                continue
            have.add((d, typ))
            found.append({"date": d, "type": typ, "label": label, "confidence": "medium", "method": "pattern"})
    item.setdefault("deadlines", [])
    item["deadlines"] += found
    return item


def typical_dates(today=None):
    t = today or date.today()
    out = []
    nb = date(t.year, t.month, 15)
    if nb < t:
        nb = date(t.year + (t.month == 12), t.month % 12 + 1, 15)
    nxt = nb.month % 12 + 1
    out.append({"date": nb.isoformat(), "type": "visa_bulletin", "label": f"Next Visa Bulletin usually published around mid-month (for {date(2000, nxt, 1).strftime('%B')})",
                "confidence": "typical", "tags": ["gc", "family"], "url": "https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html"})
    mar = date(t.year + (t.month > 3), 3, 1)
    out.append({"date": mar.isoformat(), "type": "registration_opens", "label": "H-1B cap registration usually opens in March (exact dates announced by USCIS)",
                "confidence": "typical", "tags": ["h1b"], "url": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/h-1b-specialty-occupations/h-1b-electronic-registration-process"})
    octo = date(t.year + (t.month >= 10), 10, 1)
    out.append({"date": octo.isoformat(), "type": "fiscal_year", "label": "New fiscal year: new green card numbers and H-1B cap employment start date",
                "confidence": "typical", "tags": ["gc", "h1b"], "url": "https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html"})
    return out


def build(items, today=None, past_days=30, future_days=730):
    t = today or date.today()
    lo, hi = (t - timedelta(days=past_days)).isoformat(), (t + timedelta(days=future_days)).isoformat()
    out = []
    for it in items:
        for d in it.get("deadlines", []):
            if lo <= d["date"] <= hi:
                out.append({**d, "item_id": it["id"], "title": it["title"], "tags": it.get("tags", []),
                            "url": it["sources"][0]["url"], "source": it["sources"][0]["name"], "kind": it["kind"]})
    for d in typical_dates(t):
        if lo <= d["date"] <= hi:
            out.append({**d, "item_id": None, "title": d["label"], "source": "Typical calendar", "kind": "calendar"})
    seen, uniq = set(), []
    for d in sorted(out, key=lambda x: (x["date"], x["confidence"] != "high")):
        k = (d["date"], d["type"], d.get("item_id"))
        if k not in seen:
            seen.add(k)
            uniq.append(d)
    return uniq
