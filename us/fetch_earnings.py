"""美股財報公布日：Finnhub 財報日曆 → us/data/earnings.json
用法：python us/fetch_earnings.py
環境變數：FINNHUB_KEY（必填，GitHub Secrets）
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
        print("缺 FINNHUB_KEY", file=sys.stderr); sys.exit(1)
    today = dt.date.today()
    start, end = today - dt.timedelta(days=BACK), today + dt.timedelta(days=AHEAD)
    rows, d = [], start
    while d <= end:
        d2 = min(d + dt.timedelta(days=CHUNK - 1), end)
        rows += get(d.isoformat(), d2.isoformat()); d = d2 + dt.timedelta(days=1)
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
