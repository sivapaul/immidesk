import hashlib
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..util import clean, find_dates, parse_any_date

ATOM = "{http://www.w3.org/2005/Atom}"


def _id(source_id, url):
    return f"{source_id}-{hashlib.sha1(url.encode()).hexdigest()[:10]}"


def _strip_html(s):
    return clean(BeautifulSoup(s or "", "lxml").get_text(" "))


def _rss_date(s):
    if not s:
        return None
    try:
        return parsedate_to_datetime(s).date().isoformat()
    except (TypeError, ValueError):
        return parse_any_date(s) or (s[:10] if re.match(r"\d{4}-\d{2}-\d{2}", s) else None)


def parse_rss(xml_text, base_url=""):
    root = ET.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
    out = []
    for it in root.iter("item"):
        out.append({
            "title": clean(it.findtext("title")),
            "url": clean(it.findtext("link")),
            "published": _rss_date(it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date")),
            "summary": _strip_html(it.findtext("description"))[:400],
        })
    for e in root.iter(f"{ATOM}entry"):
        link = e.find(f"{ATOM}link")
        out.append({
            "title": clean(e.findtext(f"{ATOM}title")),
            "url": urljoin(base_url, link.get("href")) if link is not None else "",
            "published": _rss_date(e.findtext(f"{ATOM}published") or e.findtext(f"{ATOM}updated")),
            "summary": _strip_html(e.findtext(f"{ATOM}summary") or e.findtext(f"{ATOM}content"))[:400],
        })
    return [x for x in out if x["title"] and x["url"]]


def parse_links(html, base_url, href_pattern, min_len=20, limit=40):
    soup = BeautifulSoup(html, "lxml")
    rx = re.compile(href_pattern)
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"]).split("#")[0]
        title = clean(a.get_text(" "))
        if not rx.search(href) or len(title) < min_len or href in seen:
            continue
        seen.add(href)
        published, summary, node = None, "", a
        for _ in range(4):
            node = node.parent
            if node is None:
                break
            t = node.find("time")
            if t is not None:
                published = (t.get("datetime") or "")[:10] or parse_any_date(t.get_text(" "))
            if not published:
                found = find_dates(node.get_text(" "))
                published = found[0][0] if found else None
            if published:
                p = node.find("p")
                if p is not None and clean(p.get_text(" ")) != title:
                    summary = clean(p.get_text(" "))[:400]
                break
        out.append({"title": title, "url": href, "published": published, "summary": summary})
        if len(out) >= limit:
            break
    return out


def scrape(fetcher, src):
    raw = fetcher.get(src["url"], src["id"])
    if src["type"] == "rss":
        entries = parse_rss(raw, src["url"])
    elif src["type"] == "html_links":
        entries = parse_links(raw, src["url"], src["href_pattern"], src.get("min_title", 20))
    else:
        raise ValueError(f"unknown feed type {src['type']}")
    if not entries:
        raise ValueError("no entries found; the page layout may have changed")
    items = []
    for e in entries:
        items.append({
            "id": _id(src["id"], e["url"]),
            "title": e["title"],
            "summary": "" if src.get("store") == "headline_only" else e["summary"],
            "kind": src.get("kind", "agency_news"),
            "published": e["published"],
            "sources": [{"id": src["id"], "name": src["name"], "url": e["url"], "published": e["published"]}],
            "deadlines": [],
            "preset_tags": src.get("tags", []),
        })
    return {"items": items}
