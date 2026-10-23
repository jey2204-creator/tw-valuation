"""美股四大指數日線＋VIX：Yahoo（免 key）→ us/data/index_px.json
用法：python us/fetch_index.py
備援：Stooq 失敗時用 FRED（只有 S&P 500、Nasdaq 綜合、道瓊，約 10 年）。
只用 Python 標準函式庫。

輸出：
{
  "updated": "2026-10-23T22:40:00Z",
  "src": {"SPX": "stooq", ...},
  "s": { "SPX": [[ "2016-10-24", 2151.33 ], ...], "NDX": [...], "DJI": [...], "SOX": [...] }
}
"""
import csv, io, json, sys, time, datetime as dt
from pathlib import Path
import urllib.request, urllib.parse, urllib.error

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "index_px.json"
START = "2000-01-01"
# 代號: (Stooq 代號, FRED 代號或 None)
# 代號: (Yahoo 代號, Stooq 代號, FRED 代號或 None)；來源順序 Yahoo → Stooq → FRED → 舊資料
IDX = {"SPX": ("^GSPC", "^spx", "SP500"), "NDX": ("^NDX", "^ndx", "NASDAQ100"), "DJI": ("^DJI", "^dji", "DJIA"),
       "SOX": ("^SOX", "^sox", None), "VIX": ("^VIX", "^vix", "VIXCLS")}
UA = {"User-Agent": "Mozilla/5.0 (tw-valuation; github.com/jey2204-creator/tw-valuation)"}


def fetch(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa
            print(f"[warn] {url}: {e}", file=sys.stderr); time.sleep(3 * (i + 1))
    return ""


def yahoo(sym):
    txt = fetch(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range=max&interval=1d&events=none")
    rows = []
    try:
        r = json.loads(txt)["chart"]["result"][0]
        ts, cl = r["timestamp"], r["indicators"]["quote"][0]["close"]
        for t, c in zip(ts, cl):
            if c is None:
                continue
            d = dt.datetime.fromtimestamp(t, dt.timezone.utc).astimezone(dt.timezone(dt.timedelta(hours=-5))).strftime("%Y-%m-%d")
            if d >= START:
                rows.append([d, round(float(c), 2)])
    except Exception as e:  # noqa
        print(f"[warn] yahoo {sym}: {e} {txt[:120]!r}", file=sys.stderr)
    return rows


def stooq(sym):
    txt = fetch(f"https://stooq.com/q/d/l/?s={sym}&i=d")
    if "Date" not in txt[:200]:
        print(f"[warn] stooq {sym}: {txt[:120]!r}", file=sys.stderr)
    rows = []
    for r in csv.DictReader(io.StringIO(txt)):
        d, c = r.get("Date"), r.get("Close")
        if d and c and d >= START:
            try:
                rows.append([d, round(float(c), 2)])
            except ValueError:
                pass
    return rows


def fred(sid):
    txt = fetch(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}")
    rows = []
    for r in csv.reader(io.StringIO(txt)):
        if len(r) == 2 and r[0] >= START:
            try:
                rows.append([r[0], round(float(r[1]), 2)])
            except ValueError:
                pass
    return rows


def main():
    old = {}
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text()).get("s", {})
        except Exception:  # noqa
            pass
    out, src = {}, {}
    for k, (ya, sq, fr) in IDX.items():
        rows, src[k] = yahoo(ya), "yahoo"
        if len(rows) <= 500:
            rows, src[k] = stooq(sq), "stooq"
        if len(rows) <= 500:
            rows, src[k] = (fred(fr) if fr else []), "fred"
        if len(rows) <= 500:
            src[k] = "old"
        if len(rows) <= 500:
            rows = old.get(k, [])
            print(f"[warn] {k}: 來源失敗，沿用舊資料 {len(rows)} 筆", file=sys.stderr)
        out[k] = rows
        print(f"{k}: {len(rows)} 筆 {rows[0][0] if rows else '-'} ~ {rows[-1][0] if rows else '-'} ({src[k]})")
        time.sleep(1.5)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "src": src, "s": out},
                              ensure_ascii=False, separators=(",", ":")))
    print("寫入", OUT)


if __name__ == "__main__":
    main()
