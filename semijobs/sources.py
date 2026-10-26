"""Fetchers for each job source. Every fetcher returns a list of raw job dicts:

    {"company", "title", "location", "url", "posted", "source", "hint"}

`posted` is an ISO date (YYYY-MM-DD) or "" if unknown. `hint` is an optional
"Internship"/"New Grad" label the source itself provides.
"""
import html
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .filters import EXCLUDE_RE


UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"
TIMEOUT = 30


def make_session():
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=1.5, status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET", "POST"])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": UA, "Accept": "application/json"})
    return s


def _iso(value):
    """Turn a timestamp (ISO string or epoch ms) into YYYY-MM-DD."""
    if not value:
        return ""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date().isoformat()
    return str(value)[:10]


def _job(company, title, location, url, posted="", source="", hint=None):
    return {
        "company": company.strip(),
        "title": html.unescape(re.sub(r"\s+", " ", title)).strip(),
        "location": html.unescape(re.sub(r"\s+", " ", location or "")).strip(),
        "url": url,
        "posted": posted,
        "source": source,
        "hint": hint,
    }


# ---------------------------------------------------------------- Workday ---

# Workday's keyword search is unreliable (some tenants ignore it), so we page
# through every posting and filter titles ourselves. Pages are fetched a few
# at a time to stay polite.
WORKDAY_PAGE = 20  # Workday's maximum page size
WORKDAY_CAP = 2000  # Workday returns at most this many results per query
WORKDAY_THREADS = 4
INTERN_FACET_RE = re.compile(r"intern|co-?op|student|apprentice", re.I)
GRAD_FACET_RE = re.compile(r"new (college )?grad|university|early career|entry level|campus|graduate", re.I)


def _workday_posted(text):
    """'Posted Today' / 'Posted 3 Days Ago' / 'Posted 30+ Days Ago' -> ISO date."""
    t = (text or "").lower()
    today = date.today()
    if "today" in t:
        return today.isoformat()
    if "yesterday" in t:
        return (today - timedelta(days=1)).isoformat()
    m = re.search(r"(\d+)\+?\s+days", t)
    if m:
        return "30+ days ago" if "+" in t else (today - timedelta(days=int(m.group(1)))).isoformat()
    return ""


def _workday_location(p):
    loc = p.get("locationsText", "")
    path = p.get("externalPath", "")
    m = re.match(r"(\d+) Locations", loc)
    if m and path.count("/") >= 3:  # "2 Locations": the URL holds the primary one, e.g. /job/US-CA-Santa-Clara/...
        return f"{path.split('/')[2].replace('-', ' ')} (+{int(m.group(1)) - 1} more)"
    return loc


def fetch_workday(session, c):
    host, tenant, site = c["host"], c["tenant"], c["site"]
    api = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"

    def page(facets, offset):
        body = {"appliedFacets": facets, "limit": WORKDAY_PAGE, "offset": offset, "searchText": ""}
        r = session.post(api, json=body, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()

    def crawl(pool, facets, first=None):
        first = first or page(facets, 0)
        total = min(first.get("total", 0), WORKDAY_CAP)
        out = list(first.get("jobPostings", []))
        for data in pool.map(lambda off: page(facets, off), range(WORKDAY_PAGE, total, WORKDAY_PAGE)):
            out += data.get("jobPostings", [])
        return out

    with ThreadPoolExecutor(WORKDAY_THREADS) as pool:
        first = page({}, 0)
        if first.get("total", 0) < WORKDAY_CAP:
            postings = crawl(pool, {}, first)
        else:
            # Workday stops at 2000 results per query, so split by a filter
            # (e.g. job family) whose groups are each under the cap.
            flat = [f for f in first.get("facets", [])
                    if f.get("values") and all("count" in v and v["count"] is not None for v in f["values"])]
            facet = min(flat, key=lambda f: max(v["count"] for v in f["values"]))
            postings = []
            for v in facet["values"]:
                postings += crawl(pool, {facet["facetParameter"]: [v["id"]]})

        # Many tenants tag roles as "Intern" / "New College Graduate" in a filter even
        # when the title doesn't say so. Fetch those groups to label them.
        hints = {}
        for f in first.get("facets", []):
            for v in f.get("values") or []:
                label = v.get("descriptor") or ""
                if not v.get("count") or EXCLUDE_RE.search(label):
                    continue
                hint = ("Internship" if INTERN_FACET_RE.search(label) else
                        "New Grad" if GRAD_FACET_RE.search(label) else None)
                if hint:
                    for p in crawl(pool, {f["facetParameter"]: [v["id"]]}):
                        hints.setdefault(p.get("externalPath"), hint)

    jobs, seen = [], set()
    for p in postings:
        path = p.get("externalPath", "")
        if path in seen:
            continue
        seen.add(path)
        jobs.append(_job(c["company"], p.get("title", ""), _workday_location(p),
                         f"https://{host}/{site}{path}", _workday_posted(p.get("postedOn")), "workday",
                         hints.get(path)))
    return jobs


# ------------------------------------------------------- Simple JSON ATSs ---

def fetch_greenhouse(session, c):
    r = session.get(f"https://boards-api.greenhouse.io/v1/boards/{c['token']}/jobs", timeout=TIMEOUT)
    r.raise_for_status()
    return [
        _job(c["company"], j["title"], (j.get("location") or {}).get("name", ""), j["absolute_url"],
             _iso(j.get("first_published") or j.get("updated_at")), "greenhouse")
        for j in r.json().get("jobs", [])
    ]


def fetch_lever(session, c):
    r = session.get(f"https://api.lever.co/v0/postings/{c['token']}?mode=json", timeout=TIMEOUT)
    r.raise_for_status()
    out = []
    for j in r.json():
        cats = j.get("categories") or {}
        loc = cats.get("location") or ", ".join(cats.get("allLocations") or [])
        hint = "Internship" if "intern" in (cats.get("commitment") or "").lower() else None
        out.append(_job(c["company"], j["text"], loc, j["hostedUrl"], _iso(j.get("createdAt")), "lever", hint))
    return out


def fetch_ashby(session, c):
    r = session.get(f"https://api.ashbyhq.com/posting-api/job-board/{c['token']}", timeout=TIMEOUT)
    r.raise_for_status()
    out = []
    for j in r.json().get("jobs", []):
        if j.get("isListed") is False:
            continue
        hint = "Internship" if (j.get("employmentType") or "").lower() == "intern" else None
        out.append(_job(c["company"], j["title"], j.get("location", ""), j.get("jobUrl", ""),
                        _iso(j.get("publishedAt")), "ashby", hint))
    return out


def fetch_smartrecruiters(session, c):
    out, offset = [], 0
    while True:
        r = session.get(f"https://api.smartrecruiters.com/v1/companies/{c['token']}/postings",
                        params={"limit": 100, "offset": offset}, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        for j in data.get("content", []):
            loc = j.get("location") or {}
            where = ", ".join(x for x in [loc.get("city"), loc.get("region"), loc.get("country", "").upper()] if x)
            out.append(_job(c["company"], j["name"], where,
                            f"https://jobs.smartrecruiters.com/{c['token']}/{j['id']}",
                            _iso(j.get("releasedDate")), "smartrecruiters"))
        offset += 100
        if offset >= data.get("totalFound", 0) or offset >= 2000:
            return out


# ------------------------------------------------------------- Job boards ---

def fetch_semidesignjobs(session, c):
    """semidesignjobs.com publishes its whole board as JSON."""
    r = session.get("https://www.semidesignjobs.com/jobs.json", timeout=90)
    r.raise_for_status()
    out = []
    for j in r.json():
        cats = {x.get("name", "") for x in j.get("categories") or []}
        hint = "Internship" if j.get("arrangement") == "internship" else (
            "New Grad" if "Level - Entry or Early Career" in cats else None)
        comp = j.get("company") or {}
        url = (j.get("links") or {}).get("self") or j.get("application_link", "")
        out.append(_job(comp.get("name", "?"), j["title"], comp.get("location", ""), url,
                        _iso(j.get("published_at")), "semidesignjobs.com", hint))
    return out


def fetch_semiengineering(session, c):
    """semiengineering.com/jobs runs WordPress Job Manager, which exposes a REST API."""
    out, page = [], 1
    while True:
        r = session.get("https://semiengineering.com/wp-json/wp/v2/job-listings",
                        params={"per_page": 100, "page": page}, timeout=90)
        r.raise_for_status()
        for j in r.json():
            meta = j.get("meta") or {}
            if str(meta.get("_filled")) == "1":
                continue
            out.append(_job(meta.get("_company_name") or "?", j["title"]["rendered"],
                            meta.get("_job_location", ""), j["link"], _iso(j.get("date")),
                            "semiengineering.com"))
        if page >= int(r.headers.get("X-WP-TotalPages", 1)):
            return out
        page += 1


FETCHERS = {
    "workday": fetch_workday,
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
    "smartrecruiters": fetch_smartrecruiters,
    "semidesignjobs": fetch_semidesignjobs,
    "semiengineering": fetch_semiengineering,
}
