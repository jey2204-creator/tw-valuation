"""美股財報公布日：Finnhub 財報日曆 + Nasdaq 日曆（近 4 週補齊）→ us/data/earnings.json
用法：python us/fetch_earnings.py
環境變數：FINNHUB_KEY（GitHub Secrets；缺的話只用 Nasdaq）
只用 Python 標準函式庫。

輸出格式（只保留本站查得到的代號）：
{
  "updated": "2026-10-22T22:40:00Z",
  "range": ["2026-10-15", "2027-01-20"],      # 抓取區間：過去 7 天 ～ 未來 90 天
  "e": { "GOOGL": [ [date, hour, epsEst, epsAct, revEst, revAct, "26Q3"], ... ] }
}
hour：bmo = 盤前、amc = 盤後、dmh = 盤中、"" = 未定
每檔最多 3 筆（最近已公布 1 筆 + 未來 2 筆），依日期排序。
"""
import json, os, sys, time, datetime as dt
from pathlib import Path
import urllib.request, urllib.parse, urllib.error

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "earnings.json"
KEY = os.environ.get("FINNHUB_KEY", "").strip()
API = "https://finnhub.io/api/v1/calendar/earnings"
BACK, AHEAD, CHUNK = 7, 90, 30


def get(frm: str, to: str):
    url = f"{API}?{urllib.parse.urlencode({'from': frm, 'to': to, 'token': KEY})}"
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "tw-valuation"}), timeout=60) as r:
                return json.load(r).get("earningsCalendar") or []
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(5 * (i + 1)); continue
            print(f"[warn] {frm}~{to}: HTTP {e.code}", file=sys.stderr); return []
        except Exception as e:  # noqa
            print(f"[warn] {frm}~{to}: {e}", file=sys.stderr); time.sleep(3)
    return []


NQ = "https://api.nasdaq.com/api/calendar/earnings"
NQ_H = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*", "Origin": "https://www.nasdaq.com", "Referer": "https://www.nasdaq.com/"}
NQ_DAYS = 28   # Nasdaq 補近期（Finnhub 免費方案近兩週常是空的）


def num(s):
    try:
        return float(str(s).replace("$", "").replace(",", "").strip()) if s not in (None, "", "N/A") else None
    except ValueError:
        return None


def nasdaq_day(d: str):
    url = f"{NQ}?date={d}"
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=NQ_H), timeout=30) as r:
                rows = ((json.load(r).get("data") or {}).get("rows")) or []
                return [{"symbol": x.get("symbol"), "date": d, "hour": {"time-pre-market": "bmo", "time-after-hours": "amc"}.get(x.get("time"), ""),
                         "epsEstimate": num(x.get("epsForecast")), "fq": x.get("fiscalQuarterEnding") or ""} for x in rows if x.get("symbol")]
        except Exception as e:  # noqa
            print(f"[warn] nasdaq {d}: {e}", file=sys.stderr); time.sleep(3)
    return []


MON = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}


def fq_label(fq: str):
    # Nasdaq 只給會計季結束月："Sep/2026" → "季結 26/09"（Finnhub 有 年/季 時以 Finnhub 為準）
    try:
        m, y = fq.replace("/", " ").split()[:2]
        return f"季結 {y[-2:]}/{MON[m[:3]]:02d}"
    except Exception:
        return ""


def known_tickers():
    ids = set()
    for p in (ROOT / "data" / "index.json", ROOT / "data" / "all" / "index.json"):
        try:
            for s in json.loads(p.read_text()):
                ids.add(s["id"] if isinstance(s, dict) else s[0])
        except Exception:
            pass
    return ids


def main():
    if not KEY:
        print("[warn] 缺 FINNHUB_KEY，只用 Nasdaq", file=sys.stderr)
    today = dt.date.today()
    start, end = today - dt.timedelta(days=BACK), today + dt.timedelta(days=AHEAD)
    rows, d = [], start
    while d <= end:
        d2 = min(d + dt.timedelta(days=CHUNK - 1), end)
        rows += get(d.isoformat(), d2.isoformat()) if KEY else []; d = d2 + dt.timedelta(days=1)
        time.sleep(1.1)   # 免費方案 60 次/分
    ids = known_tickers()
    by = {}
    for r in rows:
        s = (r.get("symbol") or "").upper()
        if ids and s not in ids:
            continue
        q = f"{str(r.get('year'))[-2:]}Q{r.get('quarter')}" if r.get("year") and r.get("quarter") else ""
        by.setdefault(s, []).append([r.get("date"), r.get("hour") or "", r.get("epsEstimate"), r.get("epsActual"),
                                      r.get("revenueEstimate"), r.get("revenueActual"), q])
    # Nasdaq：近期逐日補齊（同一檔同一天以 Nasdaq 的日期／時段為準，Finnhub 的營收預估保留）
    nq = 0
    for i in range(-BACK, NQ_DAYS + 1):
        d = today + dt.timedelta(days=i)
        if d.weekday() >= 5:
            continue
        for r in nasdaq_day(d.isoformat()):
            s = r["symbol"].upper().replace(".", "-")
            if ids and s not in ids:
                continue
            nq += 1
            lst = by.setdefault(s, [])
            near = [x for x in lst if abs((dt.date.fromisoformat(x[0]) - d).days) <= 7]   # Finnhub 同一季的日期可能差幾天
            old = near[0] if near else [None, "", None, None, None, None, ""]
            for x in near:
                lst.remove(x)
            lst.append([r["date"], r["hour"] or old[1], r["epsEstimate"] if r["epsEstimate"] is not None else old[2],
                        old[3], old[4], old[5], old[6] or fq_label(r["fq"])])
        time.sleep(0.8)
    print(f"Nasdaq 補 {nq} 筆", file=sys.stderr)
    out = {}
    t = today.isoformat()
    for s, lst in by.items():
        lst = sorted({x[0]: x for x in lst if x[0]}.values(), key=lambda x: x[0])
        past = [x for x in lst if x[0] < t][-1:]
        fut = [x for x in lst if x[0] >= t][:2]
        if past or fut:
            out[s] = past + fut
    if not out:
        print("Finnhub 沒回資料，保留舊檔", file=sys.stderr); sys.exit(1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                               "range": [start.isoformat(), end.isoformat()], "e": out},
                              ensure_ascii=False, separators=(",", ":")))
    print(f"earnings.json：{len(out)} 檔（原始 {len(rows)} 筆）")


if __name__ == "__main__":
    main()
