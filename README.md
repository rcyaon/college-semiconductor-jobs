# Semiconductor Internships & New-Grad Jobs

A daily-updated list of semiconductor internships and new-grad roles for scholars of the EDGE Consortium.

## 👉 [See the job list → JOBS.md](JOBS.md)

The list covers chip design, verification, physical design, DFT, process, device, test, firmware, and related roles. It's pulled straight from company career sites and chip-industry job boards, filtered down to internships, co-ops, and new-grad / entry-level jobs in the US.

---

## Where the jobs come from

**Company career sites:** most large chip companies post university roles on their own sites before anywhere else.

| Type | Companies |
| --- | --- |
| Large semis | NVIDIA · Intel · Micron · Analog Devices · Marvell · Broadcom · NXP · Microchip · Silicon Labs · Samsung Semiconductor · GlobalFoundries |
| Equipment, materials & EDA | Applied Materials · KLA · Entegris · Cadence |
| Startups | Tenstorrent · Lightmatter · PsiQuantum · Astera Labs · SambaNova · Etched · MatX · Axelera AI · Normal Computing · Extropic · Eliyan |

**Job boards**

- [SemiDesignJobs](https://www.semidesignjobs.com): chip-design roles (ASIC, RTL, verification, physical design, SoC) from many more companies, including Qualcomm, AMD, Texas Instruments, Synopsys and SK hynix.
- [Semiconductor Engineering jobs](https://semiengineering.com/jobs/): the board attached to the main industry trade publication.

The full list, with each site's connection details, is in [`sources.json`](sources.json).

## Check these by hand too

Some of the best sources can't be scraped because they need a login or have no public data:

| Source | Why it's worth checking |
| --- | --- |
| [ChipPath](https://semifoundation.org/chippath/) (SEMI Foundation) | The largest US semiconductor careers hub (~90k openings), plus resume and interview tools. Sign up through FutureFit AI. |
| [SIA Jobs](https://www.semiconductors.org/sia-jobs/) | The Semiconductor Industry Association's own board. |
| [Handshake](https://joinhandshake.com) | Where companies recruiting at your school post. |
| [LinkedIn Jobs](https://www.linkedin.com/jobs/) | Covers everything else. Set alerts for "semiconductor intern". |
| EDGE events | Talent-acquisition webinars and site visits are a hiring pipeline, so treat them as such. |

---

## How it works

1. `scrape.py` downloads every open posting from each source in [`sources.json`](sources.json).
2. It keeps titles that look like internships (intern, co-op, student, summer 2027…) or new-grad roles (new college grad, university, entry level, Engineer I…). It drops senior, staff, manager and similar titles. Workday portals also label many roles "Intern" or "New College Graduate" directly, and the scraper uses those labels too.
3. It keeps US locations. Roles whose location is unclear ("Remote", "3 Locations") are kept as well.
4. It merges duplicates when the same job shows up on a company site and a job board, keeping the company link.
5. It writes [`JOBS.md`](JOBS.md), plus [`data/jobs.csv`](data/jobs.csv) and [`data/jobs.json`](data/jobs.json) for spreadsheets. Jobs that weren't there on the previous run get a 🆕 badge.

A GitHub Action ([`.github/workflows/scrape.yml`](.github/workflows/scrape.yml)) re-runs this every morning and commits the updated list.

## Run it yourself

Requires Python 3.9+.

```bash
pip install -r requirements.txt
python scrape.py                   # US roles from all sources (~2–4 minutes)
python scrape.py --all-locations   # include roles outside the US
python scrape.py --only NVIDIA,Intel   # just a few sources (good for testing)
```

## Add a company

Add an entry to [`sources.json`](sources.json). Company sites go above the job boards, so their links take priority over a board's copy of the same job.

| Career site | Find it by… | Entry |
| --- | --- | --- |
| Workday (`*.myworkdayjobs.com`) | Opening any job and reading the URL: `https://{tenant}.wd5.myworkdayjobs.com/{site}/job/...` | `{"company": "X", "ats": "workday", "host": "x.wd5.myworkdayjobs.com", "tenant": "x", "site": "External"}` |
| Greenhouse | `boards.greenhouse.io/{token}` | `{"company": "X", "ats": "greenhouse", "token": "x"}` |
| Lever | `jobs.lever.co/{token}` | `{"company": "X", "ats": "lever", "token": "x"}` |
| Ashby | `jobs.ashbyhq.com/{token}` | `{"company": "X", "ats": "ashby", "token": "x"}` |
| SmartRecruiters | `jobs.smartrecruiters.com/{token}` | `{"company": "X", "ats": "smartrecruiters", "token": "X"}` |

Then run `python scrape.py --only X` to check it.

## Project layout

```
scrape.py            entry point: fetch → filter → merge → write
sources.json         companies and job boards to scrape
semijobs/sources.py  one fetcher per career-site type / job board
semijobs/filters.py  intern / new-grad / US-location rules
semijobs/report.py   writes JOBS.md and data/
JOBS.md              the generated job list
data/                jobs.csv, jobs.json, seen.json (first-seen dates for 🆕)
```
