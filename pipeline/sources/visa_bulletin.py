import re
from datetime import date

from bs4 import BeautifulSoup

from ..util import MONTH_NAMES, clean, parse_vb_date

INDEX_URL = "https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html"
BASE = "https://travel.state.gov"
LINK_RX = re.compile(r"visa-bulletin-for-(" + "|".join(MONTH_NAMES) + r")-(\d{4})\.html", re.I)

COUNTRY_KEYS = [
    ("all", re.compile(r"all\s+chargeability", re.I)),
    ("cn", re.compile(r"china", re.I)),
    ("in", re.compile(r"india", re.I)),
    ("mx", re.compile(r"mexico", re.I)),
    ("ph", re.compile(r"philippines", re.I)),
]

EB_LABELS = [
    (re.compile(r"^1st", re.I), "EB-1"),
    (re.compile(r"^2nd", re.I), "EB-2"),
    (re.compile(r"^3rd", re.I), "EB-3"),
    (re.compile(r"^other\s+workers", re.I), "Other workers"),
    (re.compile(r"^4th", re.I), "EB-4"),
    (re.compile(r"religious", re.I), "Religious workers"),
    (re.compile(r"^5th\s+unreserved", re.I), "EB-5 unreserved"),
    (re.compile(r"rural", re.I), "EB-5 rural"),
    (re.compile(r"high\s+unemployment", re.I), "EB-5 high unemployment"),
    (re.compile(r"infrastructure", re.I), "EB-5 infrastructure"),
]


def bulletin_url(month, year):
    fy = year + 1 if month >= 10 else year
    return f"{BASE}/content/travel/en/legal/visa-law0/visa-bulletin/{fy}/visa-bulletin-for-{MONTH_NAMES[month - 1]}-{year}.html"


def find_latest_link(index_html):
    found = {}
    for href in re.findall(r'href="([^"]+)"', index_html):
        m = LINK_RX.search(href)
        if m:
            key = (int(m.group(2)), MONTH_NAMES.index(m.group(1).lower()) + 1)
            found[key] = href if href.startswith("http") else BASE + href
    if not found:
        return None, None
    key = max(found)
    return found[key], key


def _row_label(kind, text):
    t = clean(text)
    if kind == "fb":
        m = re.match(r"^(F1|F2A|F2B|F3|F4)\b", t, re.I)
        return m.group(1).upper() if m else None
    for rx, label in EB_LABELS:
        if rx.search(t):
            return label
    return None


def parse_bulletin(html):
    soup = BeautifulSoup(html, "lxml")
    counts = {"fb": 0, "eb": 0}
    out = {"fb": {"fad": {}, "dff": {}}, "eb": {"fad": {}, "dff": {}}}
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 3:
            continue
        header = [clean(c.get_text(" ")) for c in rows[0].find_all(["td", "th"])]
        if not header:
            continue
        first = header[0].lower()
        kind = "fb" if "family" in first else "eb" if "employment" in first else None
        if not kind:
            continue
        cols = []
        for h in header[1:]:
            key = next((k for k, rx in COUNTRY_KEYS if rx.search(h)), None)
            cols.append(key)
        if "all" not in cols:
            continue
        chart = "fad" if counts[kind] == 0 else "dff" if counts[kind] == 1 else None
        counts[kind] += 1
        if not chart:
            continue
        for tr in rows[1:]:
            cells = [clean(c.get_text(" ")) for c in tr.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            label = _row_label(kind, cells[0])
            if not label:
                continue
            vals = {}
            for key, raw in zip(cols, cells[1:]):
                if key:
                    vals[key] = parse_vb_date(raw)
            out[kind][chart][label] = vals
    if not out["eb"]["fad"] or not out["fb"]["fad"]:
        raise ValueError("could not find family and employment final action tables")
    return out


def _months_between(a, b):
    da, db = date.fromisoformat(a), date.fromisoformat(b)
    return round((db.year - da.year) * 12 + (db.month - da.month) + (db.day - da.day) / 30.4, 1)


def compute_deltas(current, previous):
    """Months each cutoff moved vs previous bulletin. Positive = advanced."""
    deltas = {}
    if not previous:
        return deltas
    for kind in ("eb", "fb"):
        for chart in ("fad", "dff"):
            for cat, vals in current[kind][chart].items():
                pv = previous.get(kind, {}).get(chart, {}).get(cat, {})
                for c, v in vals.items():
                    p = pv.get(c)
                    key = f"{kind}.{chart}.{cat}.{c}"
                    if v is None or p is None:
                        continue
                    if v == p:
                        deltas[key] = 0
                    elif v in ("C", "U") or p in ("C", "U"):
                        deltas[key] = v
                    else:
                        deltas[key] = _months_between(p, v)
    return deltas


def scrape(fetcher):
    index = fetcher.get(INDEX_URL, "visa_bulletin_index")
    url, key = find_latest_link(index)
    if not url:
        raise ValueError("no bulletin links found on index page")
    html = fetcher.get(url, "visa_bulletin")
    year, month = key
    return {"month": f"{year:04d}-{month:02d}", "url": url, "charts": parse_bulletin(html)}
