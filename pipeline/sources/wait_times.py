import re

from bs4 import BeautifulSoup

from ..util import clean, duration_to_days

URL = "https://travel.state.gov/content/travel/en/us-visas/visa-information-resources/global-visa-wait-times.html"

COLUMNS = [
    ("b_avg", re.compile(r"b1/b2.*average", re.I)),
    ("b_next", re.compile(r"b1/b2.*next", re.I)),
    ("f_next", re.compile(r"f\s*,\s*m\s*,\s*j", re.I)),
    ("h_next", re.compile(r"h\s*,\s*l\s*,\s*o", re.I)),
    ("c_next", re.compile(r"crew|transit", re.I)),
]


def parse(html):
    soup = BeautifulSoup(html, "lxml")
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        header = [clean(c.get_text(" ")) for c in rows[0].find_all(["th", "td"])]
        if not header or not re.search(r"city|post", header[0], re.I):
            continue
        keys = [next((k for k, rx in COLUMNS if rx.search(h)), None) for h in header[1:]]
        if "h_next" not in keys:
            continue
        posts = []
        for tr in rows[1:]:
            cells = [clean(c.get_text(" ")) for c in tr.find_all(["th", "td"])]
            if len(cells) < 2 or not cells[0]:
                continue
            post = {"post": re.sub(r"\s*\(.*?\)\s*", " ", cells[0]).strip(), "post_raw": cells[0]}
            for k, raw in zip(keys, cells[1:]):
                if k:
                    post[k] = {"text": raw, "days": duration_to_days(raw)}
            posts.append(post)
        if posts:
            return posts
    raise ValueError("wait time table not found")


def scrape(fetcher):
    return {"url": URL, "posts": parse(fetcher.get(URL, "wait_times"))}


def compute_deltas(current, previous):
    if not previous:
        return {}
    prev = {p["post"]: p for p in previous.get("posts", [])}
    out = {}
    for p in current["posts"]:
        q = prev.get(p["post"])
        if not q:
            continue
        for k in ("b_next", "f_next", "h_next"):
            a, b = (p.get(k) or {}).get("days"), (q.get(k) or {}).get("days")
            if a is not None and b is not None and a != b:
                out[f"{p['post']}.{k}"] = a - b
    return out
