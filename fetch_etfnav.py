"""ETF 淨值與折溢價 → data/etfnav.json（2026-11-22，📦 ETF 主題「折溢價」用）

來源：證交所「ETF 盤中預估淨值」彙總 mis.twse.com.tw/stock/data/all_etf.txt（各投信每檔 ETF 的市價、預估淨值、折溢價、前一營業日淨值）。
收盤後抓＝以收盤價算的折溢價。各欄位意義以 diag 第一筆原始資料比對（a 代號、b 名稱、c 發行單位數、d 單位數變動、e 成交價、f 預估淨值、g 預估折溢價%、h 前一營業日淨值、i 日期、j 時間…，依官網頁面 JS）。
輸出 {"updated","asof","n","d":{代號:[市價, 預估淨值, 折溢價%, 前日淨值, "YYYYMMDD HH:MM:SS", 發行單位數, 規模億元]},"keys","diag"}
抓不到時保留舊檔。歷史：data/etfnav_hist.json＝{代號:[[日期, 折溢價%]…]}（每天收盤後一筆，留 60 筆）。
用法：python fetch_etfnav.py
"""
import json, time, datetime as dt, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "etfnav.json"
HIST = ROOT / "data" / "etfnav_hist.json"
UA = {"User-Agent": "Mozilla/5.0 (tw-valuation; GitHub Actions)", "Accept": "application/json,text/plain,*/*",
      "Referer": "https://mis.twse.com.tw/stock/etf_nav.jsp?ex=tse&lang=zh_tw"}
URL = "https://mis.twse.com.tw/stock/data/all_etf.txt"
DIAG = []


def num(v):
    try:
        x = float(str(v).replace(",", "").replace("%", "").strip())
        return x
    except ValueError:
        return None


def main():
    js = None
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{URL}?{int(time.time() * 1000)}", headers=UA), timeout=40) as r:
                raw = r.read().decode("utf-8-sig")
            js = json.loads(raw)
            break
        except Exception as e:
            DIAG.append(f"第 {i + 1} 次失敗 {str(e)[:100]}")
            time.sleep(5)
    rows = []
    if js:
        for blk in js.get("a1") or []:
            rows += blk.get("msgArray") or []
        DIAG.append(f"a1 區塊 {len(js.get('a1') or [])}、共 {len(rows)} 筆；頂層 keys {list(js.keys())[:8]}")
        if rows:
            DIAG.append("第一筆原始：" + json.dumps(rows[0], ensure_ascii=False)[:400])
            z = next((r for r in rows if r.get("a") == "0050"), None)
            if z:
                DIAG.append("0050 原始：" + json.dumps(z, ensure_ascii=False)[:400])
    d = {}
    for r in rows:
        c = str(r.get("a", "")).strip()
        if not c.startswith("00"):
            continue
        px, nav, prem, prev = num(r.get("e")), num(r.get("f")), num(r.get("g")), num(r.get("h"))
        if nav and nav > 0 and px and px > 0:
            prem2 = round((px / nav - 1) * 100, 2)
            un = num(r.get("c"))                 # 2026-11-22：發行單位數 → 規模＝單位數 × 淨值（📦 ETF 規模自動更新）
            d[c] = [px, nav, prem if prem is not None else prem2, prev, f"{r.get('i', '')} {r.get('j', '')}".strip(),
                    int(un) if un and un > 0 else None, round(un * nav / 1e8, 2) if un and un > 0 else None]
    now = dt.datetime.utcnow() + dt.timedelta(hours=8)
    if not d:
        print("fetch_etfnav: 沒有資料，保留舊檔", DIAG)
        try:
            old = json.loads(OUT.read_text("utf-8"))
        except Exception:
            old = {}
        old["diag"] = DIAG[:20]
        old["tried"] = f"{now:%Y-%m-%d %H:%M}"
        OUT.write_text(json.dumps(old, ensure_ascii=False, separators=(",", ":")), "utf-8")
        return
    days = sorted({v[4][:8] for v in d.values() if v[4][:8].isdigit()})
    asof = days[-1] if days else f"{now:%Y%m%d}"
    OUT.write_text(json.dumps({"updated": f"{now:%Y-%m-%d %H:%M}", "asof": asof, "n": len(d), "d": d,
                               "keys": "[市價, 預估淨值, 折溢價%, 前日淨值, 時間, 發行單位數, 規模億]", "diag": DIAG[:20]},
                              ensure_ascii=False, separators=(",", ":")), "utf-8")
    # 收盤後（13:35 以後）才記歷史，同一天覆蓋
    if now.hour * 60 + now.minute >= 13 * 60 + 35 or now.weekday() >= 5:
        try:
            h = json.loads(HIST.read_text("utf-8"))
        except Exception:
            h = {}
        for c, v in d.items():
            if v[4][:8] != asof or v[2] is None:
                continue
            L = [x for x in h.get(c, []) if x[0] != asof] + [[asof, v[2]]]
            h[c] = sorted(L)[-60:]
        HIST.write_text(json.dumps(h, ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"etfnav.json: {len(d)} 檔，資料日 {asof}")
    for x in DIAG:
        print("  ", x)


if __name__ == "__main__":
    main()
