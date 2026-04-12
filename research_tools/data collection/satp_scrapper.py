#!/usr/bin/env python3
import csv
import json
import os
import re
import time
from html.parser import HTMLParser
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

BASE = "https://www.satp.org"
pages = {
    # assessment pages
    "nagaland_assess":  "/terrorism-assessment/india-insurgencynortheast-nagaland",
    "mizoram_assess":   "/terrorism-assessment/india-insurgencynortheast-mizoram",

    # faction profiles
    "nscn_im":  "/terrorist-profile/india/national-socialist-council-of-nagaland-isak-muivah-nscn-im",
    "nscn_k":   "/terrorist-profile/india/national-socialist-council-of-nagaland-khaplang-nscn-k",
    "nscn_kk":  "/terrorist-profile/india/nationalist-socialist-council-of-nagaland-khole-kitovi-nscn-kk",
    "nscn_r":   "/terrorist-profile/india/nationalist-socialist-council-of-nagaland-reformation-nscn-r",
    "nscn_u":   "/terrorist-profile/india/national-socialist-council-of-nagaland-unification-nscn-u",

    # backgrounders (MNF has no profile page, only backgrounder)
    "mnf_bg":   "/backgrounder/india-insurgencynortheast-mizoram",
    "naga_bg":  "/backgrounder/india-insurgencynortheast-nagaland",
}


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self._table = []
        self._row = []
        self._cell = ""
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":            self._table = []
        elif tag == "tr":             self._row = []
        elif tag in ("td", "th"):     self._in_cell = True; self._cell = ""

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self._in_cell = False
            self._row.append(self._cell.strip())
        elif tag == "tr":
            if self._row: self._table.append(self._row)
        elif tag == "table":
            if self._table: self.tables.append(self._table)
            self._table = []

    def handle_data(self, data):
        if self._in_cell: self._cell += data

def fetch(path, delay=1.5):
    url = BASE + path if path.startswith("/") else path
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    time.sleep(delay)
    try:
        with urlopen(req, timeout=15) as r:
            enc = r.headers.get_content_charset() or "utf-8"
            return r.read().decode(enc, errors="replace")
    except HTTPError as e:
        print(f"  HTTP {e.code}  {url}")
    except URLError as e:
        print(f"  error: {e.reason}")
    return None

def get_tables(html):
    p = TableParser()
    p.feed(html)
    return p.tables


def has_years(table):
    for row in table:
        for cell in row:
            if re.search(r"19[89]\d|200\d|201\d|202\d", cell):
                return True
    return False

def save_csv(rows, fname):
    os.makedirs("satp_data", exist_ok=True)
    path = os.path.join("satp_data", fname)
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    print(f"  → {path}")


def scrape_assessment(key):
    path = pages.get(key)
    if not path:
        print(f"  unknown: {key}"); return

    print(f"  fetching {BASE + path} ...")
    html = fetch(path)
    if not html: return

    tables = [t for t in get_tables(html) if has_years(t)]
    if not tables:
        print(f"  no year tables found"); return

    t = tables[0]
    print(f"  table: {len(t)} rows x {len(t[0])} cols")
    print("  preview:")
    for row in t[:4]:
        print("    " + " | ".join(c[:22] for c in row))
    save_csv(t, f"{key}.csv")

def scrape_profile(key):
    path = pages.get(key)
    if not path:
        print(f"  no path for {key}"); return

    print(f"  fetching {key} ...")
    html = fetch(path)
    if not html: return

    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)

    cadre_hits = re.findall(r"(\d[\d,]*)\s*(?:cadres?|members?|militants?|fighters?|strength)", text, re.I)
    cf_hits    = re.findall(r"(\w+\s+\d{4}|\d{4})\s*[^.]{0,80}ceasefire", text, re.I)
    split_hits = re.findall(r"(\d{4})[^.]{0,60}(?:split|splinter|broke away|faction)", text, re.I)

    result = {
        "key":           key,
        "url":           BASE + path,
        "cadre_mentions": cadre_hits[:8],
        "ceasefire_hits": cf_hits[:8],
        "split_dates":   split_hits[:6],
        "excerpt":       text[600:2000],
    }

    os.makedirs("satp_data", exist_ok=True)
    out = os.path.join("satp_data", f"{key}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"  cadre:     {cadre_hits[:4]}")
    print(f"  ceasefire: {cf_hits[:4]}")
    print(f"  splits:    {split_hits[:4]}")
    print(f"  → {out}")


MENU = """
  satp scraper
  
  assessment pages
  1  nagaland
  2  mizoram

  faction profiles  (verified urls)
  3  nscn-im
  4  nscn-k
  5  nscn-kk
  6  nscn-r
  7  nscn-u
  8  mnf backgrounder
  9  nagaland backgrounder
  a  all profiles

  s  show all registered urls
  q  quit
"""
def main():
    print(MENU)
    while True:
        try:
            ch = input("> ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print(); break

        if   ch == "1": scrape_assessment("nagaland_assess")
        elif ch == "2": scrape_assessment("mizoram_assess")
        elif ch == "3": scrape_profile("nscn_im")
        elif ch == "4": scrape_profile("nscn_k")
        elif ch == "5": scrape_profile("nscn_kk")
        elif ch == "6": scrape_profile("nscn_r")
        elif ch == "7": scrape_profile("nscn_u")
        elif ch == "8": scrape_profile("mnf_bg")
        elif ch == "9": scrape_profile("naga_bg")
        elif ch == "a":
            for k in ("nscn_im", "nscn_k", "nscn_kk", "nscn_r", "nscn_u", "mnf_bg"):
                scrape_profile(k)
                print()
        elif ch == "s":
            for k, v in pages.items():
                print(f"  {k:<18}  {BASE + v}")
        elif ch == "q":
            break
        else:
            print("  ?")
        print()


main()
