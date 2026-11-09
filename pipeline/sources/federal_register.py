from ..util import clean

API = "https://www.federalregister.gov/api/v1/documents.json"

QUERIES = [
    {"agency": "u-s-citizenship-and-immigration-services", "term": None},
    {"agency": "homeland-security-department", "term": "immigration OR visa OR nonimmigrant"},
    {"agency": "state-department", "term": "visa OR visas OR immigrant"},
    {"agency": "labor-department", "term": "H-1B OR H-2A OR H-2B OR \"labor certification\" OR PERM OR \"prevailing wage\""},
    {"agency": "u-s-customs-and-border-protection", "term": "visa OR admission OR ESTA OR I-94"},
    {"agency": "u-s-immigration-and-customs-enforcement", "term": "student OR SEVP OR SEVIS OR \"F-1\""},
    {"agency": "executive-office-of-the-president", "term": "immigration OR visa OR entry OR aliens"},
]

FIELDS = ["title", "abstract", "document_number", "html_url", "publication_date", "type",
          "effective_on", "comments_close_on", "agencies", "action"]

TYPE_KIND = {"Rule": "final_rule", "Proposed Rule": "proposed_rule", "Notice": "notice",
             "Presidential Document": "presidential"}


def build_params(q, per_page=40):
    params = [("order", "newest"), ("per_page", str(per_page)),
              ("conditions[agencies][]", q["agency"])]
    if q["term"]:
        params.append(("conditions[term]", q["term"]))
    params += [("fields[]", f) for f in FIELDS]
    return params


def to_item(doc):
    agencies = [a.get("name") for a in doc.get("agencies") or [] if a.get("name")]
    deadlines = []
    if doc.get("comments_close_on"):
        deadlines.append({"date": doc["comments_close_on"], "type": "comments_close",
                          "label": "Public comments close", "confidence": "high", "method": "structured"})
    if doc.get("effective_on"):
        deadlines.append({"date": doc["effective_on"], "type": "effective",
                          "label": "Takes effect", "confidence": "high", "method": "structured"})
    return {
        "id": f"fr-{doc['document_number']}",
        "title": clean(doc.get("title")),
        "summary": clean(doc.get("abstract"))[:400],
        "kind": TYPE_KIND.get(doc.get("type"), "notice"),
        "published": doc.get("publication_date"),
        "fr_doc": doc["document_number"],
        "sources": [{"id": "federal_register", "name": "Federal Register", "url": doc.get("html_url"),
                     "published": doc.get("publication_date"), "detail": ", ".join(agencies)}],
        "deadlines": deadlines,
    }


def scrape(fetcher):
    items, seen, errors = [], set(), []
    for i, q in enumerate(QUERIES):
        try:
            data = fetcher.get_json(API, f"federal_register_{i}", params=build_params(q))
        except Exception as e:
            errors.append(f"{q['agency']}: {e}")
            continue
        for doc in data.get("results", []):
            if doc.get("document_number") and doc["document_number"] not in seen:
                seen.add(doc["document_number"])
                items.append(to_item(doc))
    if not items and errors:
        raise RuntimeError("; ".join(errors))
    return {"items": items, "partial_errors": errors}
