import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
MONTH_NAMES = ["january", "february", "march", "april", "may", "june", "july",
               "august", "september", "october", "november", "december"]


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")
    tmp.replace(p)


def clean(text):
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()


def parse_vb_date(value):
    """'01JAN13' -> '2013-01-01'; 'C' -> 'C'; 'U' -> 'U'."""
    v = clean(value).upper()
    if v in ("C", "U"):
        return v
    m = re.fullmatch(r"(\d{2})([A-Z]{3})(\d{2})", v)
    if not m or m.group(2).lower() not in MONTHS:
        return None
    d, mon, y = int(m.group(1)), MONTHS[m.group(2).lower()], int(m.group(3))
    year = 2000 + y if y < 70 else 1900 + y
    return date(year, mon, d).isoformat()


_DATE_PATTERNS = [
    (re.compile(r"\b(" + "|".join(MONTH_NAMES) + r")\.?\s+(\d{1,2}),?\s+(\d{4})\b", re.I), "mdy_name"),
    (re.compile(r"\b(" + "|".join(m[:3] for m in MONTH_NAMES) + r")\.?\s+(\d{1,2}),?\s+(\d{4})\b", re.I), "mdy_abbr"),
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), "iso"),
    (re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"), "us"),
]


def find_dates(text):
    """Return list of (iso_date, start, end) found in free text."""
    out = []
    for rx, kind in _DATE_PATTERNS:
        for m in rx.finditer(text or ""):
            try:
                if kind in ("mdy_name", "mdy_abbr"):
                    mon = MONTHS[m.group(1)[:3].lower()]
                    d = date(int(m.group(3)), mon, int(m.group(2)))
                elif kind == "iso":
                    d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                else:
                    d = date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
            except ValueError:
                continue
            out.append((d.isoformat(), m.start(), m.end()))
    out.sort(key=lambda x: x[1])
    dedup, seen = [], set()
    for d, s, e in out:
        if any(s < pe and e > ps for _, ps, pe in dedup):
            continue
        if (d, s) not in seen:
            seen.add((d, s))
            dedup.append((d, s, e))
    return dedup


def parse_any_date(text):
    found = find_dates(text)
    return found[0][0] if found else None


def duration_to_days(text):
    """'7.5 Months' -> 228, '45 Days' -> 45, '2 weeks' -> 14, 'Same Day' -> 0, 'NA' -> None."""
    t = clean(text).lower()
    if not t or t in ("na", "n/a", "-", "—"):
        return None
    if "same day" in t:
        return 0
    m = re.search(r"(\d+(?:\.\d+)?)\s*(calendar\s+)?(day|week|month|year)", t)
    if not m:
        return None
    n, unit = float(m.group(1)), m.group(3)
    return round(n * {"day": 1, "week": 7, "month": 30.4, "year": 365}[unit])


def unit_to_months(value, unit):
    if value is None:
        return None
    u = (unit or "").lower()
    if u.startswith("month"):
        return float(value)
    if u.startswith("week"):
        return round(float(value) * 7 / 30.4, 2)
    if u.startswith("day"):
        return round(float(value) / 30.4, 2)
    if u.startswith("year"):
        return float(value) * 12
    return float(value)
