"""Write results: job tables inside README.md, site/jobs.json for the website, and data/jobs.csv."""
import csv
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

NEW_DAYS = 7  # jobs first seen within this many days get a 🆕 badge
START, END = "<!-- JOBS:START -->", "<!-- JOBS:END -->"
FIELDS = ["id", "category", "company", "title", "location", "posted", "first_seen", "url", "via"]


def job_id(url):
    return hashlib.sha1(url.encode()).hexdigest()[:12]


def _cell(text):
    return (text or "").replace("|", "/").replace("\n", " ").strip()


def _sort_key(job):
    posted = job["posted"] if job["posted"][:2] == "20" else "0000"  # "30+ days ago" sorts last
    return (job["first_seen"], posted, job["company"].lower())


def _table(jobs, today, show_new):
    lines = ["| Company | Role | Location | Posted | Apply |", "| --- | --- | --- | --- | :---: |"]
    cutoff = (today - timedelta(days=NEW_DAYS)).isoformat()
    for j in jobs:
        badge = "🆕 " if show_new and j["first_seen"] >= cutoff else ""
        loc = _cell(j["location"]) or "—"
        if len(loc) > 60:
            loc = loc[:57] + "…"
        lines.append(f"| **{_cell(j['company'])}** | {badge}{_cell(j['title'])} | {loc} | "
                     f"{j['posted'] or '—'} | [Apply]({j['url']}) |")
    return "\n".join(lines)


def jobs_markdown(jobs, errors, n_sources, show_new, us_only):
    today = date.today()
    interns = sorted([j for j in jobs if j["category"] == "Internship"], key=_sort_key, reverse=True)
    grads = sorted([j for j in jobs if j["category"] == "New Grad"], key=_sort_key, reverse=True)
    companies = len({j["company"] for j in jobs})
    out = [
        f"> **Last updated {today.strftime('%b %-d, %Y')}** · **{len(interns)}** internships · "
        f"**{len(grads)}** new-grad roles · **{companies}** companies"
        + (" · US only" if us_only else ""),
        "",
        "**Jump to:** [Internships](#internships) · [New Grad](#new-grad) · [About this list](#about)"
        + (f" · 🆕 = added in the last {NEW_DAYS} days" if show_new else ""),
        "",
        '<a id="internships"></a>',
        "",
        f"## Internships",
        "",
        _table(interns, today, show_new) if interns else "_None found this run._",
        "",
        '<a id="new-grad"></a>',
        "",
        f"## New Grad",
        "",
        _table(grads, today, show_new) if grads else "_None found this run._",
        "",
        "<details>",
        f"<summary>Source status ({n_sources - len(errors)} of {n_sources} sources fetched)</summary>",
        "",
    ]
    if errors:
        out.append("These sources failed this run. Their jobs from the previous run are shown instead.")
        out.append("")
        out += [f"- **{name}**: `{_cell(msg)[:150]}`" for name, msg in sorted(errors.items())]
    else:
        out.append("All sources fetched successfully.")
    out += ["", "</details>"]
    return "\n".join(out)


def write_readme(path, markdown):
    """Replace the text between the JOBS markers in README.md, leaving the rest alone."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise SystemExit(f"{path} is missing the {START} / {END} markers")
    before, rest = text.split(START, 1)
    after = rest.split(END, 1)[1]
    path.write_text(f"{before}{START}\n{markdown}\n{END}{after}", encoding="utf-8")


def write_site_json(path, jobs, errors, n_sources):
    rows = sorted(jobs, key=_sort_key, reverse=True)
    payload = {
        "updated": date.today().isoformat(),
        "sources": n_sources,
        "failed": sorted(errors),
        "jobs": [{k: j.get(k, "") for k in FIELDS} for j in rows],
    }
    Path(path).parent.mkdir(exist_ok=True)
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def load_previous_jobs(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")).get("jobs", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def write_csv(path, jobs):
    rows = sorted(jobs, key=lambda j: (j["category"], j["company"].lower(), j["title"].lower()))
    Path(path).parent.mkdir(exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def load_seen(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_seen(path, seen):
    Path(path).write_text(json.dumps(seen, indent=0, sort_keys=True), encoding="utf-8")
