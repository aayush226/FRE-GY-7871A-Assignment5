"""
Assignment 5 (US midterms): collect news and forum text about the 2026 midterm elections, one day at a time.

Sources (all free):
  guardian  - The Guardian Open Platform (needs GUARDIAN_API_KEY in .env)
  gnews     - Google News RSS (no key; headlines + outlet, up to 100 per query)
  gdelt     - GDELT DOC 2.0 (no key; 1 request / 5 s limit, so this script waits). Also saves GDELT's own daily "tone" series.
  hn        - Hacker News via Algolia (no key; a tech forum, used as a social-media-style source)

Output: cache/news_all.csv  with columns id, created_at (UTC), text, n_words, platform, query
Every request is cached in cache/news/, so re-running only fetches what is missing.

Run:  python collect_news.py
"""
import os, re, json, time, hashlib, html
from datetime import date, datetime, timedelta, timezone
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
START = date(2026, 8, 1)          # change here if you want a different window
END = date(2026, 10, 5)
USE_GDELT = False                 # GDELT throttles hard (about 1 day/minute); the other sources are enough. Set True to add it.
CONTACT = os.getenv("CONTACT_EMAIL", "student")
HEADERS = {"User-Agent": f"FRE-GY-7871A-coursework ({CONTACT})"}
os.makedirs("cache/news", exist_ok=True)

# Generic election terms only: if we put topic words (economy, immigration...) in the queries,
# the topic model would just hand them back to us.
GUARDIAN_Q = 'midterms OR "midterm elections" OR "midterm election" OR "2026 midterms"'
GNEWS_QS = ["midterm elections", "midterms voters", "2026 midterms poll"]
GDELT_Q = '"midterm elections" sourcecountry:US sourcelang:eng'
HN_TERMS = ["midterms", "midterm election", "midterm elections"]


def tick(name, d):
    print(f"    {name}: {d}", flush=True)


def days():
    d = START
    while d <= END:
        yield d
        d += timedelta(days=1)


def http_get(url, params=None, tries=6, base_sleep=6):
    """GET with exponential backoff on 429/5xx. Errors never print the URL, so API keys stay out of the logs."""
    host = url.split("/")[2]
    for i in range(tries):
        r = requests.get(url, params=params, headers=HEADERS, timeout=40)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(base_sleep * (2 ** i)); continue
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code} from {host}: {r.text[:200]!r}")
        return r
    raise RuntimeError(f"HTTP {r.status_code} from {host} after {tries} tries (rate limited)")


def cached(key, fn):
    f = "cache/news/" + hashlib.md5(key.encode()).hexdigest() + ".json"
    if os.path.exists(f):
        return json.load(open(f, encoding="utf-8"))
    out = fn()
    json.dump(out, open(f, "w", encoding="utf-8"))
    return out


def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()


def row(id_, ts, text, platform, query):
    text = clean(text)
    return {"id": f"{platform}:{id_}", "created_at": ts, "text": text, "n_words": len(text.split()),
            "platform": platform, "query": query}


# ---------------------------------------------------------------- Guardian
def guardian():
    key = os.getenv("GUARDIAN_API_KEY")
    if not key:
        print("  guardian: GUARDIAN_API_KEY missing -> skipped"); return []
    out = []
    for d in days():
        tick("guardian", d)
        def fetch(d=d):
            items = []
            for page in range(1, 4):
                r = http_get("https://content.guardianapis.com/search", {
                    "q": GUARDIAN_Q, "from-date": d.isoformat(), "to-date": d.isoformat(), "page-size": 50, "page": page,
                    "order-by": "newest", "show-fields": "headline,trailText,bodyText", "api-key": key})
                res = r.json()["response"]
                items += res["results"]
                if page >= res["pages"]:
                    break
            return items
        for a in cached(f"guardian|{d}", fetch):
            f = a.get("fields", {})
            body = (f.get("bodyText") or "")[:2000]
            out.append(row(a["id"], a["webPublicationDate"], f"{f.get('headline', a['webTitle'])}. {f.get('trailText', '')}. {body}",
                           "guardian", "midterms"))
    return out


# ---------------------------------------------------------------- Google News RSS
def gnews():
    import feedparser
    out = []
    for d in days():
        tick("gnews", d)
        for q in GNEWS_QS:
            def fetch(d=d, q=q):
                r = http_get("https://news.google.com/rss/search", {
                    "q": f"{q} after:{d.isoformat()} before:{(d + timedelta(days=1)).isoformat()}",
                    "hl": "en-US", "gl": "US", "ceid": "US:en"}, base_sleep=10)
                time.sleep(1.2)
                f = feedparser.parse(r.content)
                res = []
                for e in f.entries:
                    ts = datetime(*e.published_parsed[:6], tzinfo=timezone.utc).isoformat() if getattr(e, "published_parsed", None) else None
                    res.append({"id": e.get("id") or e.link, "ts": ts, "title": e.title,
                                "source": (e.get("source") or {}).get("title", "")})
                return res
            for e in cached(f"gnews|{q}|{d}", fetch):
                if e["ts"]:
                    out.append(row(hashlib.md5(e["id"].encode()).hexdigest()[:16], e["ts"], e["title"], "gnews", q))
    return out


# ---------------------------------------------------------------- GDELT
def gdelt():
    out = []
    for d in days():
        tick("gdelt", d)
        def fetch(d=d):
            r = http_get("https://api.gdeltproject.org/api/v2/doc/doc", {
                "query": GDELT_Q, "mode": "artlist", "maxrecords": 250, "format": "json", "sort": "datedesc",
                "startdatetime": d.strftime("%Y%m%d") + "000000", "enddatetime": d.strftime("%Y%m%d") + "235959"}, base_sleep=8)
            time.sleep(6)
            try:
                return r.json().get("articles", [])
            except ValueError:
                print(f"    gdelt {d}: non-JSON reply, treated as empty")
                return []
        for a in cached(f"gdelt|{d}", fetch):
            try:
                ts = datetime.strptime(a["seendate"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).isoformat()
            except Exception:
                continue
            out.append(row(hashlib.md5(a["url"].encode()).hexdigest()[:16], ts, a.get("title", ""), "gdelt", "midterm elections"))
    # GDELT's own tone time series for the same query (a free cross-check for our sentiment index)
    try:
        def tone():
            r = http_get("https://api.gdeltproject.org/api/v2/doc/doc", {
                "query": GDELT_Q, "mode": "timelinetone", "format": "json",
                "startdatetime": START.strftime("%Y%m%d") + "000000", "enddatetime": END.strftime("%Y%m%d") + "235959"}, base_sleep=8)
            return r.json()
        j = cached("gdelt|tone", tone)
        data = j["timeline"][0]["data"]
        pd.DataFrame(data).to_csv("cache/gdelt_tone.csv", index=False)
        print(f"  gdelt tone series: {len(data)} points -> cache/gdelt_tone.csv")
    except Exception as e:
        print("  gdelt tone series skipped:", str(e)[:150])
    return out


# ---------------------------------------------------------------- Hacker News
def hn():
    out, seen = [], set()
    for d in days():
        tick("hn", d)
        lo = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())
        hi = lo + 86400 - 1
        for term in HN_TERMS:
            def fetch(term=term, lo=lo, hi=hi):
                hits = []
                for page in range(2):
                    r = http_get("https://hn.algolia.com/api/v1/search_by_date", {
                        "query": term, "tags": "(story,comment)", "numericFilters": f"created_at_i>={lo},created_at_i<={hi}",
                        "hitsPerPage": 100, "page": page})
                    j = r.json(); hits += j["hits"]
                    if page + 1 >= j["nbPages"]:
                        break
                return hits
            for h in cached(f"hn2|{term}|{lo}", fetch):
                if h["objectID"] in seen:
                    continue
                seen.add(h["objectID"])
                text = h.get("comment_text") or ((h.get("title") or "") + ". " + (h.get("story_text") or ""))
                out.append(row(h["objectID"], h["created_at"], text, "hn", term))
    return out


if __name__ == "__main__":
    rows = []
    for name, fn in [("guardian", guardian), ("gnews", gnews), ("gdelt", gdelt), ("hn", hn)]:
        if name == "gdelt" and not USE_GDELT:
            print("gdelt: skipped (USE_GDELT = False)"); continue
        print(f"{name}: collecting {START} -> {END} ...")
        try:
            got = fn()
        except Exception as e:
            print(f"  !! {name} failed: {str(e)[:300]}"); got = []
        print(f"  {name}: {len(got):,} docs" + ("   <-- ZERO docs, check this source" if not got else ""))
        rows += got
    df = pd.DataFrame(rows).drop_duplicates("id")
    df["created_at"] = df["created_at"].map(lambda x: pd.to_datetime(x, utc=True, errors="coerce"))
    bad = int(df["created_at"].isna().sum())
    if bad:
        print(f"WARNING: dropped {bad} rows with unparseable timestamps")
    df = df.dropna(subset=["created_at"])
    df = df[df["n_words"] >= 3].sort_values("created_at")
    df.to_csv("cache/news_all.csv", index=False)
    print("\nsaved cache/news_all.csv")
    print(df.groupby("platform").agg(docs=("id", "size"), first=("created_at", "min"), last=("created_at", "max")).to_string())
