"""美股財報對照（預期 vs 實際）自動層：Finnhub 驚喜率 + FinMind 財報後首日股價 → us/data/earnings_auto.json
用法：python us/fetch_earnings_cmp.py
環境變數：FINNHUB_KEY（必要）、FINMIND_TOKEN（可選，加大額度）
只用 Python 標準函式庫。

讀 us/data/earnings_cmp.json 的 companies[].ticker 與 watch[]（只收 since 之後公布的），對每檔抓：
  - Finnhub /stock/earnings      → 近 4 季 EPS 預估／實際／驚喜率（hist）
  - Finnhub /calendar/earnings   → 最新一季 EPS／營收 預估與實際（免費方案營收常為 null）
  - FinMind USStockPrice         → 財報前收盤、財報後首個交易日收盤 → 反應 %

輸出：
{
  "updated": "...Z",
  "q": { "META": { "date": "2026-10-21", "hour": "amc", "fq": "26Q3",
                   "epsEst": 6.52, "epsAct": 7.40, "epsSurp": 13.5,
                   "revEst": 6.33e10, "revAct": 6.46e10, "revSurp": 2.0,
                   "hist": [["25Q4", est, act, surp%], ...],      # 舊→新，最多 4 季
                   "px": { "prev": 648.0, "prevDate": "2026-10-21", "first": 697.5, "firstDate": "2026-10-22", "react": 7.6 } } }
}
"""
import json, os, sys, time, datetime as dt
from pathlib import Path
import urllib.request, urllib.parse, urllib.error

ROOT = Path(__file__).resolve().parent
CMP = ROOT / "data" / "earnings_cmp.json"
OUT = ROOT / "data" / "earnings_auto.json"
KEY = os.environ.get("FINNHUB_KEY", "").strip()
FM_TOKEN = os.environ.get("FINMIND_TOKEN", "").strip()
FH = "https://finnhub.io/api/v1"
FM = "https://api.finmindtrade.com/api/v4/data"
UA = {"User-Agent": "tw-valuation"}


def http(url, headers=None, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={**UA, **(headers or {})}), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(5 * (i + 1)); continue
            print(f"[warn] {url.split('?')[0]}: HTTP {e.code}", file=sys.stderr); return None
        except Exception as e:  # noqa
            print(f"[warn] {url.split('?')[0]}: {e}", file=sys.stderr); time.sleep(3)
    return None


def fh(path, **params):
    time.sleep(1.1)  # 免費方案 60 次/分
    return http(f"{FH}/{path}?{urllib.parse.urlencode({**params, 'token': KEY})}")


def finmind_px(tk, start, end):
    q = urllib.parse.urlencode(dict(dataset="USStockPrice", data_id=tk, start_date=start, end_date=end))
    js = http(f"{FM}?{q}", {"Authorization": "Bearer " + FM_TOKEN} if FM_TOKEN else {}) or {}
    rows = js.get("data") or []
    return sorted([(r["date"], float(r["Close"])) for r in rows if r.get("Close")], key=lambda x: x[0])


def pct(a, b):
    try:
        return round((a / b - 1) * 100, 1) if a is not None and b not in (None, 0) else None
    except Exception:
        return None


def surprise(act, est):
    if act is None or est is None or est == 0:
        return None
    return round((act - est) / abs(est) * 100, 1)


def reaction(tk, date, hour):
    """財報後首個交易日收盤 vs 財報前收盤。amc／未定 → 前=當天收盤、後=下一交易日；bmo → 前=前一交易日、後=當天。"""
    d = dt.date.fromisoformat(date)
    px = finmind_px(tk, (d - dt.timedelta(days=10)).isoformat(), (d + dt.timedelta(days=10)).isoformat())
    if not px:
        return None
    before = [p for p in px if p[0] <= date]
    after = [p for p in px if p[0] > date]
    if hour == "bmo":
        prev = [p for p in px if p[0] < date][-1:]
        first = [p for p in px if p[0] >= date][:1]
    else:
        prev, first = before[-1:], after[:1]
    if not prev or not first:
        return {"prev": prev[0][1] if prev else None, "prevDate": prev[0][0] if prev else None,
                "first": None, "firstDate": None, "react": None}
    return {"prev": prev[0][1], "prevDate": prev[0][0], "first": first[0][1], "firstDate": first[0][0],
            "react": pct(first[0][1], prev[0][1])}


def one(tk, override, since=""):
    today = dt.date.today()
    # 1. 歷史驚喜（含最新一季）
    hist_raw = fh("stock/earnings", symbol=tk, limit=4) or []
    hist = []
    for r in sorted(hist_raw, key=lambda x: x.get("period") or ""):
        if r.get("period") and r.get("actual") is not None:
            p = r["period"]
            hist.append([f"{p[2:4]}Q{r.get('quarter') or ''}", r.get("estimate"), r.get("actual"),
                         surprise(r.get("actual"), r.get("estimate"))])
    # 2. 最新一季日曆（營收）
    cal = fh("calendar/earnings", symbol=tk, **{"from": (today - dt.timedelta(days=120)).isoformat(),
                                               "to": (today + dt.timedelta(days=5)).isoformat()}) or {}
    rows = [r for r in (cal.get("earningsCalendar") or []) if r.get("date") and r["date"] <= today.isoformat()]
    rows.sort(key=lambda r: r["date"])
    last = rows[-1] if rows else {}
    date = override.get("date") or last.get("date")
    if not date or (since and date < since and not override.get("date")):
        return None   # 還沒公布本季（watch 名單用）
    hour = override.get("hour") or last.get("hour") or ""
    eps_est = override.get("epsEst", last.get("epsEstimate"))
    eps_act = override.get("epsAct", last.get("epsActual"))
    if eps_act is None and hist:
        eps_est, eps_act = hist[-1][1], hist[-1][2]
    rev_est = override.get("revEst", last.get("revenueEstimate"))
    rev_act = override.get("revAct", last.get("revenueActual"))
    fq = f"{str(last.get('year'))[-2:]}Q{last.get('quarter')}" if last.get("year") and last.get("quarter") else (hist[-1][0] if hist else "")
    px = reaction(tk, date, hour) if dt.date.fromisoformat(date) <= today else None
    return {"date": date, "hour": hour, "fq": fq,
            "epsEst": eps_est, "epsAct": eps_act, "epsSurp": surprise(eps_act, eps_est),
            "revEst": rev_est, "revAct": rev_act, "revSurp": surprise(rev_act, rev_est),
            "hist": hist[-4:], "px": px}


def main():
    if not KEY:
        print("缺 FINNHUB_KEY", file=sys.stderr); sys.exit(1)
    cmp = json.loads(CMP.read_text()) if CMP.exists() else {}
    tickers, overrides = [], {}
    for c in cmp.get("companies", []):
        tickers.append(c["ticker"]); overrides[c["ticker"]] = c.get("auto") or {}
    for t in cmp.get("watch", []):
        if t not in tickers:
            tickers.append(t)
    old = {}
    try:
        old = json.loads(OUT.read_text()).get("q", {})
    except Exception:
        pass
    out = {}
    for tk in tickers:
        try:
            r = one(tk, overrides.get(tk, {}), cmp.get("since", ""))
        except Exception as e:  # noqa
            print(f"[warn] {tk}: {e}", file=sys.stderr); r = None
        if r:
            out[tk] = r
            print(f"{tk}: {r['date']} {r['hour'] or '-'} EPS {r['epsAct']} vs {r['epsEst']} ({r['epsSurp']}%)"
                  f" react {r['px'] and r['px'].get('react')}%", file=sys.stderr)
        elif tk in old:
            out[tk] = old[tk]
    if not out:
        print("沒抓到任何資料，保留舊檔", file=sys.stderr); sys.exit(1)
    OUT.write_text(json.dumps({"updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "q": out},
                              ensure_ascii=False, separators=(",", ":")))
    print(f"earnings_auto.json：{len(out)} 檔")


if __name__ == "__main__":
    main()
