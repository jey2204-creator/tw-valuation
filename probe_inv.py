"""探路：觀測站個別公司 IFRS 財報（資產負債表／綜合損益表／現金流量表）回傳長什麼樣
只讀，結果寫 data/flash/probe_inv.json（用完即刪）
"""
import json, time, urllib.request, urllib.parse, sys
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
OUT = Path(__file__).resolve().parent / "data" / "flash" / "probe_inv.json"


def post_json(url, body):
    r = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
        "User-Agent": UA, "Content-Type": "application/json", "Accept": "application/json",
        "Referer": "https://mops.twse.com.tw/mops/"})
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return f"ERR {type(e).__name__}: {e}"


def post_form(url, form, referer):
    r = urllib.request.Request(url, data=urllib.parse.urlencode(form).encode(), headers={
        "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", "Referer": referer})
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return f"ERR {type(e).__name__}: {e}"


codes = sys.argv[1:] or ["2454"]
res = {}
for c in codes:
    # 新版 API 幾種參數組合
    for ep in ("t164sb03",):
        for body in (
            {"companyId": c, "dataType": "2", "season": "3", "year": "115", "subsidiaryCompanyId": ""},
            {"companyId": c, "dataType": "2", "season": "2", "year": "115", "subsidiaryCompanyId": ""},
            {"companyId": c, "dataType": "1", "season": "3", "year": "115", "subsidiaryCompanyId": ""},
            {"companyId": c, "dataType": "2", "season": "03", "year": "115", "subsidiaryCompanyId": ""},
            {"companyId": c, "dataType": "2", "season": "3", "year": "2026", "subsidiaryCompanyId": ""},
            {"companyId": c, "year": "115", "season": "3"},
        ):
            time.sleep(2)
            s = post_json("https://mops.twse.com.tw/mops/api/" + ep, body)
            key = f"{c}/api/{ep}/{json.dumps(body, ensure_ascii=False)}"
            res[key] = s[:30000]
            print(key, s[:200])
    # 舊版 ajax（兩個主機）
    for h in ("https://mopsov.twse.com.tw", "https://mops.twse.com.tw"):
        for ep in ("ajax_t164sb03", "ajax_t164sb04", "ajax_t164sb05"):
            form = {"encodeURIComponent": "1", "step": "1", "firstin": "1", "off": "1", "queryName": "co_id",
                    "inpuType": "co_id", "TYPEK": "all", "isnew": "false", "co_id": c, "year": "115", "season": "3"}
            time.sleep(4)
            s = post_form(f"{h}/mops/web/{ep}", form, f"{h}/mops/web/{ep.replace('ajax_', '')}")
            key = f"{c}/{h}/{ep}"
            res[key] = s[:60000]
            print(key, len(s), s[:200].replace("\n", " "))
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
