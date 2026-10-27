#!/usr/bin/env python3
"""投信估計持股（張）：MoneyDJ 系統「法人持股明細」頁，併進 itrust/tsh.json（2026-10-27 起）。

交易所不公布投信持股，市面上（XQ、券商看盤軟體）的數字都是估計值：每日投信買賣超累加，
再用投信投顧公會公告的基金季（半年）持股明細校正，所以季末可能跳一下。這裡直接採 MoneyDJ 的估計值，
來源：富邦 e 點通 fubon-ebrokerdj.fbs.com.tw（主），康和 concords.moneydj.com（同系統備援）。
每檔頁面預設列最近 5 個交易日，全部併入；同日以新抓的為準。

用法：
  python itrust/tsh_fetch.py <D> "<代號:L|O[:YYYYMM],…>"   # 由 itrust_kline.yml 在日K之後執行
  python itrust/tsh_fetch.py <D> @kline                     # 代號取 itrust/kline/<D>.json 的 codes（回補用）
輸出 itrust/tsh.json：
  {"asOf": 最新資料日, "updatedAt", "src", "keep",
   "t": {代號: [[YYYYMMDD, 投信估計持股張], …]}（每檔最多 KEEP 筆，由舊到新）,
   "diag": {"codes", "ok", "fail": [...], "host": {主機: 成功檔數}, "lastD": {日期: 檔數}}}
超過 RETAIN 個交易日沒再出現在名單的代號會移除。只用 Python 標準函式庫。
"""
import datetime as dt
import html
import json
import re
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "tsh.json"
HOSTS = ["https://fubon-ebrokerdj.fbs.com.tw", "https://concords.moneydj.com"]
KEEP, RETAIN = 30, 40
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,*/*;q=0.8", "Accept-Language": "zh-TW,zh;q=0.9"}
ROC = re.compile(r"^(\d{3})/(\d{2})/(\d{2})$")
GAP = 0.35                       # 同一主機兩次請求的最小間隔（秒）
_lock = {h: threading.Lock() for h in HOSTS}
_last = {h: 0.0 for h in HOSTS}


def decode(raw):
    for enc in ("cp950", "big5"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", "replace")


def get(host, code):
    with _lock[host]:
        w = GAP - (time.time() - _last[host])
        if w > 0:
            time.sleep(w)
        _last[host] = time.time()
    req = urllib.request.Request(f"{host}/z/zc/zcl/zcl_{code}.djhtm", headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return decode(r.read())


def parse(text):
    """回傳 [[YYYYMMDD, 投信估計持股張], …]（由舊到新）。欄位：日期、外資/投信/自營/合計買賣超、外資/投信/自營/合計估計持股、外資比重、三大法人比重。"""
    out = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S | re.I):
        c = [html.unescape(re.sub(r"<[^>]+>", "", td)).replace("\xa0", " ").strip()
             for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I)]
        if len(c) < 11:
            continue
        m = ROC.match(c[0])
        if not m:
            continue
        s = c[6].replace(",", "")
        if not re.fullmatch(r"-?\d+", s):
            continue
        d = f"{int(m.group(1)) + 1911}{m.group(2)}{m.group(3)}"
        out[d] = int(s)
    return [[d, out[d]] for d in sorted(out)]


def one(code, i):
    order = HOSTS if i % 2 == 0 else HOSTS[::-1]      # 兩台主機輪流分擔
    err = ""
    for host in order:
        for k in range(2):
            try:
                rows = parse(get(host, code))
                if rows:
                    return code, rows, host, ""
                err = f"{host.split('//')[1]} 無資料列"
                break                                   # 有回應但沒資料列（下市、權證等）就不重試同一台
            except Exception as e:  # noqa: BLE001
                err = f"{host.split('//')[1]} {type(e).__name__}: {str(e)[:60]}"
                time.sleep(2 * (k + 1))
    return code, None, None, err


def codes_from(arg, D):
    if arg.startswith("@"):
        k = json.loads((HERE / "kline" / f"{D}.json").read_text(encoding="utf-8"))
        specs = k.get("codes") or []
    else:
        specs = [x for x in arg.split(",") if x.strip()]
    seen, out = set(), []
    for s in specs:
        c = str(s).split(":")[0].strip()
        if re.fullmatch(r"[1-9]\d{3}", c) and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def main():
    D = sys.argv[1]
    codes = codes_from(sys.argv[2], D)
    h = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"asOf": "0", "t": {}}
    T = h.setdefault("t", {})
    t0 = time.time()
    diag = {"D": D, "codes": len(codes), "ok": 0, "fail": [], "host": {}, "lastD": {}}
    with ThreadPoolExecutor(max_workers=4) as ex:
        res = list(ex.map(lambda a: one(*a), [(c, i) for i, c in enumerate(codes)]))
    for code, rows, host, err in res:
        if not rows:
            diag["fail"].append(f"{code} {err}")
            continue
        diag["ok"] += 1
        hk = host.split("//")[1]
        diag["host"][hk] = diag["host"].get(hk, 0) + 1
        diag["lastD"][rows[-1][0]] = diag["lastD"].get(rows[-1][0], 0) + 1
        m = {r[0]: r for r in T.get(code) or []}
        for r in rows:
            m[r[0]] = r
        T[code] = [m[k] for k in sorted(m)][-KEEP:]
    dates = sorted({r[0] for v in T.values() for r in v})
    cutoff = dates[-RETAIN] if len(dates) >= RETAIN else (dates[0] if dates else "0")
    for c in [c for c, v in T.items() if not v or v[-1][0] < cutoff]:
        del T[c]
    h["asOf"] = max([h.get("asOf") or "0"] + [d for d in diag["lastD"]])
    h["updatedAt"] = (dt.datetime.utcnow() + dt.timedelta(hours=8)).strftime("%Y/%m/%d %H:%M")
    h["src"] = ("投信估計持股（張）：MoneyDJ 法人持股明細（富邦 e 點通為主、康和備援），每日投信買賣超累加並以投信投顧公會"
                "基金季（半年）持股明細校正，為估計值；季末可能跳動。交易所不公布投信持股。")
    h["keep"] = KEEP
    diag["sec"] = round(time.time() - t0, 1)
    diag["fail"] = diag["fail"][:50]
    h["diag"] = diag
    OUT.write_text(json.dumps(h, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    print(f"tsh D={D} codes={len(codes)} ok={diag['ok']} fail={len(codes) - diag['ok']} "
          f"lastD={diag['lastD']} host={diag['host']} sec={diag['sec']} total={len(T)} bytes={OUT.stat().st_size}")
    if codes and diag["ok"] < len(codes) * 0.5:
        sys.exit("成功不到一半，請檢查來源")


if __name__ == "__main__":
    main()
