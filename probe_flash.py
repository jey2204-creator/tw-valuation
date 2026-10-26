"""探測：哪個重大訊息來源最快、內文有沒有財報數字 → data/flash_probe.json（一次性，確認後刪除）"""
import json, re, time, datetime as dt, urllib.request, urllib.parse, sys

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
NOW = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
D = NOW.date()
ROC = D.year - 1911
out = {"at": NOW.isoformat(timespec="seconds"), "tries": []}


def get(url, data=None, js=False, ref=None):
    h = {"User-Agent": UA, "Accept": "application/json, text/html, */*", "Accept-Language": "zh-TW,zh;q=0.9",
         "Referer": ref or url}
    body = None
    if data is not None:
        if js:
            body = json.dumps(data).encode(); h["Content-Type"] = "application/json"
        else:
            body = urllib.parse.urlencode(data).encode(); h["Content-Type"] = "application/x-www-form-urlencoded"
    t0 = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=h), timeout=90) as r:
            raw, st = r.read(), r.status
    except urllib.error.HTTPError as e:
        raw, st = e.read(), e.code
    except Exception as e:
        raw, st = b"", f"ERR {e}"
    for enc in ("utf-8", "cp950"):
        try:
            txt = raw.decode(enc); break
        except Exception:
            txt = raw.decode("utf-8", "replace")
    rec = {"url": url, "data": data, "status": st, "len": len(txt), "sec": round(time.time() - t0, 1)}
    out["tries"].append(rec)
    time.sleep(2)
    return rec, txt


def fin(s):
    return any(k in s for k in ("財務報告", "財務報表", "自結", "每股盈餘", "財報"))


# 1) OpenAPI 上市／上櫃每日重大訊息
for name, url in (("L", "https://openapi.twse.com.tw/v1/opendata/t187ap04_L"),
                  ("O", "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap04_O")):
    rec, txt = get(url)
    try:
        j = json.loads(txt)
        rec["n"] = len(j)
        rec["keys"] = list(j[0].keys()) if j else []
        rec["dates"] = sorted({str(next(iter(x.values()))) for x in j})[:5]
        rec["first"] = j[0] if j else None
        f = [x for x in j if fin(json.dumps(x, ensure_ascii=False))]
        rec["nFin"] = len(f)
        rec["finSamples"] = f[:4]
    except Exception as e:
        rec["parseErr"] = str(e); rec["head"] = txt[:600]

# 2) 新版觀測站 JSON API（猜幾個端點）
for ep, body in (("t05sr01_1", {}), ("t05sr01_1", {"marketKind": "all"}),
                 ("t05st02", {"year": str(ROC), "month": f"{D.month:02d}", "day": f"{D.day:02d}"}),
                 ("t05st02", {"year": str(ROC), "month": str(D.month), "day": str(D.day), "marketKind": "all"})):
    rec, txt = get(f"https://mops.twse.com.tw/mops/api/{ep}", body, js=True, ref="https://mops.twse.com.tw/mops/")
    rec["head"] = txt[:2500]

# 3) 舊版 mopsov ajax（HTML）
for ep, form in (("ajax_t05sr01_1", {"encodeURIComponent": 1, "step": 0, "TYPEK": "all"}),
                 ("ajax_t05st02", {"encodeURIComponent": 1, "step": 1, "firstin": 1, "off": 1, "TYPEK": "all",
                                   "year": str(ROC), "month": f"{D.month:02d}", "day": f"{D.day:02d}"})):
    for host in ("https://mopsov.twse.com.tw", "https://mops.twse.com.tw"):
        rec, txt = get(f"{host}/mops/web/{ep}", form, ref=f"{host}/mops/web/{ep[5:]}")
        plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", txt))
        rec["plain"] = plain[:1500]
        i = txt.find("每股盈餘")
        rec["epsCtx"] = txt[max(0, i - 3000): i + 1500] if i >= 0 else None
        rec["nFinWord"] = txt.count("財務報告") + txt.count("自結")
        rec["inputs"] = re.findall(r"<input[^>]{0,300}>", txt)[:12]

json.dump(out, open("data/flash_probe.json", "w"), ensure_ascii=False, indent=1)
print("ok", len(out["tries"]))
