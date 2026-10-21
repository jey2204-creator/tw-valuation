#!/usr/bin/env python3
"""連通性探測：從 GitHub Actions 機器打一遍「投信＋外資 每日更新」主排程會用到的每個端點。
只讀不寫，結果印成 Markdown 表（寫進 job summary），不 commit 任何檔案。
用法：python itrust/probe_endpoints.py YYYYMMDD
"""
import json, sys, time, urllib.request, urllib.parse, datetime

D = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().strftime("%Y%m%d")
SL = f"{D[:4]}/{D[4:6]}/{D[6:]}"
ROC = f"{int(D[:4])-1911}/{D[4:6]}/{D[6:]}"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*"}
rows = []


def hit(name, url, method="GET", body=None, headers=None, referer=None, check=None, wait=1.3):
    h = dict(UA)
    if referer:
        h["Referer"] = referer
    if headers:
        h.update(headers)
    data = None
    if body is not None:
        data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
    t0 = time.time()
    try:
        req = urllib.request.Request(url, data=data, method=method, headers=h)
        with urllib.request.urlopen(req, timeout=40) as r:
            code = r.status
            raw = r.read()
        ms = int((time.time() - t0) * 1000)
        try:
            j = json.loads(raw.decode("utf-8", "replace"))
            note = check(j) if check else f"json {len(raw)}B"
        except Exception:
            head = raw[:80].decode("utf-8", "replace").replace("\n", " ")
            note = f"非JSON {len(raw)}B: {head}"
        rows.append((name, code, ms, note))
    except urllib.error.HTTPError as e:
        rows.append((name, e.code, int((time.time() - t0) * 1000), f"HTTP {e.code} {e.reason}"))
    except Exception as e:
        rows.append((name, "ERR", int((time.time() - t0) * 1000), str(e)[:120]))
    time.sleep(wait)


def twse_stat(j):
    n = len(j.get("data") or [])
    return f"stat={j.get('stat')} date={j.get('date')} rows={n}"


def tpex_tables(j):
    t = (j.get("tables") or [{}])[0]
    return f"date={j.get('date') or t.get('date')} rows={len(t.get('data') or [])} total={t.get('totalCount')}"


TW = "https://www.twse.com.tw"
TP = "https://www.tpex.org.tw"
first = D[:6] + "01"
d45 = (datetime.datetime.strptime(D, "%Y%m%d") - datetime.timedelta(days=45)).strftime("%Y%m%d")
sl45 = f"{d45[:4]}/{d45[4:6]}/{d45[6:]}"

# ── 證交所（主排程步驟 1～3、13）
hit("TWSE T86 三大法人", f"{TW}/rwd/zh/fund/T86?date={D}&selectType=ALLBUT0999&response=json", referer=f"{TW}/zh/trading/foreign/t86.html", check=twse_stat)
hit("TWSE FMTQIK 交易日", f"{TW}/rwd/zh/afterTrading/FMTQIK?date={first}&response=json", referer=f"{TW}/zh/", check=twse_stat)
hit("TWSE MI_QFIIS 掛牌股數", f"{TW}/rwd/zh/fund/MI_QFIIS?date={D}&selectType=ALLBUT0999&response=json", referer=f"{TW}/zh/", check=twse_stat)
hit("TWSE MI_INDEX 收盤", f"{TW}/rwd/zh/afterTrading/MI_INDEX?date={D}&type=ALLBUT0999&response=json", referer=f"{TW}/zh/", check=lambda j: f"stat={j.get('stat')} tables={len(j.get('tables') or [])}")
hit("TWSE punish 處置", f"{TW}/rwd/zh/announcement/punish?startDate={d45}&endDate={D}&response=json", referer=f"{TW}/zh/", check=twse_stat)
hit("TWSE TWT49U 除權息", f"{TW}/rwd/zh/exRight/TWT49U?startDate={d45}&endDate={D}&response=json", referer=f"{TW}/zh/", check=twse_stat)
# 連打 5 次 MI_INDEX 測限速（主排程要打 40 天）
for i in range(5):
    hit(f"TWSE MI_INDEX 連打#{i+1}", f"{TW}/rwd/zh/afterTrading/MI_INDEX?date={D}&type=ALLBUT0999&response=json", referer=f"{TW}/zh/", check=lambda j: f"stat={j.get('stat')}")

# ── 證交所 openapi（步驟 4）
hit("openapi t187ap03_L 股數", "https://openapi.twse.com.tw/v1/opendata/t187ap03_L", check=lambda j: f"rows={len(j)}")
hit("openapi TWT85U 全額交割", "https://openapi.twse.com.tw/v1/exchangeReport/TWT85U", check=lambda j: f"rows={len(j)}")

# ── 櫃買（步驟 5）
FORM = {"Content-Type": "application/x-www-form-urlencoded"}
hit("TPEx dailyTrade 法人", f"{TP}/www/zh-tw/insti/dailyTrade", "POST", f"type=Daily&sect=EW&date={urllib.parse.quote(SL)}&response=json", FORM, referer=f"{TP}/zh-tw/", check=tpex_tables)
hit("TPEx otc 收盤", f"{TP}/www/zh-tw/afterTrading/otc", "POST", f"date={SL}&type=EW&response=json", FORM, referer=f"{TP}/zh-tw/", check=tpex_tables)
hit("TPEx qfii 外資持股", f"{TP}/www/zh-tw/insti/qfii", "POST", f"date={urllib.parse.quote(SL)}&response=json", FORM, referer=f"{TP}/zh-tw/", check=tpex_tables)
hit("TPEx disposal 處置", f"{TP}/www/zh-tw/bulletin/disposal", "POST", f"startDate={sl45}&endDate={SL}&response=json", FORM, referer=f"{TP}/zh-tw/", check=tpex_tables)
hit("TPEx exDailyQ 除權息", f"{TP}/www/zh-tw/bulletin/exDailyQ", "POST", f"startDate={urllib.parse.quote(sl45)}&endDate={urllib.parse.quote(SL)}&response=json", FORM, referer=f"{TP}/zh-tw/", check=tpex_tables)
hit("TPEx openapi mopsfin_t187ap03_O", f"{TP}/openapi/v1/mopsfin_t187ap03_O", check=lambda j: f"rows={len(j)}")
hit("TPEx openapi tpex_cmode", f"{TP}/openapi/v1/tpex_cmode", check=lambda j: f"rows={len(j)}")

# ── 公開資訊觀測站（步驟 7，最可能被擋）
hit("MOPS t05st03 公司基本資料(2330)", "https://mops.twse.com.tw/mops/api/t05st03", "POST", {"companyId": "2330"},
    {"Content-Type": "application/json"}, referer="https://mops.twse.com.tw/mops/", check=lambda j: f"code={j.get('code')} sm={(j.get('result') or {}).get('commonStockAmount')} cb={((j.get('result') or {}).get('haveCompanyBonds') or {}).get('value')}")
hit("MOPS t05st03 (6510)", "https://mops.twse.com.tw/mops/api/t05st03", "POST", {"companyId": "6510"},
    {"Content-Type": "application/json"}, referer="https://mops.twse.com.tw/mops/", check=lambda j: f"code={j.get('code')} sm={(j.get('result') or {}).get('commonStockAmount')}")

# ── 輸出
ok = sum(1 for r in rows if r[1] == 200 and not str(r[3]).startswith(("非JSON", "HTTP")))
out = [f"## 連通性探測 {D}（GitHub Actions → 台灣各資料源）", "", f"通過 {ok}/{len(rows)}", "",
       "| 端點 | HTTP | 毫秒 | 內容 |", "|---|---|---|---|"]
for n, c, ms, note in rows:
    mark = "✅" if c == 200 and not str(note).startswith(("非JSON", "HTTP")) else "❌"
    out.append(f"| {mark} {n} | {c} | {ms} | {str(note).replace('|', '/')} |")
md = "\n".join(out)
print(md)
import os
if os.environ.get("GITHUB_STEP_SUMMARY"):
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
        f.write(md + "\n")
