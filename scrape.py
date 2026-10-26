#!/usr/bin/env python3
"""Scrape semiconductor internship and new-grad jobs into JOBS.md.

Usage:
    python scrape.py                 # US roles, all sources
    python scrape.py --all-locations # include roles outside the US
    python scrape.py --only NVIDIA,Intel
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

from semijobs.filters import classify, company_key, is_us
from semijobs.report import load_seen, save_seen, write_data, write_markdown
from semijobs.sources import FETCHERS, make_session

ROOT = Path(__file__).resolve().parent


def run_source(source):
    session = make_session()
    start = time.time()
    jobs = FETCHERS[source["ats"]](session, source)
    return jobs, time.time() - start


def merge(jobs, display_names):
    """Collapse duplicates (same company + title), merging their locations.

    Company career pages are listed first in sources.json, so their links win
    over the job-board copy of the same posting. Board company names like
    "Micron Technology, Inc." are renamed to the sources.json name ("Micron").
    """
    merged = {}
    for j in jobs:
        ckey = company_key(j["company"])
        j["company"] = display_names.get(ckey, j["company"])
        key = (ckey, j["title"].lower())
        if key not in merged:
            merged[key] = dict(j)
            continue
        m = merged[key]
        if j["location"] and j["location"] not in m["location"]:
            m["location"] = f"{m['location']}; {j['location']}" if m["location"] else j["location"]
        if not m["posted"] or (j["posted"][:2] == "20" and j["posted"] > m["posted"]):
            m["posted"] = j["posted"] or m["posted"]
    return list(merged.values())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all-locations", action="store_true", help="keep non-US roles too")
    ap.add_argument("--only", help="comma-separated company/source names to run (for testing)")
    ap.add_argument("--workers", type=int, default=8, help="sources fetched in parallel (default 8)")
    ap.add_argument("--output", default=str(ROOT / "JOBS.md"))
    args = ap.parse_args()

    sources = json.loads((ROOT / "sources.json").read_text())["sources"]
    if args.only:
        wanted = {x.strip().lower() for x in args.only.split(",")}
        sources = [s for s in sources if s["company"].lower() in wanted]

    order = {s["company"]: i for i, s in enumerate(sources)}
    raw, errors = [], {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_source, s): s for s in sources}
        for fut in as_completed(futures):
            s = futures[fut]
            try:
                jobs, secs = fut.result()
                for j in jobs:
                    j["_order"] = order[s["company"]]
                raw += jobs
                print(f"  ok   {s['company']:<24} {len(jobs):>5} postings  ({secs:.0f}s)", file=sys.stderr)
            except Exception as e:  # one broken source shouldn't stop the run
                errors[s["company"]] = f"{type(e).__name__}: {e}"
                print(f"  FAIL {s['company']:<24} {errors[s['company']][:120]}", file=sys.stderr)

    picked = []
    for j in sorted(raw, key=lambda j: j["_order"]):
        j["category"] = classify(j["title"], j.get("hint"))
        if j["category"] and (args.all_locations or is_us(j["location"])):
            picked.append(j)
    display_names = {company_key(s["company"]): s["company"] for s in sources}
    jobs = merge(picked, display_names)

    # Remember when each job was first seen, so new ones can be flagged.
    seen_path = ROOT / "data" / "seen.json"
    (ROOT / "data").mkdir(exist_ok=True)
    seen = load_seen(seen_path)
    first_run = seen is None
    seen = seen or {}
    today = date.today().isoformat()
    for j in jobs:
        j["first_seen"] = seen.setdefault(j["url"], today)
    # Forget jobs that have been gone a long time so the file doesn't grow forever.
    current = {j["url"] for j in jobs}
    cutoff = (date.today() - timedelta(days=180)).isoformat()
    seen = {u: d for u, d in seen.items() if u in current or d >= cutoff}
    save_seen(seen_path, seen)

    write_markdown(args.output, jobs, errors, len(sources), show_new=not first_run, us_only=not args.all_locations)
    write_data(ROOT / "data", jobs)
    n_int = sum(j["category"] == "Internship" for j in jobs)
    print(f"\n{n_int} internships, {len(jobs) - n_int} new-grad roles -> {args.output}"
          + (f"  ({len(errors)} sources failed)" if errors else ""), file=sys.stderr)


if __name__ == "__main__":
    main()
