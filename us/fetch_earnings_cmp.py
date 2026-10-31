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


def reaction(tk, date, hour, px=None):
    """財報後首個交易日收盤 vs 財報前收盤。amc／未定 → 前=當天收盤、後=下一交易日；bmo → 前=前一交易日、後=當天。
    px 可傳入已抓好的整段股價（近 8 季共用一次 FinMind 呼叫）。"""
    d = dt.date.fromisoformat(date)
    if px is None:
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


SEC_UA = os.environ.get("SEC_UA", "").strip()
_TICK = {}


def cik_of(tk):
    for f in (ROOT / "data" / f"{tk}.json", ROOT / "data" / "all" / f"{tk}.json"):
        try:
            c = json.loads(f.read_text()).get("cik")
            if c: return int(c)
        except Exception:
            pass
    if not _TICK:
        js = http("https://www.sec.gov/files/company_tickers.json", {"User-Agent": SEC_UA or UA["User-Agent"]}) or {}
        for v in js.values():
            _TICK[v["ticker"].upper()] = int(v["cik_str"])
    return _TICK.get(tk.upper().replace("-", "."), _TICK.get(tk.upper()))


def sec_releases(tk):
    """近兩年 8-K Item 2.02（業績發布）→ [(申報日, 盤前/盤後)]，舊→新。接收時間美東 09:30 前＝bmo、16:00 後＝amc、其他＝dmh。"""
    if not SEC_UA:
        return []
    cik = cik_of(tk)
    if not cik:
        return []
    time.sleep(0.15)   # SEC 10 次/秒
    js = http(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", {"User-Agent": SEC_UA}) or {}
    rec = js.get("filings", {}).get("recent", {})
    out = []
    lo = (dt.date.today() - dt.timedelta(days=760)).isoformat()
    for form, d, acc, items in zip(rec.get("form", []), rec.get("filingDate", []), rec.get("acceptanceDateTime", []), rec.get("items", [])):
        if form not in ("8-K", "8-K/A") or "2.02" not in (items or "") or d < lo:
            continue
        hm = (acc or "")[11:16]
        hr = "bmo" if hm < "09:30" else ("amc" if hm >= "16:00" else "dmh")
        if out and out[-1][0] == d:
            continue   # 同日多份（8-K/A）只留一份
        out.append((d, hr))
    out.sort()
    return out


def fq_table(tk):
    """回傳 函式(公布日)→季別：用 SEC 財報檔的季末日（公布日前 0～100 天內最近的一季），沒有財報檔就用日曆季。"""
    ends = []
    for f in (ROOT / "data" / f"{tk}.json", ROOT / "data" / "all" / f"{tk}.json"):
        try:
            for r in json.loads(f.read_text()).get("q", []):
                if r[0] and r[9]:
                    ends.append((r[9], r[0]))
            if ends: break
        except Exception:
            pass
    ends.sort()

    def fq(d8):
        c = [e for e in ends if e[0] < d8 and (dt.date.fromisoformat(d8) - dt.date.fromisoformat(e[0])).days <= 100]
        if c:
            return c[-1][1]
        dd = dt.date.fromisoformat(d8) - dt.timedelta(days=20)   # 日曆季：公布日往前 20 天所在的上一季
        q = (dd.month - 1) // 3   # 0..3 = 目前日曆季，上一季 = q-1
        y, pq = (dd.year, q) if q > 0 else (dd.year - 1, 4)
        return f"{str(y)[-2:]}Q{pq}"

    def relabel(period, label):
        if not period or not ends:
            return label
        pd = dt.date.fromisoformat(period)
        near = [(abs((dt.date.fromisoformat(e) - pd).days), lab) for e, lab in ends]
        near.sort()
        return near[0][1] if near and near[0][0] <= 10 else label
    return fq, relabel


def one(tk, override, since=""):
    today = dt.date.today()
    # 1. 歷史驚喜（含最新一季）
    hist_raw = fh("stock/earnings", symbol=tk, limit=8) or []   # 免費方案實際只回 4 季
    hist, periods = [], {}
    for r in sorted(hist_raw, key=lambda x: x.get("period") or ""):
        if r.get("period") and r.get("actual") is not None:
            p = r["period"]; periods[f"{p[2:4]}Q{r.get('quarter') or ''}"] = p
            hist.append([f"{p[2:4]}Q{r.get('quarter') or ''}", r.get("estimate"), r.get("actual"),
                         surprise(r.get("actual"), r.get("estimate"))])
    # 2. 最新一季日曆（營收）
    cal = fh("calendar/earnings", symbol=tk, **{"from": (today - dt.timedelta(days=740)).isoformat(),
                                               "to": (today + dt.timedelta(days=5)).isoformat()}) or {}
    rows = [r for r in (cal.get("earningsCalendar") or []) if r.get("date") and r["date"] <= today.isoformat()]
    rows.sort(key=lambda r: r["date"])
    last = rows[-1] if rows else {}
    # 近 8 季每季的公布日／盤前盤後／首日反應（給財報公布日頁的個股搜尋）：
    # Finnhub 免費方案日曆只有最近一季、驚喜率只有 4 季，所以公布日改用 SEC 8-K（Item 2.02 業績發布）的申報日，
    # 盤前／盤後看 8-K 的接收時間（美東 09:30 前＝盤前、16:00 後＝盤後）；季別用 SEC 財報檔（data/{T}.json 或 data/all/{T}.json）
    # 的季末日對上，沒有財報檔就用日曆季；首日反應整段股價只抓一次。hist 列 = [fq, est, act, surp, date, hour, react]
    rels = sec_releases(tk)[-8:]
    if rels:
        fqof, relabel = fq_table(tk)
        for h in hist:   # Finnhub 的季別是會計年度（AAPL 的 26Q3＝曆年 26Q2），改成 SEC 財報檔的標籤，才對得上 8-K
            h[0] = relabel(periods.get(h[0]), h[0])
        byfq = {h[0]: h for h in hist}
        rows8 = []
        for d8, hr in rels:
            fq = fqof(d8)
            h = byfq.get(fq) or [fq, None, None, None]
            if len(h) < 5:
                h.extend([d8, hr, None])
            else:
                h[4], h[5] = d8, hr
            rows8.append(h)
        hist = rows8
        pxall = finmind_px(tk, (today - dt.timedelta(days=760)).isoformat(), today.isoformat())
        for h in hist:
            rx = reaction(tk, h[4], h[5], pxall) if pxall and h[4] else None
            h[6] = rx and rx.get("react")
    else:
        for h in hist:
            if len(h) < 5:
                h.extend([None, "", None])
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
            "hist": hist[-8:], "px": px}


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
    # 主題股（data/index.json）＋首頁日曆的大型股（MEGA，與 index.html 同一份）本季已公布的也抓，
    # 給首頁／財報公布日頁「已公布」頁籤的驚喜率與首日漲跌用；它們不在 earnings_cmp 名單，財報對照頁不會列出
    MEGA = ['AAPL','TSLA','NFLX','ORCL','TSM','ASML','QCOM','INTC','TXN','IBM','COST','WMT','JPM','PLTR','CRWD','ANET','VRT','DELL','HPE','ADBE','CRM','NOW','UBER','V','MA','BRK-B','LLY','UNH','XOM']
    lo = cmp.get("since") or (dt.date.today() - dt.timedelta(days=92)).isoformat()
    try:
        idx = [s["id"] for s in json.loads((ROOT / "data" / "index.json").read_text())] + MEGA
        for tk in idx:   # 全部都問 Finnhub（日曆只回溯 7 天，不能靠它篩），公布日早於 since 的在下面丟掉；約 75 檔 × 2 次呼叫 ≈ 3 分鐘
            if tk not in tickers:
                tickers.append(tk); overrides[tk] = {"_theme": True}
    except Exception as e:  # noqa
        print(f"[warn] 主題股名單: {e}", file=sys.stderr)
    old = {}
    try:
        old = json.loads(OUT.read_text()).get("q", {})
    except Exception:
        pass
    out = {}
    for tk in tickers:
        try:
            ov = overrides.get(tk, {})
            r = one(tk, {} if ov.get("_theme") else ov, "" if ov.get("_theme") else cmp.get("since", ""))
            if r and ov.get("_theme") and r["date"] < lo:
                r = None   # 主題股／大型股只留本季（since 之後）公布的
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
