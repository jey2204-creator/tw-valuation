"""韓股資料來源探路：在 GitHub Actions 上逐一測試各來源能否抓到資料。
結果寫到 kr/data/probe.json（每個來源：ok、HTTP 狀態、耗時、筆數、樣本）。
只用 Python 標準函式庫。DART_KEY 沒設定時跳過 OpenDART。
"""
import io, json, os, re, time, zipfile, datetime as dt
import urllib.request, urllib.parse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
KEY = os.environ.get("DART_KEY", "").strip()
OUT = os.path.join(os.path.dirname(__file__), "data", "probe.json")
TODAY = dt.datetime.utcnow() + dt.timedelta(hours=9)   # 韓國時間


def http(url, data=None, headers=None, timeout=30):
    h = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "ko-KR,ko;q=0.9"}
    h.update(headers or {})
    if isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=data, headers=h)
    t = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        return r.status, body, round(time.time() - t, 2), r.headers.get("Content-Type", "")


def dec(b):
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", "replace")


results = {}


def probe(name, fn):
    try:
        r = fn()
        r.setdefault("ok", True)
    except Exception as e:  # noqa
        r = {"ok": False, "err": f"{type(e).__name__}: {str(e)[:300]}"}
    results[name] = r
    print(name, "OK" if r.get("ok") else "FAIL", json.dumps(r, ensure_ascii=False)[:400])
    time.sleep(1)


def last_trading_day():
    d = TODAY if TODAY.hour >= 16 else TODAY - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d.strftime("%Y%m%d")


# ---------- 股價 ----------
def naver_fchart():
    s, b, t, ct = http("https://fchart.stock.naver.com/sise.nhn?symbol=005930&timeframe=day&count=600&requestType=0")
    rows = re.findall(r'data="([^"]+)"', dec(b))
    return {"status": s, "sec": t, "n": len(rows), "first": rows[:1], "last": rows[-2:]}


def naver_api_chart():
    end = TODAY.strftime("%Y%m%d") + "2359"
    st = (TODAY - dt.timedelta(days=900)).strftime("%Y%m%d") + "0000"
    s, b, t, ct = http(f"https://api.stock.naver.com/chart/domestic/item/005930/day?startDateTime={st}&endDateTime={end}")
    j = json.loads(b)
    return {"status": s, "sec": t, "n": len(j), "first": j[:1], "last": j[-1:]}


def naver_integration():
    s, b, t, ct = http("https://m.stock.naver.com/api/stock/005930/integration")
    j = json.loads(b)
    infos = {x.get("code"): x.get("value") for x in j.get("totalInfos", [])}
    return {"status": s, "sec": t, "keys": list(j.keys())[:15], "totalInfos": infos}


def naver_foreign():
    s, b, t, ct = http("https://finance.naver.com/item/frgn.naver?code=005930&page=1")
    txt = dec(b)
    pcts = re.findall(r'(\d{1,2}\.\d{2})%', txt)
    return {"status": s, "sec": t, "len": len(txt), "pct_sample": pcts[:6]}


def yahoo_chart():
    s, b, t, ct = http("https://query1.finance.yahoo.com/v8/finance/chart/005930.KS?range=5y&interval=1d")
    r = json.loads(b)["chart"]["result"][0]
    ts, cl = r["timestamp"], r["indicators"]["quote"][0]["close"]
    return {"status": s, "sec": t, "n": len(ts), "last": [ts[-1], cl[-1]],
            "first": [ts[0], cl[0]], "splits": bool(r.get("events"))}


def krx_all_day():
    d = last_trading_day()
    s, b, t, ct = http(
        "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd",
        data={"bld": "dbms/MDC/STAT/standard/MDCSTAT01501", "locale": "ko_KR", "mktId": "ALL",
              "trdDd": d, "share": "1", "money": "1", "csvxls_isNo": "false"},
        headers={"Referer": "https://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020101",
                 "X-Requested-With": "XMLHttpRequest"})
    txt = dec(b)
    try:
        j = json.loads(txt)
        rows = j.get("OutBlock_1", [])
        return {"status": s, "sec": t, "date": d, "n": len(rows), "sample": rows[:1]}
    except ValueError:
        return {"ok": False, "status": s, "sec": t, "date": d, "notjson": txt[:200]}


def krx_per_pbr():
    d = last_trading_day()
    s, b, t, ct = http(
        "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd",
        data={"bld": "dbms/MDC/STAT/standard/MDCSTAT03501", "locale": "ko_KR", "searchType": "1",
              "mktId": "ALL", "trdDd": d, "csvxls_isNo": "false"},
        headers={"Referer": "https://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020502",
                 "X-Requested-With": "XMLHttpRequest"})
    txt = dec(b)
    try:
        rows = json.loads(txt).get("output", [])
        return {"status": s, "sec": t, "date": d, "n": len(rows), "sample": rows[:1]}
    except ValueError:
        return {"ok": False, "status": s, "sec": t, "date": d, "notjson": txt[:200]}


def kind_list():
    s, b, t, ct = http("https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13")
    txt = dec(b)
    rows = re.findall(r"<tr>(.*?)</tr>", txt, re.S)
    return {"status": s, "sec": t, "n_rows": len(rows), "sample": re.sub(r"\s+", " ", rows[1])[:200] if len(rows) > 1 else txt[:200]}


# ---------- 財報（OpenDART） ----------
def dart_corpcode():
    s, b, t, ct = http(f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={KEY}", timeout=60)
    z = zipfile.ZipFile(io.BytesIO(b))
    xml = z.read(z.namelist()[0]).decode("utf-8")
    listed = re.findall(r"<corp_code>(\d+)</corp_code>\s*<corp_name>([^<]*)</corp_name>(?:\s*<corp_eng_name>[^<]*</corp_eng_name>)?\s*<stock_code>(\d{6})</stock_code>", xml)
    sam = [x for x in listed if x[2] in ("005930", "000660", "009150")]
    return {"status": s, "sec": t, "n_listed": len(listed), "sample": sam}


def dart_fs(reprt):
    def f():
        q = urllib.parse.urlencode({"crtfc_key": KEY, "corp_code": "00126380", "bsns_year": "2025",
                                    "reprt_code": reprt, "fs_div": "CFS"})
        s, b, t, ct = http(f"https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json?{q}")
        j = json.loads(b)
        lst = j.get("list", [])
        want = ("ifrs-full_Revenue", "ifrs-full_GrossProfit", "dart_OperatingIncomeLoss",
                "ifrs-full_ProfitLossAttributableToOwnersOfParent", "ifrs-full_BasicEarningsLossPerShare",
                "ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities")
        pick = [{k: x.get(k) for k in ("sj_div", "account_id", "account_nm", "thstrm_nm", "thstrm_amount",
                                       "thstrm_add_amount")} for x in lst if x.get("account_id") in want]
        return {"ok": j.get("status") == "000", "status": s, "dart": j.get("status"), "msg": j.get("message"),
                "sec": t, "n": len(lst), "pick": pick}
    return f


probe("naver_fchart", naver_fchart)
probe("naver_api_chart", naver_api_chart)
probe("naver_integration", naver_integration)
probe("naver_foreign", naver_foreign)
probe("yahoo_chart", yahoo_chart)
probe("krx_all_day", krx_all_day)
probe("krx_per_pbr", krx_per_pbr)
probe("kind_list", kind_list)
if KEY:
    probe("dart_corpcode", dart_corpcode)
    probe("dart_fs_Q3_2025", dart_fs("11014"))
    probe("dart_fs_FY_2025", dart_fs("11011"))
else:
    results["dart"] = {"ok": False, "err": "DART_KEY 未設定，跳過"}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as fp:
    json.dump({"asof": TODAY.strftime("%Y-%m-%d %H:%M KST"), "r": results}, fp, ensure_ascii=False, indent=1, default=str)
print("summary:", {k: v.get("ok") for k, v in results.items()})
