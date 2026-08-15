#!/usr/bin/env python3
"""CI build: pull the CONVERTS Client Data DB from Notion and write index.html at repo root.

Runs inside GitHub Actions. The Notion token comes from the NOTION_TOKEN env var
(a GitHub Actions secret) — never committed to the repo. Self-contained: stdlib only.
"""
import json, os, sys, time, urllib.request, urllib.error, datetime

TOKEN = os.environ.get("NOTION_TOKEN")
if not TOKEN:
    sys.exit("NOTION_TOKEN env var is not set")
DB = "3bc5d5746b468048a21acd6680bf5a18"
NV = "2022-06-28"
BUILD_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BUILD_DIR)
TEMPLATE = os.path.join(BUILD_DIR, "template.html")
OUT = os.path.join(ROOT, "index.html")

def req(method, path, body=None, tries=6):
    url = "https://api.notion.com/v1/" + path
    data = json.dumps(body).encode() if body is not None else None
    for a in range(tries):
        r = urllib.request.Request(url, data=data, method=method)
        r.add_header("Authorization", "Bearer " + TOKEN)
        r.add_header("Notion-Version", NV)
        r.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(r, timeout=45) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503, 504) and a < tries - 1:
                try: wait = float(e.headers.get("Retry-After") or (a + 1))
                except Exception: wait = a + 1
                time.sleep(min(max(wait, 0.5), 30)); continue
            raise
        except Exception:
            if a < tries - 1: time.sleep(a + 1); continue
            raise
    raise SystemExit("Notion request retries exhausted")

def rich(p):
    if p is None: return None
    t = p.get("type")
    if t in ("title", "rich_text"): return "".join(x.get("plain_text", "") for x in p.get(t, []))
    if t == "number": return p.get("number")
    if t == "url": return p.get("url")
    if t == "select": return (p.get("select") or {}).get("name")
    if t == "multi_select": return [o["name"] for o in p.get("multi_select", [])]
    if t == "date": return (p.get("date") or {}).get("start")
    if t == "formula":
        f = p.get("formula") or {}; return f.get(f.get("type"))
    return None

def division(fmt, st):
    fmt = (fmt or "").strip(); st = (st or "").strip()
    if fmt == "Carousel": return "carousel"
    if st == "Talking Head": return "talking_head"
    if st == "Green Screen": return "green_screen"
    if st in ("Stich", "Comment Response"): return "reaction"
    if st in ("B - Roll + Text", "Written Post B - Roll", "Static B-Roll + TExt"): return "broll"
    return "other"

def pull():
    rows, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor: body["start_cursor"] = cursor
        r = req("POST", f"databases/{DB}/query", body)
        for pg in r["results"]:
            p = pg["properties"]
            v = rich(p.get("Views")); posted = rich(p.get("Date & Time Posted"))
            if not isinstance(v, (int, float)) or v <= 0 or not posted: continue
            def n(x): return x if isinstance(x, (int, float)) else 0
            rows.append({
                "handle": rich(p.get("IG Username")) or "unknown",
                "title": (rich(p.get("Video Title")) or "").strip(),
                "views": int(v), "comments": int(n(rich(p.get("Comments")))),
                "likes": int(n(rich(p.get("Likes")))), "outlier": round(n(rich(p.get("Outlier Score"))), 2),
                "followers": int(n(rich(p.get("Account Follower Count")))),
                "video_url": rich(p.get("Video URL")) or "", "audio_url": rich(p.get("Audio URL")) or "",
                "hook": (rich(p.get("Hook")) or "").strip(), "transcript": (rich(p.get("Script")) or "").strip(),
                "caption": (rich(p.get("Caption")) or "").strip(),
                "trigger": rich(p.get("Converts Trigger")) or [],
                "format": rich(p.get("Content Format ")) or "", "style": rich(p.get("Content Style")) or "",
                "division": division(rich(p.get("Content Format ")), rich(p.get("Content Style"))),
                "posted": posted[:10],
            })
        if not r.get("has_more"): break
        cursor = r["next_cursor"]
    return rows

def main():
    rows = pull()
    rows.sort(key=lambda x: -x["views"]); rows = rows[:100]
    for i, c in enumerate(rows): c["rank"] = i + 1
    today = datetime.date.today()
    newest = max((datetime.date.fromisoformat(c["posted"]) for c in rows), default=today)
    ref = max(today, newest)
    html = (open(TEMPLATE).read()
            .replace("__DATA__", json.dumps(rows))
            .replace("__SNAPDATE__", today.strftime("%b %-d, %Y"))
            .replace("__SNAPSHOT_ISO__", ref.isoformat()))
    if "__DATA__" in html or "__SNAPSHOT_ISO__" in html:
        sys.exit("template placeholders not fully replaced")
    open(OUT, "w").write(html)
    print(f"Built {len(rows)} videos from {DB} (snapshot {today}).")

if __name__ == "__main__":
    main()
