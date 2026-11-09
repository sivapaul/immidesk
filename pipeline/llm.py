"""Optional AI deadline extraction. Runs only when ANTHROPIC_API_KEY is set, once per item."""
import json
import os
import re

import requests

API = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("IMMIDESK_LLM_MODEL", "claude-haiku-5-5")
HINT = re.compile(r"effective|deadline|comment|registration|window|expire|begin|starting|until|through|by \w+ \d", re.I)

PROMPT = """You extract action dates from US immigration news for a public dashboard.
Return only JSON: {"deadlines":[{"date":"YYYY-MM-DD","type":"effective|comments_close|registration_opens|registration_closes|filing_window|expires|deadline","label":"short plain-English label"}]}
Only include dates explicitly stated in the text. If none, return {"deadlines":[]}.

Title: %s
Published: %s
Text: %s"""


def enabled():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def extract(item, max_items_state):
    if "llm" in item or max_items_state["left"] <= 0:
        return item
    if item.get("deadlines") or not HINT.search(f"{item['title']} {item.get('summary', '')}"):
        return item
    max_items_state["left"] -= 1
    try:
        r = requests.post(API, timeout=60, headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json",
        }, json={"model": MODEL, "max_tokens": 400, "messages": [{"role": "user", "content": PROMPT % (
            item["title"], item.get("published"), item.get("summary", "")[:2000])}]})
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json().get("content", []))
        data = json.loads(text[text.find("{"): text.rfind("}") + 1])
        found = [d for d in data.get("deadlines", []) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.get("date", ""))]
    except Exception as e:
        item["llm"] = {"error": str(e)[:200]}
        return item
    item["llm"] = {"model": MODEL, "deadlines": found}
    return item


def apply(item):
    for d in (item.get("llm") or {}).get("deadlines", []):
        if not any(x["date"] == d["date"] for x in item["deadlines"]):
            item["deadlines"].append({**d, "confidence": "ai", "method": "llm"})
    return item
