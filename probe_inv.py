"""探路：觀測站新版 API 個別公司 IFRS 財報（資產負債表／綜合損益表／現金流量表）回傳長什麼樣
只讀，結果寫 data/flash/probe_inv.json（用完即刪）
"""
import json, time, urllib.request, sys
from pathlib import Path

API = "https://mops.twse.com.tw/mops/api/"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
OUT = Path(__file__).resolve().parent / "data" / "flash" / "probe_inv.json"


def post(ep, body):
    r = urllib.request.Request(API + ep, data=json.dumps(body).encode(), headers={
        "User-Agent": UA, "Content-Type": "application/json", "Accept": "application/json",
        "Referer": "https://mops.twse.com.tw/mops/"})
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


codes = sys.argv[1:] or ["2454", "2330"]
res = {}
for c in codes:
    for ep in ("t164sb03", "t164sb04", "t164sb05"):
        for body in ({"companyId": c, "dataType": "2", "season": "3", "year": "115", "subsidiaryCompanyId": ""},):
            time.sleep(2)
            j = post(ep, body)
            s = json.dumps(j, ensure_ascii=False)
            res[f"{c}/{ep}"] = j if len(s) < 60000 else {"truncated": s[:60000]}
            print(c, ep, s[:300])
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
