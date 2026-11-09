COUNTRY_NAMES = {"all": "Rest of World", "cn": "China", "in": "India", "mx": "Mexico", "ph": "Philippines"}
WATCH = ["EB-1", "EB-2", "EB-3", "F2A", "EB-5 unreserved"]


def _fmt_months(m):
    m = round(abs(m), 1)
    if m < 1:
        return f"{round(m * 30.4)} days"
    return f"{m:g} month" + ("" if m == 1 else "s")


def visa_bulletin(vb):
    out = []
    deltas = (vb or {}).get("deltas") or {}
    moves = []
    for key, d in deltas.items():
        kind, chart, cat, c = key.split(".", 3)
        if chart != "fad" or d == 0:
            continue
        if isinstance(d, str):
            text = f"{cat} {COUNTRY_NAMES[c]} became current" if d == "C" else f"{cat} {COUNTRY_NAMES[c]} became unavailable" if d == "U" else None
            if text:
                moves.append((10, text, "good" if d == "C" else "bad"))
            continue
        weight = abs(d) + (3 if cat in WATCH else 0) + (2 if c in ("in", "cn", "all") else 0) + (4 if d < 0 else 0)
        verb = "advanced" if d > 0 else "moved back"
        moves.append((weight, f"{cat} {COUNTRY_NAMES[c]} {verb} {_fmt_months(d)}", "good" if d > 0 else "bad"))
    moves.sort(key=lambda m: -m[0])
    for _, text, tone in moves[:3]:
        out.append({"area": "Visa Bulletin", "text": text, "tone": tone})
    return out


def processing_times(pt):
    out = []
    deltas = (pt or {}).get("deltas") or {}
    for form, d in sorted(deltas.items(), key=lambda kv: -abs(kv[1]))[:2]:
        if abs(d) < 0.5:
            continue
        out.append({"area": "USCIS", "text": f"{form} processing is {_fmt_months(d)} {'faster' if d < 0 else 'slower'} at the slowest office",
                    "tone": "good" if d < 0 else "bad"})
    return out


def wait_times(wt):
    out = []
    deltas = (wt or {}).get("deltas") or {}
    names = {"h_next": "work visa (H, L, O)", "f_next": "student visa", "b_next": "visitor visa"}
    for key, d in sorted(deltas.items(), key=lambda kv: -abs(kv[1]))[:2]:
        if abs(d) < 14:
            continue
        post, col = key.rsplit(".", 1)
        out.append({"area": "Consulates", "text": f"{post} {names[col]} wait {'grew' if d > 0 else 'dropped'} by {_fmt_months(d / 30.4)}",
                    "tone": "bad" if d > 0 else "good"})
    return out


def build(vb, pt, wt):
    items = visa_bulletin(vb) + processing_times(pt) + wait_times(wt)
    return items[:6]
