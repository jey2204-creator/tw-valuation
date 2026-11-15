import json, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (tw-valuation; GitHub Actions)", "Accept": "application/json,text/plain,*/*"}
out = {}
for k, u in {"openapi": "https://openapi.twse.com.tw/v1/holidaySchedule/holidaySchedule",
             "rwd": "https://www.twse.com.tw/rwd/zh/holidaySchedule/holidaySchedule?response=json",
             "rwd2027": "https://www.twse.com.tw/rwd/zh/holidaySchedule/holidaySchedule?response=json&queryYear=116"}.items():
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r:
            out[k] = json.loads(r.read().decode("utf-8-sig"))
    except Exception as e:
        out[k] = {"err": str(e)[:200]}
open("data/hol_probe.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
