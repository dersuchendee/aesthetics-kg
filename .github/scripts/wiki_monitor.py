"""Weekly check for new Aesthetics Wiki pages that are not in Aesthetics-KG yet.

Keeps one open issue (label `wiki-update`) with a checklist of pages to review.
Each run collects the pages created since the previous successful run, drops
redirects, deleted pages and anything already in the KG, and re-checks the
pages still waiting on the list.

Environment: GITHUB_TOKEN, GITHUB_REPOSITORY, GITHUB_WORKFLOW_REF (set by Actions),
SINCE (optional, YYYY-MM-DD: re-scan from that date), DRY_RUN=1 (print, don't write).
"""
import datetime as dt
import json
import os
import re
import urllib.parse
import urllib.request

WIKI_API = "https://aesthetics.fandom.com/api.php"
WIKI_PAGE = "https://aesthetics.fandom.com/wiki/"
SPARQL = "https://semantics.istc.cnr.it/aesthetics-kg/graphdb/repositories/aesthetics"
GITHUB_API = "https://api.github.com"

REPO = os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ["GITHUB_TOKEN"]
DRY_RUN = os.environ.get("DRY_RUN") == "1"

LABEL = "wiki-update"
MARKER = "<!-- wiki-monitor -->"
TITLE = "New wiki aesthetics to review"
AESTHETIC_CAT = "Category:Aesthetics Wiki Articles"
FLAG_CATS = {
    "Category:Awaiting Validation": "awaiting validation",
    "Category:Needs work": "needs work",
}
MAX_REVIEWED = 300

ITEM = re.compile(r"^- \[([ xX])\] \[.*?\]\((" + re.escape(WIKI_PAGE) + r"\S+?)\)(.*)$")
CREATED = re.compile(r"created (\d{4}-\d{2}-\d{2})")


def http_json(url, params=None, data=None, method=None, headers=None):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
    return json.loads(raw) if raw else None


def wiki(**params):
    params.update(action="query", format="json", formatversion=2)
    # Fandom answers 403 to the default urllib User-Agent.
    return http_json(WIKI_API, params, headers={"User-Agent": "Mozilla/5.0"})["query"]


def github(path, params=None, data=None, method=None):
    return http_json(GITHUB_API + path, params, data, method, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    })


def parse_time(value):
    t = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def key(title):
    return urllib.parse.unquote(title).replace("_", " ").strip().casefold()


def page_url(title):
    return WIKI_PAGE + urllib.parse.quote(title.replace(" ", "_"), safe="/:'!,-._~&*$+;=@")


def title_from_url(url):
    return urllib.parse.unquote(url[len(WIKI_PAGE):]).replace("_", " ")


def link(title):
    return f"[{title}]({page_url(title)})"


def scan_start(now):
    """Start of the window: SINCE if given, else when the last successful run started."""
    if os.environ.get("SINCE", "").strip():
        return parse_time(os.environ["SINCE"].strip())
    workflow = os.environ["GITHUB_WORKFLOW_REF"].split("@")[0].rsplit("/", 1)[-1]
    runs = github(f"/repos/{REPO}/actions/workflows/{workflow}/runs",
                  {"status": "success", "per_page": 1})["workflow_runs"]
    return parse_time(runs[0]["run_started_at"]) if runs else now - dt.timedelta(days=7)


def new_pages(since):
    """Main-namespace pages created since `since`, as {title: creation date}."""
    pages, cont = {}, {}
    while True:
        d = wiki(list="recentchanges", rctype="new", rcnamespace=0,
                 rcprop="title|timestamp", rclimit="max",
                 rcend=since.strftime("%Y-%m-%dT%H:%M:%SZ"), **cont)
        for rc in d["recentchanges"]:
            pages.setdefault(rc["title"], rc["timestamp"][:10])
        if "continue" not in d:
            return pages
        cont = d["continue"]


def resolve(titles):
    """Follow redirects: {title: (final title, categories)}, or None if the page is gone."""
    titles, out = list(titles), {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        q = wiki(titles="|".join(batch), redirects=1, prop="categories", cllimit="max",
                 clcategories="|".join([AESTHETIC_CAT, *FLAG_CATS]))
        normalized = {n["from"]: n["to"] for n in q.get("normalized", [])}
        redirects = {r["from"]: r["to"] for r in q.get("redirects", [])}
        pages = {p["title"]: p for p in q["pages"]}
        for t in batch:
            t2 = normalized.get(t, t)
            final = redirects.get(t2, t2)
            p = pages.get(final)
            if p is None or p.get("missing") or p.get("invalid"):
                out[t] = None
            else:
                out[t] = (final, {c["title"] for c in p.get("categories", [])})
    return out


def kg_index():
    """Wiki titles and names of every aesthetic in the KG, plus alt labels -> name."""
    query = """
        PREFIX vibe: <https://w3id.org/vibe-ontology/>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT ?name ?kind ?value WHERE {
          ?a a vibe:Aesthetic ; vibe:name ?name .
          { ?a vibe:URL ?value BIND("url" AS ?kind) }
          UNION { ?a vibe:name ?value BIND("name" AS ?kind) }
          UNION { ?a skos:altLabel ?value BIND("alt" AS ?kind) }
        }"""
    rows = http_json(SPARQL, {"query": query},
                     headers={"Accept": "application/sparql-results+json"})["results"]["bindings"]
    known, alt = set(), {}
    for r in rows:
        kind, value = r["kind"]["value"], r["value"]["value"]
        if kind == "url":
            known.add(key(value.split("/wiki/", 1)[-1]))
        elif kind == "name":
            known.add(key(value))
        else:
            alt.setdefault(key(value), r["name"]["value"])
    if not known:
        raise RuntimeError("The KG endpoint returned no aesthetics; not touching the issue.")
    return known, alt


def find_issue():
    for issue in github(f"/repos/{REPO}/issues",
                        {"labels": LABEL, "state": "open", "per_page": 100}):
        if MARKER in (issue.get("body") or ""):
            return issue
    return None


def parse_issue(body):
    """Unticked items -> {title: created date}; ticked items -> list of lines, in order."""
    pending, reviewed = {}, []
    for line in (body or "").splitlines():
        m = ITEM.match(line.strip())
        if not m:
            continue
        ticked, url, rest = m.groups()
        if ticked == " ":
            created = CREATED.search(rest)
            pending[title_from_url(url)] = created.group(1) if created else ""
        else:
            reviewed.append("- [x]" + line.strip()[5:])
    return pending, reviewed


def render(pending, reviewed, now, since):
    lines = [
        MARKER,
        "Pages created on the [Aesthetics Wiki](https://aesthetics.fandom.com/wiki/Aesthetics_Wiki) "
        "that are not in the KG yet. This list is updated every Monday.",
        "",
        "Tick a page once you have added it to the KG or decided to skip it; it moves to "
        "*Reviewed* on the next update. Pages that turn into redirects, get deleted or "
        "appear in the KG are cleared automatically.",
        "",
        f"### To review ({len(pending)})",
        "",
    ]
    for title, (created, notes) in sorted(sorted(pending.items()), key=lambda kv: kv[1][0], reverse=True):
        details = [f"created {created}" if created else "older page"]
        lines.append(f"- [ ] {link(title)} — " + " · ".join(details + notes))
    if not pending:
        lines.append("_Nothing to review._")
    if reviewed:
        lines += ["", f"<details><summary>Reviewed ({len(reviewed)})</summary>", "", *reviewed, "", "</details>"]
    lines += ["", f"<sub>Last checked {now:%Y-%m-%d %H:%M} UTC · new pages since {since:%Y-%m-%d %H:%M} UTC</sub>"]
    return "\n".join(lines)


def main():
    now = dt.datetime.now(dt.timezone.utc)
    since = scan_start(now)
    issue = find_issue()
    old_pending, reviewed = parse_issue(issue["body"] if issue else "")
    reviewed_keys = {key(title_from_url(ITEM.match(r).group(2))) for r in reviewed}

    created = {t: d for t, d in new_pages(since).items() if key(t) not in reviewed_keys}
    candidates = {**created, **{t: d or created.get(t, "") for t, d in old_pending.items()}}
    resolved = resolve(candidates)
    known, alt = kg_index()

    pending, added = {}, []
    for title, date in candidates.items():
        was_listed = title in old_pending
        target = resolved[title]
        if target is None:
            if was_listed:
                reviewed.insert(0, f"- [x] {link(title)} — deleted on the wiki")
            continue
        final, cats = target
        if key(final) in known:
            if was_listed:
                note = "now in the KG" if final == title else f"now redirects to {final}, which is in the KG"
                reviewed.insert(0, f"- [x] {link(title)} — {note}")
            continue
        if key(final) in reviewed_keys or final in pending:
            continue
        notes = []
        if final != title:
            if final in candidates:
                continue  # the target is a new page itself and gets listed on its own
            date, notes = "", [f"via the new redirect {title}"]
        if AESTHETIC_CAT not in cats:
            notes.append("not tagged as an aesthetic")
        notes += [label for cat, label in FLAG_CATS.items() if cat in cats]
        if key(final) in alt:
            notes.append(f"may already be in the KG as {alt[key(final)]}")
        pending[final] = (date, notes)
        if not was_listed:
            added.append(final)

    reviewed = reviewed[:MAX_REVIEWED]
    body = render(pending, reviewed, now, since)
    title = f"{TITLE} ({len(pending)})"
    print(f"Window since {since:%Y-%m-%d %H:%M} UTC: {len(created)} new page(s); "
          f"{len(added)} added to the list, {len(pending)} waiting for review.")

    if DRY_RUN:
        print(f"\n--- {title} ---\n{body}")
        return
    if issue is None:
        if not pending:
            return
        issue = github(f"/repos/{REPO}/issues", data={"title": title, "body": body, "labels": [LABEL]}, method="POST")
        print(f"Opened {issue['html_url']}")
        return
    github(f"/repos/{REPO}/issues/{issue['number']}", data={"title": title, "body": body}, method="PATCH")
    if added:
        comment = f"{len(added)} new page(s) added to the list:\n\n" + "\n".join(f"- {link(t)}" for t in added)
        github(f"/repos/{REPO}/issues/{issue['number']}/comments", data={"body": comment}, method="POST")
    print(f"Updated {issue['html_url']}")


if __name__ == "__main__":
    main()
