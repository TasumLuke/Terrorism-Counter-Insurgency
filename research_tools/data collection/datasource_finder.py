#!/usr/bin/env python3
import json
import os
import re
import time
import csv
from urllib.request import urlopen, Request
from urllib.parse import urlencode, quote_plus
from urllib.error import URLError, HTTPError

# ucdp conflict IDs for our cases
UCDP_IDS = {
    "naga (NSCN)": 343,
    "mizo (MNF)":  226,
    "naga (NNC)":  203,
}

MHA_DOCS = {
    "NE Insurgency Profile 2023": "https://www.mha.gov.in/sites/default/files/2023-03/NE_Insurgency_profile.pdf",
    "MHA Annual Report 2022-23":  "https://www.mha.gov.in/sites/default/files/MHA-AR2223-070923.pdf",
}

WIKI_PAGES = [
    "National Socialist Council of Nagaland",
    "Mizo National Front",
    "Naga insurgency",
    "1986 Mizoram Peace Accord",
    "NSCN–Khaplang",
]


def get_json(url, delay=0.8):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    time.sleep(delay)
    try:
        with urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except HTTPError as e:
        print(f"  HTTP {e.code}")
    except URLError as e:
        print(f"  {e.reason}")
    except json.JSONDecodeError:
        print("  response wasn't JSON")
    return None


def ucdp_india_conflicts():
    url = "https://ucdpapi.pcr.uu.se/api/conflicts/23.1?location=India&pagesize=50"
    print("  querying ucdp for India conflicts ...")
    data = get_json(url)
    if not data or "Result" not in data:
        print("  nothing"); return

    for c in data["Result"]:
        cid   = c.get("ConflictId", "?")
        name  = c.get("Conflict", "?")
        start = str(c.get("StartDate", "?"))[:4]
        end   = str(c.get("EndDate", ""))[:4] or "ongoing"
        print(f"  [{cid:>5}]  {name:<55}  {start}–{end}")


def ucdp_fatalities(conflict_id, label="conflict"):
    url = f"https://ucdpapi.pcr.uu.se/api/gedevents/23.1?ConflictId={conflict_id}&pagesize=1000"
    print(f"  pulling ucdp fatalities for conflict {conflict_id} ...")
    data = get_json(url)
    if not data or "Result" not in data:
        print("  nothing"); return []
    by_year = {}
    for ev in data["Result"]:
        y = ev.get("year")
        if y:
            by_year.setdefault(int(y), 0)
            by_year[int(y)] += ev.get("best", 0) or 0

    rows = sorted(by_year.items())
    print(f"\n  {'year':<6} {'best estimate':>14}")
    print("  " + "─"*22)
    for y, v in rows:
        print(f"  {y:<6} {v:>14}")

    os.makedirs("downloads", exist_ok=True)
    path = f"downloads/ucdp_{label}_{conflict_id}.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year", "best_fatalities"])
        w.writerows(rows)
    print(f"\n  → {path}")
    return rows
    
def ucdp_actor_search(fragment):
    enc = quote_plus(fragment)
    url = f"https://ucdpapi.pcr.uu.se/api/actors/23.1?ActorName={enc}&pagesize=20"
    print(f"  searching for '{fragment}' ...")
    data = get_json(url)
    if not data or "Result" not in data:
        print("  nothing"); return
    for a in data["Result"][:10]:
        print(f"  [{a.get('ActorId','?')}]  {a.get('ActorName','?')}")

def gdelt_timeline(query, start="1997", end="2023"):
    params = urlencode({
        "query": query,
        "mode":  "timelinevolnorm",
        "format": "json",
        "startdatetime": f"{start}0101000000",
        "enddatetime":   f"{end}1231235959",
    })
    url = f"https://api.gdeltproject.org/api/v2/doc/doc?{params}"
    print(f"  gdelt: {query!r}")
    data = get_json(url, delay=1.5)
    if not data:
        print("  no data"); return

    timeline = data.get("timeline", [{}])[0].get("data", [])
    if not timeline:
        print("  empty timeline"); return

    ranked = sorted(timeline, key=lambda x: x.get("value", 0), reverse=True)
    print(f"\n  top peaks:")
    for item in ranked[:12]:
        date  = item.get("date", "")[:8]
        v     = item.get("value", 0)
        bar   = "█" * int(v * 40)
        print(f"  {date}  {bar} {v:.4f}")

    os.makedirs("downloads", exist_ok=True)
    fname = "downloads/gdelt_" + re.sub(r"[^a-z0-9]", "_", query.lower()[:30]) + ".json"
    with open(fname, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\n  → {fname}")


def download_mha():
    os.makedirs("downloads/mha", exist_ok=True)
    for label, url in MHA_DOCS.items():
        fname = re.sub(r"[^a-z0-9]", "_", label.lower()) + ".pdf"
        path  = f"downloads/mha/{fname}"
        print(f"  downloading {label} ...")
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urlopen(req, timeout=30) as r, open(path, "wb") as f:
                f.write(r.read())
            print(f"  → {path}")
        except Exception as e:
            print(f"  failed: {e}")


def wiki_revisions(page):
    params = urlencode({
        "action":  "query",
        "titles":  page,
        "prop":    "revisions",
        "rvprop":  "timestamp",
        "rvlimit": "max",
        "format":  "json",
    })
    url = f"https://en.wikipedia.org/w/api.php?{params}"
    time.sleep(0.5)
    data = get_json(url, delay=0)
    if not data: return

    pages_d = data.get("query", {}).get("pages", {})
    for _, p in pages_d.items():
        revs = p.get("revisions", [])
        by_year = {}
        for r in revs:
            y = r.get("timestamp", "")[:4]
            if y: by_year[y] = by_year.get(y, 0) + 1
        print(f"\n  {page}  ({len(revs)} total edits)")
        for y in sorted(by_year)[-12:]:
            bar = "▪" * min(by_year[y], 50)
            print(f"  {y}  {bar} ({by_year[y]})")

MENU = """
  datasource finder
  
  ucdp
  1  all ucdp india conflicts
  2  fatalities : nagaland NSCN (id 343)
  3  fatalities :  mizoram MNF (id 226)
  4  actor search

  gdelt
  5  timeline :  nagaland ceasefire
  6  timeline :  mizo peace accord
  7  custom query

  mha / other
  8  download mha pdf docs
  9  wikipedia revision counts :  all pages
  w  wikipedia  : pick one page

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
            ucdp_india_conflicts()
        elif ch == "2":
            ucdp_fatalities(343, "nagaland")
        elif ch == "3":
            ucdp_fatalities(226, "mizoram")
        elif ch == "4":
            q = input("  actor fragment: ").strip()
            if q: ucdp_actor_search(q)
        elif ch == "5":
            gdelt_timeline("Nagaland ceasefire NSCN")
        elif ch == "6":
            gdelt_timeline("Mizoram peace accord Laldenga")
        elif ch == "7":
            q = input("  query: ").strip()
            if q: gdelt_timeline(q)
        elif ch == "8":
            download_mha()
        elif ch == "9":
            for p in WIKI_PAGES:
                wiki_revisions(p)
        elif ch == "w":
            for i, p in enumerate(WIKI_PAGES, 1):
                print(f"  {i}. {p}")
            try:
                wiki_revisions(WIKI_PAGES[int(input("  pick: ").strip()) - 1])
            except (ValueError, IndexError):
                print("  bad choice")
        elif ch == "q":
            break
        else:
            print("  ?")
        print()
main()
