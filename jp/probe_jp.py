"""日股資料來源探路：在 GitHub Actions 上逐一測試各來源能否抓到資料、延遲多少。

⚠️ J-Quants 條款禁止把取得的資料以可瀏覽的形式散布，repo 又是公開的，
   所以這支程式只記錄「中繼資料」：HTTP 狀態、耗時、筆數、日期範圍、欄位名稱、
   哪些欄位有值（True/False），一律不寫入股價、營收、EPS 等數值。
   Yahoo／TDnet 也比照辦理。

結果寫到 jp/data/probe.json。JQUANTS_API_KEY 沒設定時跳過 J-Quants。
主要用標準函式庫；yfinance 若有安裝就多測一項。
"""
import io, json, os, re, time, zipfile, datetime as dt
import urllib.request, urllib.parse, urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
KEY = os.environ.get("JQUANTS_API_KEY", "").strip()
OUT = os.path.join(os.path.dirname(__file__), "data", "probe.json")
NOW_JST = dt.datetime.utcnow() + dt.timedelta(hours=9)
TODAY = NOW_JST.date()
JQ = "https://api.jquants.com/v2"
SAMPLE = ["8035", "6981", "4063"]          # 東京威力、村田、信越（原型 3 檔）

results = {}


def http(url, headers=None, timeout=40):
    h = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.8"}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h)
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), round(time.time() - t, 2)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300], round(time.time() - t, 2)


def probe(name, fn):
    try:
        r = fn()
        r.setdefault("ok", True)
    except Exception as e:  # noqa
        r = {"ok": False, "err": f"{type(e).__name__}: {str(e)[:300]}"}
    results[name] = r
    print(name, "OK" if r.get("ok") else "FAIL", json.dumps(r, ensure_ascii=False)[:500])


def days_ago(d):
    return (TODAY - dt.date.fromisoformat(d[:10])).days if d else None


def filled(rec):
    """只回傳「哪些欄位有值」，不回傳數值本身。"""
    return sorted(k for k, v in rec.items() if v not in ("", None))


# ======================= J-Quants（需要金鑰） =======================
_last_plan_call = [0.0]


def jq(path, params, plan_pool=True):
    """免費方案一般端點 5 次／分（fins/* 另有 60 次／分）→ 一般端點每次間隔 13 秒。
    遇 429 等 75 秒重試一次（官方建議至少等 1 分鐘）。"""
    if plan_pool:
        wait = 13 - (time.time() - _last_plan_call[0])
        if wait > 0:
            time.sleep(wait)
    url = f"{JQ}{path}?{urllib.parse.urlencode(params)}"
    for attempt in range(2):
        s, b, t = http(url, {"x-api-key": KEY, "Accept": "application/json"})
        if plan_pool:
            _last_plan_call[0] = time.time()
        if s == 429 and attempt == 0:
            print("429，等 75 秒")
            time.sleep(75)
            continue
        break
    try:
        j = json.loads(b) if s == 200 else {}
    except Exception:  # noqa
        j = {}
    return s, j, t, (b[:200].decode("utf-8", "replace") if s != 200 else "")


def jq_master():
    out = {}
    for code in ("8035", "285A"):          # 285A = 鎧俠（英數代號）
        s, j, t, err = jq("/equities/master", {"code": code})
        d = j.get("data", [])
        out[code] = {"status": s, "sec": t, "n": len(d), "err": err,
                     "code_returned": d[0].get("Code") if d else None,
                     "date": d[0].get("Date") if d else None,
                     "name": d[0].get("CoName") if d else None,
                     "fields": list(d[0].keys()) if d else []}
    return {"items": out, "ok": all(v["status"] == 200 for v in out.values())}


def jq_bars():
    s, j, t, err = jq("/equities/bars/daily", {"code": "8035"})
    d = j.get("data", [])
    dates = sorted(x.get("Date") for x in d if x.get("Date"))
    return {"status": s, "sec": t, "n": len(d), "err": err,
            "first": dates[0] if dates else None, "last": dates[-1] if dates else None,
            "last_days_ago": days_ago(dates[-1]) if dates else None,
            "has_pagination_key": bool(j.get("pagination_key")),
            "fields": list(d[0].keys()) if d else [],
            "split_events": sum(1 for x in d if x.get("ExRT") not in (None, "")),
            "ok": s == 200}


def jq_valuation():
    s, j, t, err = jq("/equities/valuation", {"code": "8035"})
    d = j.get("data", [])
    dates = sorted(x.get("Date") for x in d if x.get("Date"))
    last = max(d, key=lambda x: x.get("Date", "")) if d else {}
    return {"status": s, "sec": t, "n": len(d), "err": err,
            "first": dates[0] if dates else None, "last": dates[-1] if dates else None,
            "last_days_ago": days_ago(dates[-1]) if dates else None,
            "fields": list(d[0].keys()) if d else [], "last_filled": filled(last),
            "ok": s == 200}


def jq_calendar():
    s, j, t, err = jq("/equities/earnings-calendar", {})
    d = j.get("data", [])
    dates = sorted({x.get("Date") for x in d if x.get("Date")})
    codes = {str(x.get("Code", ""))[:4] for x in d}
    return {"status": s, "sec": t, "n": len(d), "err": err,
            "dates": dates[:10], "fields": list(d[0].keys()) if d else [],
            "sample_in_calendar": {c: (c in codes) for c in SAMPLE},
            "ok": s == 200}


def jq_bars_by_date():
    """日期查詢 = 全市場一天一次（之後每日更新會用到），看筆數與是否分頁。"""
    bars = results.get("jq_bars", {})
    day = (bars.get("last") or "").replace("-", "")
    if not day:
        return {"ok": False, "err": "沒有可用日期（jq_bars 失敗）"}
    s, j, t, err = jq("/equities/bars/daily", {"date": day})
    d = j.get("data", [])
    return {"status": s, "sec": t, "date": day, "n": len(d), "err": err,
            "has_pagination_key": bool(j.get("pagination_key")), "ok": s == 200}


def jq_fins():
    out = {}
    for code in SAMPLE:
        s, j, t, err = jq("/fins/summary", {"code": code}, plan_pool=False)
        time.sleep(1.5)
        d = sorted(j.get("data", []), key=lambda x: (x.get("DiscDate", ""), x.get("DiscTime", "")))
        periods = [[x.get("DiscDate"), x.get("CurPerType"), x.get("CurPerEn"),
                    x.get("DocType")] for x in d]
        last = d[-1] if d else {}
        out[code] = {"status": s, "sec": t, "n": len(d), "err": err,
                     "periods": periods[-12:],
                     "last_disc_days_ago": days_ago(last.get("DiscDate")) if last else None,
                     "last_filled": filled(last)}
    return {"items": out, "ok": all(v["status"] == 200 for v in out.values())}


# ======================= Yahoo（免金鑰） =======================
def yahoo_chart():
    s, b, t = http("https://query1.finance.yahoo.com/v8/finance/chart/8035.T"
                   "?range=10y&interval=1d&events=div%2Csplit&includeAdjustedClose=true")
    j = json.loads(b) if s == 200 else {}
    r = (j.get("chart", {}).get("result") or [{}])[0]
    ts = r.get("timestamp") or []
    ind = r.get("indicators", {})
    day = lambda x: (dt.datetime.utcfromtimestamp(x) + dt.timedelta(hours=9)).strftime("%Y-%m-%d")
    splits = r.get("events", {}).get("splits", {})
    return {"status": s, "sec": t, "n": len(ts),
            "first": day(ts[0]) if ts else None, "last": day(ts[-1]) if ts else None,
            "last_days_ago": days_ago(day(ts[-1])) if ts else None,
            "has_adjclose": bool(ind.get("adjclose")),
            "splits": sorted(day(int(k)) for k in splits),
            "currency": r.get("meta", {}).get("currency"), "ok": s == 200 and bool(ts)}


YF_TYPES = ["TotalRevenue", "GrossProfit", "OperatingIncome", "NetIncomeCommonStockholders",
            "DilutedEPS", "DilutedAverageShares", "StockholdersEquity", "CapitalExpenditure"]


def yahoo_fundamentals():
    """yfinance 背後用的 fundamentals-timeseries；只記錄每個科目有哪些期別。"""
    out = {}
    p2 = int(time.time())
    p1 = p2 - 6 * 366 * 86400
    for freq in ("quarterly", "annual"):
        types = ",".join(freq + x for x in YF_TYPES)
        s, b, t = http("https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/"
                       f"timeseries/8035.T?symbol=8035.T&type={types}&period1={p1}&period2={p2}")
        per = {}
        if s == 200:
            for res in json.loads(b).get("timeseries", {}).get("result", []):
                typ = (res.get("meta", {}).get("type") or [""])[0]
                rows = [x for x in (res.get(typ) or []) if x]
                per[typ.replace(freq, "")] = [x.get("asOfDate") for x in rows]
        out[freq] = {"status": s, "sec": t, "periods": per}
        time.sleep(1)
    q = out["quarterly"]["periods"].get("TotalRevenue", [])
    return {"items": out, "latest_quarter": max(q) if q else None, "ok": bool(q)}


def yfinance_lib():
    import yfinance as yf  # noqa
    tk = yf.Ticker("8035.T")
    qi = tk.quarterly_income_stmt
    hist = tk.history(period="5d")
    cols = [str(c)[:10] for c in qi.columns] if qi is not None else []
    rows = list(qi.index) if qi is not None else []
    has = lambda name: {str(c)[:10]: bool(qi.loc[name, c] == qi.loc[name, c]) for c in qi.columns} \
        if qi is not None and name in qi.index else {}
    return {"version": getattr(yf, "__version__", "?"), "quarters": cols, "n_rows": len(rows),
            "has_revenue": has("Total Revenue"), "has_diluted_eps": has("Diluted EPS"),
            "price_last": str(hist.index[-1])[:10] if len(hist) else None, "ok": bool(cols)}


# ======================= TDnet（決算短信 XBRL，免金鑰） =======================
def tdnet():
    """TDnet 公開頁只保留約 1 個月；找最近幾天有附 XBRL 的決算短信，下載一個看檔案結構。"""
    days, found = [], None
    d = TODAY
    for _ in range(8):
        if d.weekday() < 5:
            url = f"https://www.release.tdnet.info/inbs/I_list_001_{d:%Y%m%d}.html"
            s, b, t = http(url)
            html = b.decode("utf-8", "replace") if s == 200 else ""
            rows = re.findall(r"<tr>(.*?)</tr>", html, re.S)
            tanshin = [r for r in rows if "決算短信" in r]
            xbrl = [r for r in tanshin if ".zip" in r]
            days.append({"date": f"{d:%Y-%m-%d}", "status": s, "sec": t, "rows": len(rows),
                         "tanshin": len(tanshin), "tanshin_xbrl": len(xbrl),
                         "more_pages": "I_list_002_" in html})
            if xbrl and not found:
                m = re.search(r'href="([^"]+\.zip)"', xbrl[0])
                code = re.search(r'kjCode"[^>]*>\s*([0-9A-Z]{4,5})', xbrl[0])
                found = {"date": f"{d:%Y-%m-%d}", "zip": m.group(1) if m else None,
                         "code": code.group(1) if code else None}
            time.sleep(1)
        d -= dt.timedelta(days=1)
    z = {}
    if found and found.get("zip"):
        s, b, t = http("https://www.release.tdnet.info/inbs/" + found["zip"])
        z = {"status": s, "sec": t, "bytes": len(b)}
        if s == 200:
            names = zipfile.ZipFile(io.BytesIO(b)).namelist()
            z["files"] = names[:40]
            z["has_summary_ixbrl"] = any("ixbrl" in n.lower() and "sm" in n.lower() for n in names)
    return {"days": days, "sample": found, "zip": z,
            "ok": any(x["status"] == 200 for x in days)}


# ======================= Stooq（股價備援，免金鑰） =======================
def stooq():
    s, b, t = http("https://stooq.com/q/d/l/?s=8035.jp&i=d")
    lines = b.decode("utf-8", "replace").strip().splitlines() if s == 200 else []
    is_csv = bool(lines) and lines[0].startswith("Date")
    last = lines[-1].split(",")[0] if is_csv and len(lines) > 1 else None
    return {"status": s, "sec": t, "n": max(len(lines) - 1, 0), "is_csv": is_csv,
            "head": lines[0][:80] if lines else "", "last": last,
            "last_days_ago": days_ago(last) if last else None, "ok": is_csv}


if __name__ == "__main__":
    t0 = time.time()
    if KEY:
        probe("jq_master", jq_master)
        probe("jq_bars", jq_bars)
        probe("jq_valuation", jq_valuation)
        probe("jq_calendar", jq_calendar)
        probe("jq_bars_by_date", jq_bars_by_date)
        probe("jq_fins", jq_fins)
    else:
        results["jquants"] = {"ok": False, "err": "未設定 JQUANTS_API_KEY，跳過"}
    probe("yahoo_chart", yahoo_chart)
    probe("yahoo_fundamentals", yahoo_fundamentals)
    probe("yfinance_lib", yfinance_lib)
    probe("tdnet", tdnet)
    probe("stooq", stooq)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"asof": NOW_JST.strftime("%Y-%m-%d %H:%M JST"), "key_set": bool(KEY),
                   "sec": round(time.time() - t0, 1), "results": results},
                  f, ensure_ascii=False, indent=1)
    print("寫入", OUT)
