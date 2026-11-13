"""探測除權息／減資／面額變更端點（一次性）→ data/adj_probe.json"""
import json, urllib.request, urllib.parse, time
UA = {"User-Agent": "Mozilla/5.0 (tw-valuation; GitHub Actions)", "Accept": "application/json,text/plain,*/*"}
S, E = "20260801", "20261113"
sl = lambda d: f"{d[:4]}%2F{d[4:6]}%2F{d[6:]}"
roc = lambda d: urllib.parse.quote(f"{int(d[:4]) - 1911}/{d[4:6]}/{d[6:]}")
URLS = {
 "twse_ex": f"https://www.twse.com.tw/rwd/zh/exRight/TWT49U?startDate={S}&endDate={E}&response=json",
 "twse_red": f"https://www.twse.com.tw/rwd/zh/reducation/TWTAUU?startDate={S}&endDate={E}&response=json",
 "twse_pv": f"https://www.twse.com.tw/rwd/zh/change/TWTB8U?startDate={S}&endDate={E}&response=json",
 "tpex_ex": f"https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ?startDate={sl(S)}&endDate={sl(E)}&response=json",
 "tpex_red": f"https://www.tpex.org.tw/www/zh-tw/bulletin/revivt?startDate={sl(S)}&endDate={sl(E)}&response=json",
 "tpex_pv": f"https://www.tpex.org.tw/www/zh-tw/bulletin/pvChgRslt?startDate={sl(S)}&endDate={sl(E)}&response=json",
 "tpex_ex_old": f"https://www.tpex.org.tw/web/stock/exright/dailyquo/exDailyQ_result.php?l=zh-tw&d={roc(S)}&ed={roc(E)}&o=json",
 "tpex_red_old": f"https://www.tpex.org.tw/web/stock/exright/revivt/revivt_result.php?l=zh-tw&d={roc(S)}&ed={roc(E)}&o=json",
 "tpex_pv_old": f"https://www.tpex.org.tw/web/stock/exright/decap/decap_result.php?l=zh-tw&d={roc(S)}&ed={roc(E)}&o=json",
}
WATCH = {"6108", "2468", "6221", "4747", "6173", "2492", "3026", "2327", "1416"}
out = {}
for k, u in URLS.items():
    r = {"url": u}
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=45) as x:
            raw = x.read().decode("utf-8-sig", "replace")
        r["len"] = len(raw)
        try:
            js = json.loads(raw)
            r["keys"] = list(js.keys()) if isinstance(js, dict) else str(type(js))
            tabs = []
            if isinstance(js, dict):
                for t in (js.get("tables") or []):
                    if isinstance(t, dict):
                        tabs.append((t.get("fields"), t.get("data") or [], {a: b for a, b in t.items() if a not in ("fields", "data")}))
                if isinstance(js.get("data"), list):
                    tabs.append((js.get("fields"), js["data"], {a: (b if not isinstance(b, (list, dict)) else "...") for a, b in js.items() if a not in ("fields", "data")}))
                if js.get("aaData"):
                    tabs.append((None, js["aaData"], {a: (b if not isinstance(b, (list, dict)) else "...") for a, b in js.items() if a != "aaData"}))
            r["tables"] = [{"fields": f, "n": len(d), "meta": m, "head": d[:3],
                            "watch": [row for row in d if any(str(c).strip() in WATCH for c in row[:3])]} for f, d, m in tabs]
            if not tabs:
                r["raw"] = raw[:800]
        except Exception as e:
            r["notjson"] = str(e); r["raw"] = raw[:500]
    except Exception as e:
        r["err"] = str(e)[:200]
    out[k] = r
    time.sleep(3)
open("data/adj_probe.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1)[:6000])
