"""
Assignment 5: download the daily price history of the prediction-market contracts for the 2026 midterms.

What we use as "the probability of a Democratic sweep":
  Polymarket event 'Balance of Power: 2026 Midterms', market '2026 Balance of Power: D Senate, D House'
  (the 2025 market literally called 'Democratic sweep?' is about last year's elections and already resolved).
Also saved for robustness: the other balance-of-power outcomes, the House-control market, and (best effort) Kalshi.

Output: cache/polymarket_prices.csv   columns: ts_utc, market, price, question, slug
        cache/kalshi_prices.csv        (only if the Kalshi calls work)
Run:  python collect_markets.py
No API keys needed.
"""
import json, os, re, time
from datetime import datetime, timezone
import requests
import pandas as pd

os.makedirs("cache", exist_ok=True)
H = {"User-Agent": "FRE-GY-7871A-coursework"}


def get(url, params=None, tries=4):
    for i in range(tries):
        r = requests.get(url, params=params, headers=H, timeout=40)
        if r.status_code in (429, 500, 502, 503):
            time.sleep(3 * (2 ** i)); continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"gave up after {tries} tries ({url.split('/')[2]})")


def label(question):
    """Short stable label for a Polymarket market question."""
    q = question
    table = [("D Senate, D House", "D_Senate_D_House"), ("D Senate, R House", "D_Senate_R_House"),
             ("R Senate, D House", "R_Senate_D_House"), ("R Senate, R House", "R_Senate_R_House"),
             ("Balance of Power: Other", "BoP_Other")]
    for k, v in table:
        if k in q:
            return v
    if re.search(r"Democratic Party control the House", q): return "D_House"
    if re.search(r"Republican Party control the House", q): return "R_House"
    if re.search(r"Democratic Party control the Senate", q): return "D_Senate"
    if re.search(r"Republican Party control the Senate", q): return "R_Senate"
    return None


def polymarket():
    slugs = ["balance-of-power-2026-midterms", "which-party-will-win-the-house-in-2026"]
    # the Senate event: look it up by search, because we do not know its exact slug
    try:
        s = get("https://gamma-api.polymarket.com/public-search", {"q": "which party will win the senate in 2026", "limit_per_type": 8})
        for e in s.get("events", []):
            t = e.get("title", "")
            if re.search(r"senate", t, re.I) and "2026" in t and "win" in t.lower() and e["slug"] not in slugs:
                slugs.append(e["slug"]); print("  found Senate event:", t, "->", e["slug"]); break
    except Exception as ex:
        print("  senate search failed:", str(ex)[:120])
    rows = []
    for slug in slugs:
        ev = get("https://gamma-api.polymarket.com/events", {"slug": slug})
        if not ev:
            print("  event not found:", slug); continue
        e = ev[0]; print(f"  EVENT {e['title']!r} (volume ${float(e.get('volume') or 0):,.0f})")
        for m in e.get("markets", []):
            lab = label(m.get("question", ""))
            toks = m.get("clobTokenIds"); toks = json.loads(toks) if isinstance(toks, str) else toks
            if not lab or not toks:
                continue
            h = get("https://clob.polymarket.com/prices-history", {"market": toks[0], "interval": "max", "fidelity": 1440}).get("history", [])
            time.sleep(0.4)
            print(f"    {lab:18s} {len(h)} daily points" + (f"  last price {h[-1]['p']:.3f}" if h else ""))
            for p in h:
                rows.append({"ts_utc": datetime.fromtimestamp(p["t"], tz=timezone.utc).isoformat(), "market": lab,
                             "price": p["p"], "question": m["question"], "slug": slug})
    df = pd.DataFrame(rows)
    df.to_csv("cache/polymarket_prices.csv", index=False)
    print(f"  saved cache/polymarket_prices.csv ({len(df):,} rows, markets: {sorted(df.market.unique())})")
    return df


def kalshi():
    """Best effort: House and Senate control markets. Prints what it finds so the shape can be fixed if needed."""
    base = "https://api.elections.kalshi.com/trade-api/v2"
    rows = []
    for ev in ["CONTROLH-2026", "CONTROLS-2026"]:
        ms = get(f"{base}/markets", {"event_ticker": ev, "limit": 100}).get("markets", [])
        print(f"  {ev}: {len(ms)} markets", [m["ticker"] for m in ms][:6])
        for m in ms:
            series = m.get("series_ticker") or ev.split("-")[0]
            c = get(f"{base}/series/{series}/markets/{m['ticker']}/candlesticks",
                    {"start_ts": int(datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp()), "end_ts": int(time.time()), "period_interval": 1440})
            cs = c.get("candlesticks", [])
            if cs and not rows:
                print("    sample candlestick:", json.dumps(cs[-1])[:300])
            for k in cs:
                pr = k.get("price", {}) or {}
                v = None
                for key in ("close", "close_dollars", "previous", "previous_dollars"):
                    if pr.get(key) not in (None, ""):
                        v = float(pr[key]); break
                if v is None:
                    yb = (k.get("yes_bid") or {}); ya = (k.get("yes_ask") or {})
                    b_ = yb.get("close_dollars", yb.get("close")); a_ = ya.get("close_dollars", ya.get("close"))
                    v = (float(b_) + float(a_)) / 2 if b_ not in (None, "") and a_ not in (None, "") else None
                if v is None:
                    continue
                rows.append({"ts_utc": datetime.fromtimestamp(k["end_period_ts"], tz=timezone.utc).isoformat(), "ticker": m["ticker"],
                             "title": m.get("yes_sub_title") or m.get("title"), "price": v / 100 if v > 1 else v})
            time.sleep(0.3)
    df = pd.DataFrame(rows)
    if len(df):
        df.to_csv("cache/kalshi_prices.csv", index=False)
        print(f"  saved cache/kalshi_prices.csv ({len(df):,} rows)")
    else:
        print("  Kalshi: no usable rows (fine, Polymarket is the main series)")


if __name__ == "__main__":
    print("Polymarket ...")
    try:
        polymarket()
    except Exception as e:
        print("  !! Polymarket failed:", str(e)[:300])
    print("Kalshi (optional) ...")
    try:
        kalshi()
    except Exception as e:
        print("  Kalshi skipped:", str(e)[:200])
