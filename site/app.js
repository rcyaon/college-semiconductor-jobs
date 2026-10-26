// Semiconductor Jobs website: loads jobs.json, filters it, and keeps an
// application tracker in the browser, with optional sync to a private GitHub gist.
(() => {
  "use strict";

  const CONFIG = window.SEMI_JOBS_CONFIG || {};
  const STATUSES = ["", "Saved", "Applied", "Interviewing", "Offer", "Rejected"];
  const STORE_KEY = "semi-jobs-tracker-v1";
  const TOKEN_KEY = "semi-jobs-github-token";
  const GIST_FILE = "semiconductor-jobs-tracker.json";
  const PAGE_SIZE = 150;
  const NEW_DAYS = 7;

  const $ = (sel) => document.querySelector(sel);
  const state = { jobs: [], byId: new Map(), view: "all", shown: PAGE_SIZE, user: null, gistId: null };

  // ---------------------------------------------------------------- storage
  // Any of these can throw (private mode, blocked storage), so the page must work without them.
  function readLocal(key, fallback) {
    try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch { return fallback; }
  }
  function writeLocal(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* storage unavailable */ }
  }
  function removeLocal(key) {
    try { localStorage.removeItem(key); } catch { /* storage unavailable */ }
  }

  // tracker = { [jobId]: { status, updated, company, title, url } }
  let tracker = readLocal(STORE_KEY, {});

  function setStatus(job, status) {
    const prev = tracker[job.id];
    if (!status && !prev) return;
    tracker[job.id] = {
      status,
      updated: new Date().toISOString(),
      applied: status === "Applied" && !prev?.applied ? new Date().toISOString().slice(0, 10) : prev?.applied || "",
      company: job.company, title: job.title, url: job.url, category: job.category, location: job.location,
    };
    writeLocal(STORE_KEY, tracker);
    scheduleSync();
    updateCounts();
  }

  // ------------------------------------------------------------- rendering
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const daysAgo = (iso) => (Date.now() - new Date(iso + "T00:00:00").getTime()) / 864e5;
  const isNew = (j) => j.first_seen && daysAgo(j.first_seen) <= NEW_DAYS;

  function trackedJobs() {
    // Tracked jobs stay visible in "My applications" even after the posting disappears.
    return Object.entries(tracker)
      .filter(([, t]) => t.status)
      .map(([id, t]) => state.byId.get(id) || { id, company: t.company, title: t.title, url: t.url,
        category: t.category || "", location: t.location || "", posted: "", first_seen: "", closed: true });
  }

  function filtered() {
    const q = $("#q").value.trim().toLowerCase();
    const company = $("#company").value;
    const newOnly = $("#new-only").checked;
    const hideTracked = $("#hide-applied").checked;
    const terms = q.split(/\s+/).filter(Boolean);
    let list = state.view === "tracked" ? trackedJobs()
      : state.jobs.filter((j) => state.view === "all" || j.category === state.view);
    list = list.filter((j) => {
      if (company && j.company !== company) return false;
      if (newOnly && !isNew(j)) return false;
      if (hideTracked && state.view !== "tracked" && tracker[j.id]?.status) return false;
      if (!terms.length) return true;
      const hay = `${j.company} ${j.title} ${j.location} ${j.category}`.toLowerCase();
      return terms.every((t) => hay.includes(t));
    });
    const sort = $("#sort").value;
    const cmp = {
      new: (a, b) => (b.first_seen || "").localeCompare(a.first_seen || "") || (b.posted || "").localeCompare(a.posted || ""),
      company: (a, b) => a.company.localeCompare(b.company) || a.title.localeCompare(b.title),
      title: (a, b) => a.title.localeCompare(b.title),
    }[sort];
    return list.sort(cmp);
  }

  function statusSelect(job) {
    const cur = tracker[job.id]?.status || "";
    const opts = STATUSES.map((s) => `<option value="${s}"${s === cur ? " selected" : ""}>${s || "Track…"}</option>`).join("");
    return `<select class="status" data-id="${esc(job.id)}" data-status="${esc(cur)}" aria-label="Status for ${esc(job.title)}">${opts}</select>`;
  }

  function render() {
    const list = filtered();
    const rows = list.slice(0, state.shown).map((j) => {
      const badge = isNew(j) ? '<span class="badge new">New</span>' : "";
      const cat = j.category ? `<span class="badge ${j.category === "Internship" ? "intern" : "grad"}">${esc(j.category)}</span>` : "";
      const closed = j.closed ? '<span class="badge closed">No longer listed</span>' : "";
      const applied = tracker[j.id]?.applied ? `<span class="muted small">Applied ${esc(tracker[j.id].applied)}</span>` : "";
      return `<tr>
        <td class="co" data-label="Company">${esc(j.company)}</td>
        <td class="role" data-label="Role"><a href="${esc(j.url)}" target="_blank" rel="noopener">${esc(j.title)}</a> ${badge}${state.view === "all" || state.view === "tracked" ? cat : ""}${closed}</td>
        <td class="loc" data-label="Location">${esc(j.location) || "—"}</td>
        <td class="date" data-label="Posted">${esc(j.posted) || "—"}</td>
        <td class="st" data-label="Status">${statusSelect(j)}${applied}</td>
        <td class="go"><a class="apply" href="${esc(j.url)}" target="_blank" rel="noopener">Apply</a></td>
      </tr>`;
    });
    $("#rows").innerHTML = rows.join("") ||
      `<tr><td colspan="6" class="empty">${state.view === "tracked"
        ? "Nothing tracked yet. Use the <strong>Track…</strong> menu on any job to save it here."
        : "No jobs match these filters."}</td></tr>`;
    $("#result-line").textContent = `${list.length.toLocaleString()} ${list.length === 1 ? "job" : "jobs"}`
      + (list.length > state.shown ? ` · showing first ${state.shown}` : "");
    $("#more").hidden = list.length <= state.shown;
  }

  function updateCounts() {
    const tracked = trackedJobs();
    $("#tracked-count").textContent = tracked.length;
    const by = (s) => tracked.filter((j) => tracker[j.id].status === s).length;
    const interns = state.jobs.filter((j) => j.category === "Internship").length;
    const newCount = state.jobs.filter(isNew).length;
    $("#stats").innerHTML = [
      [interns, "internships"],
      [state.jobs.length - interns, "new-grad roles"],
      [new Set(state.jobs.map((j) => j.company)).size, "companies"],
      [newCount, "new this week"],
      [by("Applied") + by("Interviewing") + by("Offer"), "you've applied to"],
    ].map(([n, label]) => `<div class="stat"><b>${n.toLocaleString()}</b><span>${label}</span></div>`).join("");
  }

  // ------------------------------------------------------- GitHub sync ---
  // Tracker data lives in a private gist in the visitor's own account. Without
  // sign-in, everything still works from localStorage.
  const token = () => readLocal(TOKEN_KEY, null);

  async function gh(path, opts = {}) {
    const res = await fetch(`https://api.github.com${path}`, {
      ...opts,
      headers: { Accept: "application/vnd.github+json", Authorization: `Bearer ${token()}`, ...(opts.headers || {}) },
    });
    if (!res.ok) throw new Error(`GitHub ${res.status}`);
    return res.status === 204 ? null : res.json();
  }

  async function findGist() {
    for (let page = 1; page <= 10; page++) {
      const gists = await gh(`/gists?per_page=100&page=${page}`);
      const hit = gists.find((g) => g.files && g.files[GIST_FILE]);
      if (hit) return hit.id;
      if (gists.length < 100) return null;
    }
    return null;
  }

  function mergeTrackers(a, b) {
    const out = { ...a };
    for (const [id, t] of Object.entries(b || {})) {
      if (!out[id] || (t.updated || "") > (out[id].updated || "")) out[id] = t;
    }
    return out;
  }

  async function connect() {
    try {
      state.user = await gh("/user");
      state.gistId = await findGist();
      if (state.gistId) {
        const gist = await gh(`/gists/${state.gistId}`);
        const file = gist.files[GIST_FILE];
        const remote = JSON.parse(file.truncated ? await (await fetch(file.raw_url)).text() : file.content || "{}");
        tracker = mergeTrackers(tracker, remote.tracker || {});
        writeLocal(STORE_KEY, tracker);
      }
      await pushNow();
    } catch (err) {
      console.warn(err);
      if (String(err).includes("401")) removeLocal(TOKEN_KEY);
      state.user = null;
    }
    renderAccount();
    updateCounts();
    render();
  }

  let syncTimer = null;
  function scheduleSync() {
    if (!state.user) return;
    clearTimeout(syncTimer);
    setSyncLabel("Saving…");
    syncTimer = setTimeout(pushNow, 1200);
  }

  async function pushNow() {
    if (!token()) return;
    const body = { files: { [GIST_FILE]: { content: JSON.stringify({ tracker, saved: new Date().toISOString() }, null, 1) } } };
    try {
      if (state.gistId) {
        await gh(`/gists/${state.gistId}`, { method: "PATCH", body: JSON.stringify(body) });
      } else {
        const g = await gh("/gists", { method: "POST", body: JSON.stringify({ ...body, public: false, description: "Semiconductor Jobs application tracker" }) });
        state.gistId = g.id;
      }
      setSyncLabel("Synced");
    } catch (err) {
      console.warn(err);
      setSyncLabel("Sync failed, saved in this browser");
    }
  }

  function setSyncLabel(text) {
    const el = $("#sync-label");
    if (el) el.textContent = text;
  }

  function renderAccount() {
    const box = $("#account");
    if (state.user) {
      box.innerHTML = `<img src="${esc(state.user.avatar_url)}&s=56" alt="" width="28" height="28">
        <span><b>${esc(state.user.login)}</b><span class="muted small" id="sync-label">Synced</span></span>
        <button class="secondary small-btn" id="signout">Sign out</button>`;
      $("#signout").onclick = () => { removeLocal(TOKEN_KEY); state.user = null; state.gistId = null; renderAccount(); };
      $("#sync-note").textContent = " and synced to a private gist in your GitHub account";
    } else {
      box.innerHTML = `<button class="secondary" id="signin">${githubIcon()} Sync with GitHub</button>`;
      $("#signin").onclick = signIn;
      $("#sync-note").textContent = " (optional: sync with GitHub to use it on any device)";
    }
  }

  function githubIcon() {
    return '<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>';
  }

  function signIn() {
    if (CONFIG.githubClientId && CONFIG.tokenExchangeUrl) {
      // One-click OAuth: GitHub sends the visitor back here with ?code=…, which the
      // worker swaps for a token (the swap needs a secret, so it can't happen in the browser).
      const stateParam = crypto.getRandomValues(new Uint32Array(4)).join("-");
      try { sessionStorage.setItem("semi-jobs-oauth-state", stateParam); } catch { /* ignore */ }
      const redirect = location.origin + location.pathname;
      location.href = `https://github.com/login/oauth/authorize?client_id=${encodeURIComponent(CONFIG.githubClientId)}`
        + `&scope=gist&state=${stateParam}&redirect_uri=${encodeURIComponent(redirect)}`;
    } else {
      $("#token-error").hidden = true;
      $("#token-input").value = "";
      $("#token-dialog").showModal();
    }
  }

  async function finishOAuth() {
    const params = new URLSearchParams(location.search);
    const code = params.get("code");
    if (!code) return;
    history.replaceState(null, "", location.pathname);
    let expected = null;
    try { expected = sessionStorage.getItem("semi-jobs-oauth-state"); } catch { /* ignore */ }
    if (!expected || params.get("state") !== expected) return;
    try {
      const res = await fetch(CONFIG.tokenExchangeUrl, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code }),
      });
      const data = await res.json();
      if (data.access_token) writeLocal(TOKEN_KEY, data.access_token);
    } catch (err) {
      console.warn("GitHub sign-in failed", err);
    }
  }

  // ----------------------------------------------------------------- CSV ---
  function exportCsv() {
    const rows = [["Status", "Applied on", "Company", "Role", "Location", "Category", "Link", "Last changed"]];
    for (const j of trackedJobs()) {
      const t = tracker[j.id];
      rows.push([t.status, t.applied || "", j.company, j.title, j.location, j.category, j.url, (t.updated || "").slice(0, 10)]);
    }
    const csv = rows.map((r) => r.map((v) => `"${String(v ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = `semiconductor-applications-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  // ---------------------------------------------------------------- wiring
  function wire() {
    let t = null;
    $("#q").addEventListener("input", () => { clearTimeout(t); t = setTimeout(() => { state.shown = PAGE_SIZE; render(); }, 120); });
    for (const id of ["#company", "#sort", "#new-only", "#hide-applied"]) {
      $(id).addEventListener("change", () => { state.shown = PAGE_SIZE; render(); });
    }
    $("#tabs").addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-view]");
      if (!btn) return;
      state.view = btn.dataset.view;
      state.shown = PAGE_SIZE;
      for (const b of $("#tabs").querySelectorAll("button")) b.setAttribute("aria-selected", String(b === btn));
      render();
    });
    $("#rows").addEventListener("change", (e) => {
      const sel = e.target.closest("select.status");
      if (!sel) return;
      const job = state.byId.get(sel.dataset.id) || trackedJobs().find((j) => j.id === sel.dataset.id);
      if (job) setStatus(job, sel.value);
      sel.dataset.status = sel.value;
      if (state.view === "tracked" || $("#hide-applied").checked) render();
    });
    $("#more").addEventListener("click", () => { state.shown += PAGE_SIZE; render(); });
    $("#export").addEventListener("click", exportCsv);
    $("#token-save").addEventListener("click", async (e) => {
      e.preventDefault();
      const value = $("#token-input").value.trim();
      if (!value) return;
      writeLocal(TOKEN_KEY, value);
      await connect();
      if (state.user) { $("#token-dialog").close(); }
      else { $("#token-error").textContent = "That token didn't work. Check that it has the gist scope."; $("#token-error").hidden = false; }
    });
  }

  async function init() {
    wire();
    renderAccount();
    try {
      const res = await fetch("jobs.json", { cache: "no-cache" });
      const data = await res.json();
      state.jobs = data.jobs || [];
      state.byId = new Map(state.jobs.map((j) => [j.id, j]));
      $("#updated").textContent = `updated ${new Date(data.updated + "T12:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}`;
      const companies = [...new Set(state.jobs.map((j) => j.company))].sort((a, b) => a.localeCompare(b));
      $("#company").insertAdjacentHTML("beforeend", companies.map((c) => `<option>${esc(c)}</option>`).join(""));
    } catch (err) {
      $("#updated").textContent = "couldn't load jobs";
      console.error(err);
    }
    updateCounts();
    render();
    await finishOAuth();
    if (token()) connect();
  }

  init();
})();
