"""Regenerate sample fixtures: python tests/make_fixtures.py. All values are invented samples."""
import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path

F = Path(__file__).parent / "fixtures"
T = date.today()


def d(n):
    return (T - timedelta(days=n)).isoformat()


def f(n):
    return (T + timedelta(days=n)).isoformat()


def vb_table(kind, title, rows):
    head = ("Family-Sponsored" if kind == "fb" else "Employment-based")
    cols = ["All Chargeability Areas Except Those Listed", "CHINA-mainland born", "INDIA", "MEXICO", "PHILIPPINES"]
    h = "<tr>" + f"<td><b>{head}</b></td>" + "".join(f"<td><b>{c}</b></td>" for c in cols) + "</tr>"
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<p><b>{title}</b></p><table border='1'><tbody>{h}{body}</tbody></table>"


FB_FAD = [["F1", "08NOV16", "08NOV16", "08NOV16", "22APR05", "01MAR13"], ["F2A", "01JAN23", "01JAN23", "01JAN23", "01FEB22", "01JAN23"],
          ["F2B", "22SEP16", "22SEP16", "22SEP16", "01OCT08", "22OCT12"], ["F3", "22JUL11", "22JUL11", "22JUL11", "22MAY01", "01OCT03"],
          ["F4", "08APR08", "08APR08", "08JAN06", "30APR01", "01JUN05"]]
FB_DFF = [["F1", "01SEP17", "01SEP17", "01SEP17", "01APR06", "01JAN15"], ["F2A", "01JUL25", "01JUL25", "01JUL25", "01JUL25", "01JUL25"],
          ["F2B", "15MAR17", "15MAR17", "15MAR17", "01OCT09", "01OCT13"], ["F3", "01FEB12", "01FEB12", "01FEB12", "01APR02", "01AUG04"],
          ["F4", "08JAN09", "08JAN09", "15AUG06", "01AUG01", "01JAN06"]]
EB_FAD = [["1st", "C", "08FEB23", "15FEB22", "C", "C"], ["2nd", "01APR24", "01JAN21", "01JAN13", "01APR24", "15OCT23"],
          ["3rd", "01APR23", "01APR21", "15NOV13", "01APR23", "01JAN23"], ["Other Workers", "01JUL21", "01DEC17", "15NOV13", "01APR21", "01JUL21"],
          ["4th", "01JAN21", "01JAN21", "01JAN21", "01JAN21", "01JAN21"], ["Certain Religious Workers", "U", "U", "U", "U", "U"],
          ["5th Unreserved (including C5, T5, I5, R5)", "C", "22JAN16", "01NOV21", "C", "C"],
          ["5th Set Aside: Rural (20%)", "C", "C", "C", "C", "C"]]
EB_DFF = [["1st", "C", "01AUG23", "01AUG22", "C", "C"], ["2nd", "15OCT24", "01SEP21", "15JUL13", "15OCT24", "15OCT24"],
          ["3rd", "01OCT23", "01OCT21", "15APR14", "01OCT23", "01AUG23"], ["Other Workers", "01OCT21", "01JUN18", "15APR14", "01OCT21", "01OCT21"],
          ["4th", "01MAR21", "01MAR21", "01MAR21", "01MAR21", "01MAR21"], ["Certain Religious Workers", "01MAR21", "01MAR21", "01MAR21", "01MAR21", "01MAR21"],
          ["5th Unreserved (including C5, T5, I5, R5)", "C", "01JAN17", "01APR22", "C", "C"], ["5th Set Aside: Rural (20%)", "C", "C", "C", "C", "C"]]
PREV = {"2nd": ["01FEB24", "01JAN21", "01DEC12", "01FEB24", "15OCT23"], "3rd": ["01MAR23", "01FEB21", "15NOV13", "01MAR23", "01APR23"],
        "1st": ["C", "08JAN23", "15DEC21", "C", "C"]}


def bulletin(prev=False):
    def shift(rows):
        return [[r[0]] + PREV[r[0]] if prev and r[0] in PREV else r for r in rows]
    parts = ["<html><body><h1>Visa Bulletin</h1><p>Sample fixture with invented values.</p>",
             "<table><tr><td>Unrelated layout table</td></tr></table>",
             vb_table("fb", "A. FINAL ACTION DATES FOR FAMILY-SPONSORED PREFERENCE CASES", FB_FAD),
             vb_table("fb", "B. DATES FOR FILING FAMILY-SPONSORED VISA APPLICATIONS", FB_DFF),
             vb_table("eb", "A. FINAL ACTION DATES FOR EMPLOYMENT-BASED PREFERENCE CASES", shift(EB_FAD)),
             vb_table("eb", "B. DATES FOR FILING OF EMPLOYMENT-BASED VISA APPLICATIONS", EB_DFF),
             "</body></html>"]
    return "\n".join(parts)


def index():
    from pipeline.util import MONTH_NAMES
    m = T.month % 12 + 1
    y = T.year + (T.month == 12)
    links = []
    for mm, yy in ((T.month, T.year), (m, y)):
        fy = yy + 1 if mm >= 10 else yy
        links.append(f'<li><a href="/content/travel/en/legal/visa-law0/visa-bulletin/{fy}/visa-bulletin-for-{MONTH_NAMES[mm - 1]}-{yy}.html">Visa Bulletin For {MONTH_NAMES[mm - 1].title()} {yy}</a></li>')
    return f"<html><body><h2>Current and upcoming bulletins</h2><ul>{''.join(links)}</ul></body></html>"


POSTS = [("Chennai (Madras)", "7.5 Months", "7.5 months", "3.5 months", "2.5 months", "NA"), ("Hyderabad", "8 Months", "8 months", "4 months", "3 months", "NA"),
         ("Mumbai", "7 Months", "7 months", "2.5 months", "2 months", "1 month"), ("New Delhi", "6 Months", "6 months", "2 months", "1.5 months", "NA"),
         ("Kolkata", "5 Months", "5 months", "1.5 months", "1 month", "NA"), ("Chengdu", "NA", "NA", "NA", "NA", "NA"),
         ("Beijing", "1 Month", "1 month", "0.5 months", "1 month", "2 weeks"), ("Shanghai", "1.5 Months", "1.5 months", "1 month", "1 month", "NA"),
         ("Mexico City", "14 Months", "14 months", "1.5 months", "3 months", "NA"), ("Monterrey", "11 Months", "11 months", "1 month", "2 months", "NA"),
         ("Manila", "6 Months", "6 months", "1 month", "2 months", "1 month"), ("Toronto", "18 Months", "18 months", "5 months", "12 months", "NA"),
         ("Vancouver", "15 Months", "15 months", "4 months", "9 months", "NA"), ("London", "1.5 Months", "1.5 months", "2 weeks", "1 month", "1 week"),
         ("Frankfurt", "2 Months", "2 months", "1 month", "1 month", "NA"), ("Lagos", "12 Months", "12 months", "4 months", "6 months", "NA"),
         ("Bogota", "16 Months", "16 months", "2 months", "4 months", "NA"), ("Sao Paulo", "3 Months", "3 months", "1 month", "1 month", "NA"),
         ("Seoul", "1 Month", "1 month", "2 weeks", "1 month", "1 week"), ("Tokyo", "1 Month", "1 month", "2 weeks", "2 weeks", "1 week"),
         ("Dubai", "4 Months", "4 months", "1.5 months", "2 months", "NA"), ("Istanbul", "9 Months", "9 months", "2 months", "3 months", "NA"),
         ("Ho Chi Minh City", "5 Months", "5 months", "2 months", "2 months", "NA"), ("Dhaka", "10 Months", "10 months", "3 months", "4 months", "NA"),
         ("Karachi", "11 Months", "11 months", "3 months", "5 months", "NA")]


def wait_html(prev=False):
    hdr = ["City/Post", "Interview Required (B1/B2) Average wait times", "Interview Required (B1/B2) Next available appointment",
           "Interview Required (F,M,J) Next available appointment", "Interview Required Petition-Base (H,L,O,P,Q) Next available appointment",
           "Interview Required Crew and Transit (C,D,C1/D) Next available appointment"]
    rows = []
    for p in POSTS:
        p = list(p)
        if prev and p[0].startswith(("Chennai", "Hyderabad", "Toronto")):
            p[4] = {"Chennai (Madras)": "1.5 months", "Hyderabad": "2 months", "Toronto": "10 months"}[p[0]]
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in p) + "</tr>")
    return ("<html><body><h1>Global Visa Wait Times</h1><table><thead><tr>" + "".join(f"<th>{h}</th>" for h in hdr)
            + "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></body></html>")


PT = [("I-485", "IOE", "Employment-based adjustment", 8, "Months", 22, "Months"), ("I-485", "NBC", "Family-based adjustment", 9, "Months", 18, "Months"),
      ("I-765", "IOE", "Based on a pending I-485", 3, "Months", 7, "Months"), ("I-131", "IOE", "Advance parole", 4, "Months", 9, "Months"),
      ("I-140", "TSC", "Regular processing", 6, "Months", 11, "Months"), ("I-140", "NSC", "Regular processing", 7, "Months", 10.5, "Months"),
      ("I-129", "CSC", "H-1B extension", 2, "Months", 6, "Months"), ("I-539", "VSC", "H-4 / L-2 extension", 4, "Months", 10, "Months"),
      ("I-130", "NBC", "Spouse of US citizen", 10, "Months", 16, "Months"), ("I-751", "IOE", "Remove conditions", 14, "Months", 24, "Months"),
      ("I-90", "NBC", "Renew or replace green card", 6, "Months", 12, "Months"), ("N-400", "IOE", "Naturalization", 5, "Months", 10, "Months"),
      ("I-526E", "IPO", "Investor petition", 12, "Months", 30, "Months"), ("I-821D", "IOE", "DACA renewal", 2, "Weeks", 3, "Months")]


def uscis_db(path, prev=False):
    path.unlink(missing_ok=True)
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE offices(code TEXT PRIMARY KEY, description TEXT)")
    con.execute("CREATE TABLE processing_time(form_name TEXT, office_code TEXT, form_note_en TEXT, form_note_es TEXT, form_subtype TEXT, publication_date TEXT,"
                " range_upper REAL, range_upper_unit TEXT, range_lower REAL, range_lower_unit TEXT, service_request_date TEXT, subtype_info_en TEXT,"
                " subtype_info_es TEXT, subtype_note_en TEXT, subtype_note_es TEXT)")
    for c, n in [("IOE", "Online / ELIS"), ("NBC", "National Benefits Center"), ("TSC", "Texas Service Center"), ("NSC", "Nebraska Service Center"),
                 ("CSC", "California Service Center"), ("VSC", "Vermont Service Center"), ("IPO", "Immigrant Investor Program Office")]:
        con.execute("INSERT INTO offices VALUES (?,?)", (c, n))
    for i, (form, off, sub, lo, lou, hi, hiu) in enumerate(PT):
        if prev:
            hi = {"I-140": hi + 1, "I-485": hi + 0.5, "I-765": hi - 0.5, "I-539": hi - 1}.get(form, hi)
        con.execute("INSERT INTO processing_time VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (form, off, None, None, f"{form}-{i}", d(35 if prev else 5), hi, hiu, lo, lou, None, sub, None, None, None))
    con.commit()
    con.close()


def fr(i):
    docs = [
        [{"title": "Sample: Modernizing H-1B Requirements and Cap Selection", "abstract": "Sample proposed rule changing how H-1B cap registrations are selected.",
          "document_number": "2026-24518", "html_url": "https://www.federalregister.gov/documents/sample-1", "publication_date": d(3), "type": "Proposed Rule",
          "effective_on": None, "comments_close_on": f(57), "agencies": [{"name": "U.S. Citizenship and Immigration Services"}]},
         {"title": "Sample: USCIS Fee Schedule Adjustment for Employment Authorization", "abstract": "Sample final rule adjusting I-765 and I-131 filing fees.",
          "document_number": "2026-23001", "html_url": "https://www.federalregister.gov/documents/sample-2", "publication_date": d(10), "type": "Rule",
          "effective_on": f(50), "comments_close_on": None, "agencies": [{"name": "U.S. Citizenship and Immigration Services"}]}],
        [{"title": "Sample: Extension of Temporary Protected Status Designation", "abstract": "Sample notice extending a TPS designation for 18 months.",
          "document_number": "2026-22410", "html_url": "https://www.federalregister.gov/documents/sample-3", "publication_date": d(15), "type": "Notice",
          "effective_on": f(20), "comments_close_on": None, "agencies": [{"name": "Homeland Security Department"}]}],
        [{"title": "Sample: Schedule of Fees for Consular Services, Nonimmigrant Visa Application Fee", "abstract": "Sample rule on visa application fees.",
          "document_number": "2026-21877", "html_url": "https://www.federalregister.gov/documents/sample-4", "publication_date": d(20), "type": "Rule",
          "effective_on": f(10), "comments_close_on": None, "agencies": [{"name": "State Department"}]}],
        [{"title": "Sample: Labor Certification Process for Temporary Agricultural Employment (H-2A)", "abstract": "Sample proposed rule on H-2A wage methodology.",
          "document_number": "2026-20010", "html_url": "https://www.federalregister.gov/documents/sample-5", "publication_date": d(25), "type": "Proposed Rule",
          "effective_on": None, "comments_close_on": f(5), "agencies": [{"name": "Labor Department"}]}],
        [], [],
        [{"title": "Sample: Proclamation on Visa Integrity Screening", "abstract": "Sample presidential proclamation on entry screening.",
          "document_number": "2026-19555", "html_url": "https://www.federalregister.gov/documents/sample-6", "publication_date": d(30), "type": "Presidential Document",
          "effective_on": d(28), "comments_close_on": None, "agencies": [{"name": "Executive Office of the President"}]}],
    ]
    return {"count": len(docs[i]), "results": docs[i]}


def state_news():
    items = [("sample-interview-waiver-update", "Sample: Interview Waiver Update for Nonimmigrant Visa Applicants", 2,
              "Sample text. The updated policy takes effect on " + (T + timedelta(days=24)).strftime("%B %d, %Y") + " for all posts."),
             ("sample-visa-bulletin-release", "Sample: Visa Bulletin for Next Month Now Available", 6, "Sample text about the new bulletin."),
             ("sample-social-media-vetting", "Sample: Expanded Online Presence Review for H-1B and H-4 Applicants", 12, "Sample text about vetting and appointment rescheduling.")]
    lis = "".join(f'<li><a href="/content/travel/en/News/visas-news/{s}.html">{t}</a><span>{(T - timedelta(days=n)).strftime("%B %d, %Y")}</span><p>{p}</p></li>'
                  for s, t, n, p in items)
    return f'<html><body><nav><a href="/content/travel/en/News/visas-news.html">Visa News</a></nav><ul>{lis}</ul></body></html>'


def uscis_news():
    items = [("news-releases/sample-h-1b-registration-dates", "Sample: USCIS Announces FY 2028 H-1B Cap Season Registration Dates", 1,
              "Sample text. The registration period opens " + (T + timedelta(days=110)).strftime("%B %d, %Y") + " and closes "
              + (T + timedelta(days=127)).strftime("%B %d, %Y") + "."),
             ("alerts/sample-ead-automatic-extension", "Sample: Updated Guidance on Automatic Extension of Employment Authorization Documents", 4, "Sample alert text."),
             ("news-releases/sample-fee-schedule-adjustment", "Sample: USCIS Fee Schedule Adjustment for Employment Authorization", 9, "Sample text about the fee rule."),
             ("alerts/sample-civics-test", "Sample: Civics Test Update for Naturalization Applicants", 18, "Sample alert for N-400 applicants.")]
    rows = "".join(f'<div class="views-row"><time datetime="{(T - timedelta(days=n)).isoformat()}T12:00:00Z">x</time><a href="/newsroom/{s}">{t}</a><p>{p}</p></div>'
                   for s, t, n, p in items)
    return f"<html><body>{rows}</body></html>"


def sits():
    t = (T - timedelta(days=7))
    return (f'<html><body><article><a href="https://studyinthestates.dhs.gov/{t.year}/{t.month:02d}/sample-stem-opt-reporting-reminder">'
            f'Sample: Reminder on STEM OPT Reporting Requirements for F-1 Students</a><time datetime="{t.isoformat()}">x</time></article></body></html>')


def dol():
    return ("<html><body><h2>Processing times as of " + T.strftime("%B %d, %Y") + "</h2>"
            "<h3>PERM Processing Times</h3><table><tr><th>Processing Queue</th><th>Priority Date</th><th>Average Days</th></tr>"
            "<tr><td>Analyst Review</td><td>" + (T - timedelta(days=470)).strftime("%B %Y") + "</td><td>470</td></tr>"
            "<tr><td>Audit Review</td><td>" + (T - timedelta(days=520)).strftime("%B %Y") + "</td><td>N/A</td></tr>"
            "<tr><td>Reconsideration Request</td><td>" + (T - timedelta(days=240)).strftime("%B %Y") + "</td><td>N/A</td></tr></table>"
            "<h3>Prevailing Wage Processing Times</h3><table><tr><th>Determination</th><th>Month</th><th>Average Days</th></tr>"
            "<tr><td>H-1B (OEWS)</td><td>" + (T - timedelta(days=185)).strftime("%B %Y") + "</td><td>185</td></tr>"
            "<tr><td>PERM (OEWS)</td><td>" + (T - timedelta(days=190)).strftime("%B %Y") + "</td><td>190</td></tr></table></body></html>")


def main():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    F.mkdir(parents=True, exist_ok=True)
    (F / "visa_bulletin_index.html").write_text(index())
    (F / "visa_bulletin.html").write_text(bulletin())
    (F / "visa_bulletin_prev.html").write_text(bulletin(prev=True))
    (F / "wait_times.html").write_text(wait_html())
    (F / "wait_times_prev.html").write_text(wait_html(prev=True))
    (F / "dol_flag.html").write_text(dol())
    uscis_db(F / "uscis_times.db")
    uscis_db(F / "uscis_times_prev.db", prev=True)
    for i in range(7):
        (F / f"federal_register_{i}.json").write_text(json.dumps(fr(i), indent=1))
    (F / "state_visa_news.html").write_text(state_news())
    (F / "uscis_news.html").write_text(uscis_news())
    (F / "study_in_the_states.html").write_text(sits())
    print("fixtures written to", F)


if __name__ == "__main__":
    main()
