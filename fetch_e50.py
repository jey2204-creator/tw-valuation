"""0050（元大台灣50）成份股 → data/e50.json（2026-11-20）

首頁產業主題表的自動主題「🏛️ 0050成份股」與掃描頁同名名單用；世杰選：排第 1 位、依市值排序、只做 0050。
成份股一季才換一次（3／6／9／12 月），但每個交易日跟在「更新股票資料」後面抓一次（1～3 次請求），換股當週就會跟上。

來源（依序試，第一個通過檢查的就採用）：
  1 元大投信官網 API   www.yuantaetfs.com/api/StkWeights?date=&fundid=1066
  2 MoneyDJ 全部持股   www.moneydj.com/ETF/X/Basic/Basic0007B.xdjhtm?etfid=0050.TW
  3 元大投信 PCF 頁    www.yuantaetfs.com/tradeInfo/pcf/0050（網頁內嵌資料）
檢查：45～55 檔、都是 data/list.json 裡的上市櫃普通股、含 2330、權重合計 90～101%。不通過就不覆蓋舊檔。

輸出 data/e50.json：
  {asof:"YYYYMMDD"（持股資料日；來源沒給就用抓取日）, src, updated, n,
   stocks:[[代號, 權重%]…]（依市值＝收盤×已發行普通股數 由大到小；summary.json 沒有的用權重補排在後）,
   chg:{d:"YYYYMMDD", in:[代號…], out:[代號…]}（最近一次名單變動；沒變動過就沒有）}
每次執行的診斷寫在 data/e50_diag.json（各來源的狀態碼、長度、抓到幾檔、失敗原因）。
用法：python fetch_e50.py
"""
import json, re, sys, time, datetime as dt, urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent / "data"
F = OUT / "e50.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json, text/html, */*", "Accept-Language": "zh-TW,zh;q=0.9"}
diag = []


def get(url, referer=None):
    h = dict(UA)
    if referer:
        h["Referer"] = referer
    last = ""
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=40) as r:
                raw = r.read()
                return r.status, raw.decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
            time.sleep(3 * (i + 1))
    return 0, last


def num(x):
    try:
        return float(str(x).replace(",", "").replace("%", "").strip())
    except Exception:
        return None


def ymd(x):
    m = re.search(r"(20\d\d)\D?(\d\d)\D?(\d\d)", str(x or ""))
    return "".join(m.groups()) if m else None


def src_yuanta_api():
    st, tx = get("https://www.yuantaetfs.com/api/StkWeights?date=&fundid=1066", "https://www.yuantaetfs.com/product/detail/0050/ratio")
    d = {"src": "yuanta_api", "status": st, "len": len(tx), "head": tx[:200]}
    diag.append(d)
    rows, asof = [], None
    try:
        j = json.loads(tx)
        if isinstance(j, dict):
            asof = ymd(j.get("date") or j.get("Date") or j.get("tradeDate"))
            j = next((v for v in j.values() if isinstance(v, list) and v and isinstance(v[0], dict)), [])
        d["keys"] = sorted(j[0].keys()) if j else []
        for r in j:
            lk = {k.lower(): v for k, v in r.items()}
            c = str(lk.get("code") or lk.get("stkcd") or lk.get("stockcode") or lk.get("stock_id") or "").strip()
            w = num(lk.get("weights") if lk.get("weights") is not None else lk.get("weight") if lk.get("weight") is not None else lk.get("ratio"))
            if re.fullmatch(r"\d{4}", c) and w is not None:
                rows.append([c, w])
            asof = asof or ymd(lk.get("date") or lk.get("ymd") or lk.get("tradedate"))
    except Exception as e:  # noqa: BLE001
        d["err"] = f"{type(e).__name__}: {e}"
    return rows, asof


def src_moneydj():
    st, tx = get("https://www.moneydj.com/ETF/X/Basic/Basic0007B.xdjhtm?etfid=0050.TW", "https://www.moneydj.com/")
    d = {"src": "moneydj", "status": st, "len": len(tx), "head": re.sub(r"\s+", " ", tx[:200])}
    diag.append(d)
    rows, seen = [], set()
    for m in re.finditer(r"\((\d{4})\.TW\)\s*</a>\s*</td>\s*<td[^>]*>\s*([\d.,]+)\s*</td>", tx):
        if m.group(1) not in seen:
            seen.add(m.group(1))
            rows.append([m.group(1), num(m.group(2))])
    m = re.search(r"資料日期[^0-9]{0,20}(20\d\d[/-]\d\d[/-]\d\d)", tx)
    return rows, ymd(m.group(1)) if m else None


def src_yuanta_pcf():
    st, tx = get("https://www.yuantaetfs.com/tradeInfo/pcf/0050", "https://www.yuantaetfs.com/")
    d = {"src": "yuanta_pcf", "status": st, "len": len(tx), "head": re.sub(r"\s+", " ", tx[:200])}
    diag.append(d)
    rows, seen = [], set()
    # 內嵌資料：{…code:"2330",…weights:58.9…}（欄位順序不定，抓同一個物件裡的代號與權重）
    for m in re.finditer(r"\{[^{}]{0,400}\}", tx):
        o = m.group(0)
        c = re.search(r"(?:code|stkCd|stkcd)\W{1,3}(\d{4})\b", o)
        w = re.search(r"(?:weights?|ratio)\W{1,3}([\d.]+)", o)
        if c and w and c.group(1) not in seen:
            seen.add(c.group(1))
            rows.append([c.group(1), num(w.group(1))])
    return rows, None


def check(rows, common):
    if not (45 <= len(rows) <= 55):
        return f"檔數 {len(rows)}"
    bad = [c for c, _ in rows if c not in common]
    if bad:
        return f"不在 list.json：{bad[:5]}"
    if "2330" not in {c for c, _ in rows}:
        return "沒有 2330"
    tot = sum(w or 0 for _, w in rows)
    if not (90 <= tot <= 101):
        return f"權重合計 {tot:.1f}"
    return ""


def main():
    common = {r[0] for r in json.loads((OUT / "list.json").read_text("utf-8")) if re.fullmatch(r"[1-9]\d{3}", str(r[0]))}
    old = {}
    try:
        old = json.loads(F.read_text("utf-8"))
    except Exception:
        pass
    got = None
    for fn in (src_yuanta_api, src_moneydj, src_yuanta_pcf):
        rows, asof = fn()
        why = check(rows, common)
        diag[-1].update(n=len(rows), ok=not why, why=why, asof=asof)
        if not why:
            got = (diag[-1]["src"], rows, asof)
            break
    now = dt.datetime.utcnow() + dt.timedelta(hours=8)
    (OUT / "e50_diag.json").write_text(json.dumps({"at": now.strftime("%Y-%m-%d %H:%M"), "ok": bool(got), "tries": diag}, ensure_ascii=False, indent=1), "utf-8")
    if not got:
        print("全部來源都失敗，保留舊檔", json.dumps(diag, ensure_ascii=False)[:1500])
        return 0
    src, rows, asof = got
    # 依市值排序（收盤 × 已發行普通股數）；沒有市值的依權重排在後面
    cap = {}
    try:
        S = json.loads((OUT / "summary.json").read_text("utf-8"))
        for c, _ in rows:
            px, sh = (S["d"].get(c) or [None])[0], (S.get("sh") or {}).get(c)
            if px and sh:
                cap[c] = px * sh
    except Exception as e:  # noqa: BLE001
        print("summary.json 讀不到，改依權重排序", e)
    rows.sort(key=lambda r: (-(cap.get(r[0]) or 0), -(r[1] or 0)))
    out = {"asof": asof or now.strftime("%Y%m%d"), "src": src, "updated": now.strftime("%Y-%m-%d %H:%M"), "n": len(rows),
           "stocks": [[c, round(w, 2)] for c, w in rows]}
    o_ids, n_ids = [c for c, _ in old.get("stocks") or []], [c for c, _ in rows]
    if o_ids and set(o_ids) != set(n_ids):
        out["chg"] = {"d": out["asof"], "in": [c for c in n_ids if c not in o_ids], "out": [c for c in o_ids if c not in n_ids]}
    elif old.get("chg"):
        out["chg"] = old["chg"]
    F.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"ok {src} {len(rows)} 檔 asof={out['asof']} 無市值 {len(rows) - len(cap)} 檔", out.get("chg") or "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
