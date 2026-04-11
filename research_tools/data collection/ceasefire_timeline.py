#!/usr/bin/env python3

import csv
import json
import os
import re
import time
from urllib.request import urlopen, Request
from urllib.parse import urlencode

# all events that matter for the CPC construction

events = [
    {"date": "1966-02-28", "state": "Mizoram",  "faction": "MNF",     "type": "insurgency_start",     "cf": False, "cf_end": None,       "note": "Operation Jericho. Scroll 2016, The Print 2023."},
    {"date": "1986-06-30", "state": "Mizoram",  "faction": "MNF",     "type": "peace_accord",          "cf": True,  "cf_end": "1986-06-30", "note": "Laldenga signs with Rajiv Gandhi. DIPR Mizoram."},
    {"date": "1988-04-30", "state": "Nagaland", "faction": "NSCN",    "type": "faction_split",         "cf": False, "cf_end": None,       "note": "Khaplang attacks Muivah camp, ~140 killed. IDR 2024."},
    {"date": "1997-08-01", "state": "Nagaland", "faction": "NSCN-IM", "type": "ceasefire_start",       "cf": True,  "cf_end": None,       "note": "ETV Bharat 2020."},
    {"date": "2001-04-28", "state": "Nagaland", "faction": "NSCN-K",  "type": "ceasefire_start",       "cf": True,  "cf_end": "2015-03-27", "note": "SATP NSCN-K profile."},
    {"date": "2002-01-01", "state": "Nagaland", "faction": "NNC-A",   "type": "ceasefire_start",       "cf": True,  "cf_end": None,       "note": "MHA NE insurgency 2023."},
    {"date": "2007-01-01", "state": "Nagaland", "faction": "NSCN-U",  "type": "ceasefire_start",       "cf": True,  "cf_end": None,       "note": "SATP Nagaland assessment 2024."},
    {"date": "2009-01-01", "state": "Nagaland", "faction": "multiple","type": "reconciliation_attempt","cf": False, "cf_end": None,       "note": "28 FNR inter-factional meetings. IDSA 2009."},
    {"date": "2011-06-01", "state": "Nagaland", "faction": "NSCN-KK", "type": "faction_split",         "cf": False, "cf_end": None,       "note": "Eurasia Review 2014."},
    {"date": "2011-06-15", "state": "Nagaland", "faction": "NSCN-KK", "type": "ceasefire_start",       "cf": True,  "cf_end": None,       "note": "SATP Nagaland 2024."},
    {"date": "2014-01-01", "state": "Nagaland", "faction": "NSCN-R",  "type": "ceasefire_start",       "cf": True,  "cf_end": None,       "note": "MHA NE insurgency 2023."},
    {"date": "2015-01-01", "state": "Nagaland", "faction": "ZUF",     "type": "ceasefire_start",       "cf": True,  "cf_end": None,       "note": "MHA NE insurgency 2023."},
    {"date": "2015-03-27", "state": "Nagaland", "faction": "NSCN-K",  "type": "ceasefire_end",         "cf": False, "cf_end": None,       "note": "SATP NSCN-K profile."},
    {"date": "2015-08-03", "state": "Nagaland", "faction": "NSCN-IM", "type": "framework_agreement",   "cf": False, "cf_end": None,       "note": "Terms undisclosed. MHA 2023."},
]

def cpc_for_year(year, state="Nagaland"):
    return sum(
        1 for e in events
        if e["state"] == state
        and e["type"] == "ceasefire_start"
        and int(e["date"][:4]) <= year
        and (e["cf_end"] is None or year <= int(e["cf_end"][:4]))
    )

def print_events(filter_state=None, filter_type=None):
    shown = events
    if filter_state: shown = [e for e in shown if e["state"] == filter_state]
    if filter_type:  shown = [e for e in shown if e["type"]  == filter_type]
    print()
    for e in sorted(shown, key=lambda x: x["date"]):
        dot = "●" if e["cf"] else "○"
        print(f"  {dot} {e['date']}  [{e['state']:<8}]  {e['faction']:<10}  {e['type']}")
        print(f"       {e['note']}")
    print()

def cpc_series(state, start=1963, end=2022):
    rows = [(y, cpc_for_year(y, state)) for y in range(start, end+1)]
    print(f"\n  CPC / {state}")
    for y, c in rows:
        if c > 0 or y >= 1990:
            print(f"  {y}  {'█'*c} ({c})")
    return rows

def export_events():
    os.makedirs("downloads", exist_ok=True)
    path = "downloads/ceasefire_events.csv"
    fields = ["date", "state", "faction", "type", "cf", "cf_end", "note"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(events, key=lambda x: x["date"]))
    print(f"  → {path}")


def export_cpc(state):
    rows = [(y, cpc_for_year(y, state)) for y in range(1963, 2023)]
    os.makedirs("downloads", exist_ok=True)
    path = f"downloads/cpc_{state.lower()}.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year", "cpc"])
        w.writerows(rows)
    print(f"  → {path}")


def wiki_check():
    targets = {
        "NSCN-IM ceasefire":     "National Socialist Council of Nagaland (Isak-Muivah)",
        "NSCN-K ceasefire":      "National Socialist Council of Nagaland–Khaplang",
        "Mizoram Peace Accord":  "Mizoram Peace Accord",
    }
    date_pat = re.compile(
        r"\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}"
        r"|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
        re.I
    )
    for label, page in targets.items():
        params = urlencode({"action": "query", "titles": page, "prop": "extracts", "exintro": True, "explaintext": True, "format": "json"})
        req = Request(f"https://en.wikipedia.org/w/api.php?{params}", headers={"User-Agent": "Mozilla/5.0"})
        time.sleep(0.5)
        try:
            with urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
        except Exception as e:
            print(f"  error: {e}"); continue

        for _, p in data.get("query", {}).get("pages", {}).items():
            text = p.get("extract", "")
            dates = date_pat.findall(text)
            print(f"\n  {label}")
            print(f"  dates found: {dates[:6]}")
            print(f"  excerpt: {text[:250].strip()}")
    print()


def load_acled(path):
    if not os.path.exists(path):
        print(f"  not found: {path}")
        print("  get it from https://acleddata.com/data-export-tool  (free account, filter India)")
        return
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            loc = (row.get("admin1", "") + " " + row.get("location", "")).lower()
            if "nagaland" in loc or "mizoram" in loc:
                rows.append(row)
    print(f"\n  matched {len(rows)} rows")
    by = {}
    for row in rows:
        key = (row.get("admin1", "?"), row.get("year", "?"))
        by[key] = by.get(key, 0) + 1
    print(f"  {'state':<12} {'year':<6} {'events'}")
    for (s, y), c in sorted(by.items()):
        print(f"  {s:<12} {y:<6} {c}")


def add_event():
    e = {}
    e["date"]    = input("  date (YYYY-MM-DD): ").strip()
    e["state"]   = input("  state: ").strip()
    e["faction"] = input("  faction: ").strip()
    e["type"]    = input("  type: ").strip()
    e["note"]    = input("  source/note: ").strip()
    e["cf"]      = input("  ceasefire start? y/n: ").strip().lower() == "y"
    ce = input("  ceasefire end date (blank = ongoing): ").strip()
    e["cf_end"]  = ce or None
    events.append(e)
    print(f"  added {e['date']} {e['faction']}")


MENU = """
  ceasefire timeline
 
  1  all events
  2  nagaland only
  3  ceasefire starts only
  4  wiki date cross-check
  5  export event log csv
  6  cpc series,  nagaland
  7  cpc series,  mizoram
  8  export cpc csv
  9  load acled csv
  a  add event manually
  q  quit
"""


def main():
    print(MENU)
    while True:
        try:
            ch = input("> ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print(); break

        if ch == "1":
            print_events()
        elif ch == "2":
            print_events(filter_state="Nagaland")
        elif ch == "3":
            print_events(filter_type="ceasefire_start")
        elif ch == "4":
            wiki_check()
        elif ch == "5":
            export_events()
        elif ch == "6":
            cpc_series("Nagaland")
        elif ch == "7":
            cpc_series("Mizoram")
        elif ch == "8":
            s = input("  state: ").strip() or "Nagaland"
            export_cpc(s)
        elif ch == "9":
            load_acled(input("  path to acled csv: ").strip())
        elif ch == "a":
            add_event()
        elif ch == "q":
            break
        else:
            print("  ?")
        print()

main()
