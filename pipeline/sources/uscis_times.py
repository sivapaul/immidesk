"""USCIS processing times.

USCIS blocks automated requests to egov.uscis.gov from cloud IPs, so instead of
scraping it directly we read the daily SQLite dataset published by
github.com/jzebedee/uscis (released from residential IPs). Credit that project
on the site and consider sponsoring it.
"""
import gzip
import io
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from ..util import unit_to_months

RELEASES_API = "https://api.github.com/repos/jzebedee/uscis/releases/latest"
DATASET_URL = "https://github.com/jzebedee/uscis/releases/latest"

FORMS = {
    "I-485": "Adjust status to permanent resident",
    "I-765": "Work permit (EAD)",
    "I-131": "Travel document / advance parole",
    "I-140": "Immigrant petition for alien worker",
    "I-129": "Petition for nonimmigrant worker (H-1B, L-1)",
    "I-539": "Extend or change status (H-4, F-1)",
    "I-130": "Petition for alien relative",
    "I-751": "Remove conditions on residence",
    "I-90": "Replace green card",
    "N-400": "Naturalization",
    "I-526E": "Immigrant investor petition",
    "I-821D": "DACA renewal",
}


def _open_db_bytes(blob, name):
    if name.endswith(".gz"):
        blob = gzip.decompress(blob)
    elif name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            inner = next(n for n in z.namelist() if n.endswith(".db"))
            blob = z.read(inner)
    elif name.endswith(".zst"):
        import zstandard
        blob = zstandard.ZstdDecompressor().decompress(blob, max_output_size=1 << 30)
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.write(blob)
    tmp.close()
    return tmp.name


def summarize(db_path):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT p.form_name, p.office_code, o.description AS office, p.form_subtype, "
        "p.subtype_info_en, p.publication_date, p.range_upper, p.range_upper_unit, "
        "p.range_lower, p.range_lower_unit "
        "FROM processing_time p LEFT JOIN offices o ON o.code = p.office_code"
    ).fetchall()
    con.close()
    forms = {}
    for r in rows:
        if r["form_name"] not in FORMS:
            continue
        lo = unit_to_months(r["range_lower"], r["range_lower_unit"])
        hi = unit_to_months(r["range_upper"], r["range_upper_unit"])
        if hi is None:
            continue
        lo = hi if lo is None else lo
        f = forms.setdefault(r["form_name"], {"form": r["form_name"], "label": FORMS[r["form_name"]], "entries": []})
        f["entries"].append({
            "office_code": r["office_code"], "office": r["office"], "subtype": r["form_subtype"],
            "subtype_label": r["subtype_info_en"], "published": r["publication_date"],
            "low_months": round(min(lo, hi), 1), "high_months": round(max(lo, hi), 1),
        })
    out = []
    for f in forms.values():
        e = f["entries"]
        f["low_months"] = min(x["low_months"] for x in e)
        f["high_months"] = max(x["high_months"] for x in e)
        f["published"] = max((x["published"] or "") for x in e) or None
        out.append(f)
    out.sort(key=lambda f: list(FORMS).index(f["form"]))
    return out


def scrape(fetcher):
    if fetcher.offline:
        blob = fetcher.get("", "uscis_times", binary=True)
        path = _open_db_bytes(blob, "uscis.db")
        release = {"tag": "fixture", "url": DATASET_URL}
    else:
        rel = fetcher.get_json(RELEASES_API, "uscis_release", headers={"Accept": "application/vnd.github+json"})
        assets = rel.get("assets", [])
        asset = next((a for a in assets if a["name"].endswith((".db", ".db.gz", ".db.zst", ".zip"))), None)
        if not asset:
            raise ValueError(f"no database asset in release {rel.get('tag_name')}")
        blob = fetcher.get(asset["browser_download_url"], "uscis_times", binary=True)
        path = _open_db_bytes(blob, asset["name"])
        release = {"tag": rel.get("tag_name"), "url": rel.get("html_url", DATASET_URL)}
    try:
        forms = summarize(path)
    finally:
        Path(path).unlink(missing_ok=True)
    if not forms:
        raise ValueError("dataset contained none of the tracked forms")
    return {"release": release, "forms": forms}


def compute_deltas(current, previous):
    if not previous:
        return {}
    prev = {f["form"]: f for f in previous.get("forms", [])}
    out = {}
    for f in current["forms"]:
        p = prev.get(f["form"])
        if p:
            out[f["form"]] = round(f["high_months"] - p["high_months"], 1)
    return out
