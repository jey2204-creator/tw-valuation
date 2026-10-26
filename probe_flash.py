"""探測 2：觀測站 t05st02 清單 + t05st02_detail（找財報重訊格式）→ data/flash_probe.json（一次性）"""
import json, time, urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
API = "https://mops.twse.com.tw/mops/api/"
out = {"days": {}, "details": []}


def post(ep, body):
    h = {"User-Agent": UA, "Content-Type": "application/json", "Referer": "https://mops.twse.com.tw/mops/",
         "Accept": "application/json"}
    r = urllib.request.Request(API + ep, data=json.dumps(body).encode(), headers=h)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            t = resp.read().decode("utf-8", "replace")
    except Exception as e:
        t = json.dumps({"err": str(e)})
    time.sleep(1.2)
    try:
        return json.loads(t)
    except Exception:
        return {"raw": t[:500]}


for ymd in (("115", "08", "12"), ("115", "07", "16"), ("115", "08", "13")):
    j = post("t05st02", {"year": ymd[0], "month": ymd[1], "day": ymd[2]})
    rows = ((j.get("result") or {}).get("data")) or []
    key = "/".join(ymd)
    out["days"][key] = {"n": len(rows), "resultKeys": list((j.get("result") or {}).keys()),
                        "fin": [[r[1], r[2], r[3], r[4]] for r in rows if "財" in r[4] or "盈餘" in r[4] or "自結" in r[4]][:120]}
    picked = [r for r in rows if ("財務報告" in r[4] or "財務報表" in r[4] or "自結" in r[4])][:6]
    for r in picked:
        d = post(r[5]["apiName"], r[5]["parameters"])
        out["details"].append({"day": key, "row": r[:5], "detail": d})

json.dump(out, open("data/flash_probe.json", "w"), ensure_ascii=False, indent=1)
print({k: v["n"] for k, v in out["days"].items()}, len(out["details"]))
