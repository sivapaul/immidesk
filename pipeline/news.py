import re
from datetime import date, timedelta
from difflib import SequenceMatcher

TAG_RULES = {
    "h1b": r"\bH-?1B\b|specialty occupation|cap registration|cap-subject",
    "gc": r"green card|adjustment of status|\bI-485\b|\bI-140\b|permanent resident|\bEB-?[1-5]\b|visa bulletin|"
          r"labor certification|\bPERM\b|prevailing wage|priority date|immigrant visa|\bI-765\b|employment authorization|\bEAD\b",
    "students": r"\bF-1\b|\bOPT\b|\bSTEM\b|\bSEVP\b|\bSEVIS\b|\bstudents?\b|\bJ-1\b|exchange visitor|duration of status",
    "citizenship": r"naturaliz|\bN-400\b|citizenship|civics test",
    "family": r"\bI-130\b|family-sponsored|\bspouses?\b|fianc|\bK-1\b|relative petition",
    "humanitarian": r"asylum|refugee|\bTPS\b|temporary protected|\bparole\b|\bDACA\b|humanitarian",
    "fees": r"\bfees?\b|fee schedule|premium processing",
    "travel": r"visa appointment|interview waiver|consular|embassy|consulate|\btravel\b|entry into the united states|"
              r"\bESTA\b|\bI-94\b|proclamation|suspension of entry|visa issuance|visa integrity|social media",
    "work_visas": r"\bH-2A\b|\bH-2B\b|\bL-1\b|\bO-1\b|\bTN\b|\bE-[123]\b|\bH-4\b",
}
TAG_RX = {k: re.compile(v, re.I) for k, v in TAG_RULES.items()}
FR_DOC_RX = re.compile(r"\b(20\d{2}-\d{5})\b")
KIND_RANK = {"final_rule": 0, "proposed_rule": 1, "presidential": 2, "notice": 3, "agency_news": 4,
             "court": 5, "legislation": 6, "law_firm": 7, "media": 8}


def tag(item):
    text = f"{item['title']} {item.get('summary', '')}"
    tags = {k for k, rx in TAG_RX.items() if rx.search(text)}
    tags.update(item.get("preset_tags", []))
    item["tags"] = sorted(tags)
    return item


def _norm(t):
    t = re.sub(r"[^a-z0-9 ]", " ", t.lower())
    return " ".join(w for w in t.split() if w not in {"the", "a", "an", "of", "for", "and", "to", "in", "on", "uscis", "announces"})


def _close(a, b):
    if not a or not b:
        return True
    return abs((date.fromisoformat(a) - date.fromisoformat(b)).days) <= 10


def dedupe(items):
    items = sorted(items, key=lambda i: (KIND_RANK.get(i["kind"], 9), i.get("published") or "9999"))
    stories = []
    for it in items:
        refs = set(FR_DOC_RX.findall(f"{it['title']} {it.get('summary', '')}"))
        if it.get("fr_doc"):
            refs.add(it["fr_doc"])
        match = None
        for s in stories:
            if refs and refs & s["_refs"]:
                match = s
                break
            if _close(it.get("published"), s.get("published")) and \
                    SequenceMatcher(None, _norm(it["title"]), _norm(s["title"])).ratio() >= 0.82:
                match = s
                break
        if match:
            urls = {x["url"] for x in match["sources"]}
            match["sources"] += [x for x in it["sources"] if x["url"] not in urls]
            match["_refs"] |= refs
            match["deadlines"] += [d for d in it.get("deadlines", []) if d not in match["deadlines"]]
            match["preset_tags"] = sorted(set(match.get("preset_tags", [])) | set(it.get("preset_tags", [])))
            if not match.get("summary") and it.get("summary"):
                match["summary"] = it["summary"]
            if it.get("published") and (not match.get("published") or it["published"] < match["published"]):
                match["published"] = it["published"]
        else:
            s = dict(it)
            s["sources"] = list(it["sources"])
            s["deadlines"] = list(it.get("deadlines", []))
            s["_refs"] = refs
            stories.append(s)
    for s in stories:
        s.pop("_refs", None)
    return stories


def merge_with_previous(new_items, previous_items, keep_days=120, cap=500):
    by_id = {i["id"]: i for i in previous_items or []}
    for it in new_items:
        old = by_id.get(it["id"])
        if old and old.get("llm"):
            it["llm"] = old["llm"]
        by_id[it["id"]] = it
    cutoff = (date.today() - timedelta(days=keep_days)).isoformat()
    kept = [i for i in by_id.values() if (i.get("published") or "9999") >= cutoff]
    kept.sort(key=lambda i: i.get("published") or "", reverse=True)
    return kept[:cap]
