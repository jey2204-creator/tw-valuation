"""美股四大指數日線＋VIX → us/data/index_px.json
用法：python us/fetch_index.py
來源順序（每檔獨立）：Nasdaq 歷史報價 API → Yahoo chart → Stooq → FRED → 沿用舊資料
只用 Python 標準函式庫。失敗原因寫進輸出 JSON 的 log（Actions 的 log 無法下載）。

輸出：
{
  "updated": "2026-10-23T22:40:00Z",
  "src": {"SPX": "nasdaq", ...},
  "log": ["..."],
  "s": { "SPX": [[ "2000-01-03", 1455.22 ], ...], "NDX": [...], "DJI": [...], "SOX": [...], "VIX": [...] }
}
"""
import csv, io, json, sys, time, datetime as dt
from pathlib import Path
import urllib.request, urllib.parse, urllib.error

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "index_px.json"
START = "2000-01-01"
# 代號: (Nasdaq 代號, Yahoo 代號, Stooq 代號, FRED 代號或 None)
IDX = {"SPX": (["SPX", "spx", "INX", "^SPX", "S&P 500"], "^GSPC", "^spx", "SP500"), "NDX": (["NDX"], "^NDX", "^ndx", "NASDAQ100"),
       "DJI": (["DJI", "DJIA", "INDU", "^DJI", "DOW"], "^DJI", "^dji", "DJIA"),
       "SOX": (["SOX"], "^SOX", "^sox", None), "VIX": (["VIX", "VXX", "^VIX"], "^VIX", "^vix", "VIXCLS")}
# Cboe 公開 CSV（VIX 最可靠）
CBOE = {"VIX": "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv",
        "SPX": "https://cdn.cboe.com/api/global/us_indices/daily_prices/SPX_History.csv"}
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9"}
NQ_H = dict(UA, Origin="https://www.nasdaq.com", Referer="https://www.nasdaq.com/")
LOG = []


def warn(msg):
    print("[warn]", msg, file=sys.stderr); LOG.append(msg[:160])


import http.cookiejar
JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(JAR))


def fetch(url, tries=2, timeout=25, headers=UA):
    for i in range(tries):
        try:
            with OPENER.open(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            body = e.read()[:100].decode("utf-8", "replace")
            warn(f"{url[:70]}: HTTP {e.code} {body!r}"); time.sleep(3 * (i + 1))
        except Exception as e:  # noqa
            warn(f"{url[:70]}: {e}"); time.sleep(3 * (i + 1))
    return ""


def num(s):
    try:
        return round(float(str(s).replace(",", "").replace("$", "").strip()), 2)
    except ValueError:
        return None


def nasdaq(sym):
    today = dt.date.today().isoformat()
    url = f"https://api.nasdaq.com/api/quote/{urllib.parse.quote(sym)}/historical?assetclass=index&fromdate={START}&todate={today}&limit=20000"
    txt = fetch(url, headers=NQ_H, tries=1)
    rows = []
    try:
        for r in ((json.loads(txt).get("data") or {}).get("tradesTable") or {}).get("rows") or []:
            m, d, y = r["date"].split("/")
            c = num(r.get("close"))
            if c:
                rows.append([f"{y}-{m}-{d}", c])
    except Exception as e:  # noqa
        warn(f"nasdaq {sym}: {e} {txt[:100]!r}")
    rows.sort()
    if len(rows) <= 500:
        warn(f"nasdaq {sym}: {len(rows)} rows {txt[:100]!r}")
    return [r for r in rows if r[0] >= START]


def cboe(k):
    if k not in CBOE:
        return []
    txt = fetch(CBOE[k])
    rows = []
    for r in csv.reader(io.StringIO(txt)):
        # DATE,OPEN,HIGH,LOW,CLOSE
        if len(r) >= 5 and r[0][:2] in ("19", "20"):
            d, c = r[0][:10].replace("/", "-"), num(r[4])
            if "/" in r[0]:  # MM/DD/YYYY
                m, dd, y = r[0].split("/"); d = f"{y}-{m}-{dd}"
            if c and d >= START:
                rows.append([d, c])
    if len(rows) <= 500:
        warn(f"cboe {k}: {len(rows)} rows {txt[:100]!r}")
    rows.sort()
    return rows


def yahoo(sym):
    rows, txt = [], ""
    if not any(c.domain.endswith("yahoo.com") for c in JAR):
        fetch("https://fc.yahoo.com/", tries=1, timeout=15)   # 先拿 cookie，少被 429
    for host in ("query1", "query2"):
        txt = fetch(f"https://{host}.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range=max&interval=1d&events=none", tries=1)
        if '"timestamp"' in txt:
            break
    try:
        r = json.loads(txt)["chart"]["result"][0]
        for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]):
            if c is None:
                continue
            d = dt.datetime.fromtimestamp(t, dt.timezone.utc).astimezone(dt.timezone(dt.timedelta(hours=-5))).strftime("%Y-%m-%d")
            if d >= START:
                rows.append([d, round(float(c), 2)])
    except Exception as e:  # noqa
        warn(f"yahoo {sym}: {e} {txt[:100]!r}")
    return rows


def stooq(sym):
    txt = fetch(f"https://stooq.com/q/d/l/?s={sym}&i=d", tries=1)
    if "Date" not in txt[:200]:
        warn(f"stooq {sym}: {txt[:100]!r}")
    rows = []
    for r in csv.DictReader(io.StringIO(txt)):
        d, c = r.get("Date"), num(r.get("Close"))
        if d and c and d >= START:
            rows.append([d, c])
    return rows


def fred(sid):
    txt = fetch(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", timeout=90)
    rows = []
    for r in csv.reader(io.StringIO(txt)):
        if len(r) == 2 and r[0] >= START:
            c = num(r[1])
            if c:
                rows.append([r[0], c])
    return rows


def main():
    old = {}
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text()).get("s", {})
        except Exception:  # noqa
            pass
    out, src = {}, {}
    for k, (nqs, ya, sq, fr) in IDX.items():
        rows, src[k] = [], "nasdaq"
        for nq in nqs:
            rows = nasdaq(nq)
            if len(rows) > 500:
                break
        if len(rows) <= 500:
            rows, src[k] = cboe(k), "cboe"
        if len(rows) <= 500:
            rows, src[k] = yahoo(ya), "yahoo"
        if len(rows) <= 500:
            rows, src[k] = stooq(sq), "stooq"
        if len(rows) <= 500 and fr:
            rows, src[k] = fred(fr), "fred"
        if len(rows) <= 500:
            rows, src[k] = old.get(k, []), "old"
            warn(f"{k}: 來源全部失敗，沿用舊資料 {len(rows)} 筆")
        out[k] = rows
        print(f"{k}: {len(rows)} 筆 {rows[0][0] if rows else '-'} ~ {rows[-1][0] if rows else '-'} ({src[k]})")
        time.sleep(1.5)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "src": src, "log": LOG[:60], "s": out},
                              ensure_ascii=False, separators=(",", ":")))
    print("寫入", OUT)


if __name__ == "__main__":
    main()
