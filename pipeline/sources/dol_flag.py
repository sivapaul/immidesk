from bs4 import BeautifulSoup

from ..util import clean

URL = "https://flag.dol.gov/processingtimes"


def parse(html):
    soup = BeautifulSoup(html, "lxml")
    tables = []
    for table in soup.find_all("table"):
        rows = [[clean(c.get_text(" ")) for c in tr.find_all(["th", "td"])] for tr in table.find_all("tr")]
        rows = [r for r in rows if any(r)]
        if len(rows) < 2:
            continue
        heading = None
        for prev in table.find_all_previous(["h1", "h2", "h3", "h4", "caption", "strong"], limit=3):
            t = clean(prev.get_text(" "))
            if t:
                heading = t
                break
        cap = table.find("caption")
        tables.append({"heading": clean(cap.get_text(" ")) if cap else heading, "header": rows[0], "rows": rows[1:]})
    if not tables:
        raise ValueError("no processing time tables found")
    updated = None
    text = clean(soup.get_text(" "))
    import re
    m = re.search(r"(as of|updated|current as of)\s*:?\s*([A-Z][a-z]+\.? \d{1,2},? \d{4}|\d{1,2}/\d{1,2}/\d{4})", text, re.I)
    if m:
        updated = m.group(2)
    return {"tables": tables, "as_of": updated}


def scrape(fetcher):
    data = parse(fetcher.get(URL, "dol_flag"))
    data["url"] = URL
    return data
