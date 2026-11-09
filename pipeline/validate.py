"""Check every output file against its schema and report stale sources. Exit 1 on schema errors."""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from .util import read_json

DATE = {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}"}
META = {"type": "object", "required": ["generated_at", "sample"]}
VB_CELL = {"type": ["string", "null"], "pattern": r"^(C|U|\d{4}-\d{2}-\d{2})$"}
VB_CHART = {"type": "object", "additionalProperties": {"type": "object", "additionalProperties": VB_CELL}}
SOURCE = {"type": "object", "required": ["name", "url"], "properties": {"url": {"type": ["string", "null"]}}}
DEADLINE = {"type": "object", "required": ["date", "type", "label", "confidence"], "properties": {"date": DATE}}

SCHEMAS = {
    "visa_bulletin/latest.json": {
        "type": "object", "required": ["month", "url", "charts", "meta"],
        "properties": {"month": {"type": "string", "pattern": r"^\d{4}-\d{2}$"}, "meta": META,
                       "charts": {"type": "object", "required": ["eb", "fb"], "additionalProperties": {
                           "type": "object", "required": ["fad", "dff"], "properties": {"fad": VB_CHART, "dff": VB_CHART}}}}},
    "processing_times/latest.json": {
        "type": "object", "required": ["forms", "meta"],
        "properties": {"meta": META, "forms": {"type": "array", "minItems": 1, "items": {
            "type": "object", "required": ["form", "label", "low_months", "high_months"],
            "properties": {"low_months": {"type": "number", "minimum": 0}, "high_months": {"type": "number", "minimum": 0}}}}}},
    "wait_times/latest.json": {
        "type": "object", "required": ["posts", "meta"],
        "properties": {"meta": META, "posts": {"type": "array", "minItems": 20, "items": {"type": "object", "required": ["post"]}}}},
    "dol/latest.json": {
        "type": "object", "required": ["tables", "meta"],
        "properties": {"meta": META, "tables": {"type": "array", "minItems": 1}}},
    "news.json": {
        "type": "object", "required": ["items", "meta"],
        "properties": {"meta": META, "items": {"type": "array", "items": {
            "type": "object", "required": ["id", "title", "kind", "sources", "tags", "deadlines"],
            "properties": {"title": {"type": "string", "minLength": 5}, "published": {"type": ["string", "null"]},
                           "sources": {"type": "array", "minItems": 1, "items": SOURCE},
                           "deadlines": {"type": "array", "items": DEADLINE}}}}}},
    "deadlines.json": {
        "type": "object", "required": ["items", "meta"],
        "properties": {"meta": META, "items": {"type": "array", "items": DEADLINE}}},
    "changes.json": {"type": "object", "required": ["items", "meta"]},
    "status.json": {"type": "object", "required": ["sources", "meta"]},
}

def check(out):
    out = Path(out)
    errors, warnings = [], []
    for rel, schema in SCHEMAS.items():
        data = read_json(out / rel)
        if data is None:
            warnings.append(f"{rel}: missing")
            continue
        for e in Draft202012Validator(schema).iter_errors(data):
            errors.append(f"{rel}: {'/'.join(map(str, e.path))}: {e.message[:160]}")
    status = (read_json(out / "status.json") or {}).get("sources", {})
    now = datetime.now(timezone.utc)
    for sid, st in status.items():
        last, max_age = st.get("last_success"), st.get("max_age_hours")
        if not last:
            warnings.append(f"{sid}: never succeeded ({st.get('error')})")
        elif max_age and (now - datetime.fromisoformat(last)).total_seconds() > max_age * 3600:
            warnings.append(f"{sid}: stale, last success {last} ({st.get('error')})")
    return errors, warnings


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default=str(Path(__file__).resolve().parent.parent / "web" / "public" / "data"))
    ap.add_argument("--strict", action="store_true", help="also fail on stale sources")
    a = ap.parse_args(argv)
    errors, warnings = check(a.out)
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    if errors or (a.strict and warnings):
        return 1
    print("data valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
