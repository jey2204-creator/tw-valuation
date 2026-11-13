"""除權息／減資／面額變更的還原係數 → data/adj.json（2026-11-13）
用途：週／月／季漲幅改用「還原價」算，跟 XQ 一致（例：競國 10/7 除息 1 元、信昌電 10/19 現金減資、強生 8/31 面額 10→5 元）。

來源（證交所／櫃買官網，可指定起迄日）：
  上市 除權息計算結果表      www.twse.com.tw/rwd/zh/exRight/TWT49U
  上市 減資恢復買賣參考價    www.twse.com.tw/rwd/zh/reducation/TWTAUU
  上市 變更面額恢復買賣參考價 www.twse.com.tw/rwd/zh/change/TWTB8U
  上櫃 除權息               www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ
  上櫃 減資                 www.tpex.org.tw/www/zh-tw/bulletin/revivt
  上櫃 變更面額             www.tpex.org.tw/www/zh-tw/bulletin/pvChgRslt

輸出 {"updated","from","to","ev":{代號:[[YYYYMMDD, 係數, 類別]]},"errors":[]}
  係數 = 參考價 ÷ 前一交易日收盤；事件日「之前」的價格都乘上它就是還原價（多個事件連乘）
  類別 x=除權息、r=減資、p=面額變更
每次重抓最近 100 天併入舊檔（第一次 230 天），保留 260 天。某個來源失敗就沿用舊資料、不中斷。
用法：python fetch_adj.py
"""
import json, time, datetime as dt, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "adj.json"
UA = {"User-Agent": "Mozilla/5.0 (tw-valuation; GitHub Actions)", "Accept": "application/json,text/plain,*/*"}
KEEP, FIRST, EACH, CHUNK = 260, 230, 100, 100


def get(url):
    for i in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
                return json.loads(r.read().decode("utf-8-sig"))
        except Exception as e:
            if i == 1:
                raise RuntimeError(str(e)[:100])
            time.sleep(5)


def num(v):
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return None


def ymd(v):
    """'115年08月03日'／'115/08/03'／'1150825'／'20260803' → 'YYYYMMDD'"""
    dg = "".join(ch for ch in str(v) if ch.isdigit())
    if len(dg) == 7:
        dg = str(int(dg[:3]) + 1911) + dg[3:]
    return dg if len(dg) == 8 else None


def tables_of(js):
    out = []
    if isinstance(js, dict):
        for t in js.get("tables") or []:
            if isinstance(t, dict) and t.get("data"):
                out.append((t.get("fields") or [], t["data"]))
        if isinstance(js.get("data"), list) and js["data"]:
            out.append((js.get("fields") or [], js["data"]))
    return out


def parse(js, typ):
    ev = []
    for fields, rows in tables_of(js):
        fs = [str(f) for f in fields]
        first = lambda *keys: next((i for i, f in enumerate(fs) if any(k in f for k in keys)), None)
        idt, ic, ip, ir = first("日期"), first("代號"), first("收盤價"), first("參考價")
        if None in (idt, ic, ip, ir):
            continue
        for r in rows:
            c, d, p, ref = str(r[ic]).strip(), ymd(r[idt]), num(r[ip]), num(r[ir])
            if not (len(c) == 4 and c.isdigit() and c[0] != "0") or not d or not p or not ref or p <= 0 or ref <= 0:
                continue
            f = ref / p
            if 0.02 < f < 50 and abs(f - 1) > 1e-6:
                ev.append((c, d, round(f, 6), typ))
    return ev


def main():
    old = {}
    try:
        old = json.loads(OUT.read_text("utf-8"))
    except Exception:
        pass
    today = (dt.datetime.utcnow() + dt.timedelta(hours=8)).date()
    start = today - dt.timedelta(days=EACH if old.get("ev") else FIRST)
    cut = (today - dt.timedelta(days=KEEP)).strftime("%Y%m%d")
    got, errs, n = {}, [], 0
    a = start
    while a <= today:
        b = min(today, a + dt.timedelta(days=CHUNK - 1))
        s, e = f"{a:%Y%m%d}", f"{b:%Y%m%d}"
        sl = lambda d: f"{d:%Y}%2F{d:%m}%2F{d:%d}"
        for name, typ, host, url in (
            ("上市除權息", "x", "twse", f"https://www.twse.com.tw/rwd/zh/exRight/TWT49U?startDate={s}&endDate={e}&response=json"),
            ("上市減資", "r", "twse", f"https://www.twse.com.tw/rwd/zh/reducation/TWTAUU?startDate={s}&endDate={e}&response=json"),
            ("上市面額", "p", "twse", f"https://www.twse.com.tw/rwd/zh/change/TWTB8U?startDate={s}&endDate={e}&response=json"),
            ("上櫃除權息", "x", "tpex", f"https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ?startDate={sl(a)}&endDate={sl(b)}&response=json"),
            ("上櫃減資", "r", "tpex", f"https://www.tpex.org.tw/www/zh-tw/bulletin/revivt?startDate={sl(a)}&endDate={sl(b)}&response=json"),
            ("上櫃面額", "p", "tpex", f"https://www.tpex.org.tw/www/zh-tw/bulletin/pvChgRslt?startDate={sl(a)}&endDate={sl(b)}&response=json"),
        ):
            try:
                for c, d, f, t in parse(get(url), typ):
                    if s <= d <= e:
                        got[(c, d, t)] = f
                        n += 1
            except Exception as ex:
                errs.append(f"{name} {s}~{e}: {ex}")
            time.sleep(3.5 if host == "twse" else 2)
        a = b + dt.timedelta(days=1)
    # 併入舊檔：這次有抓到的區間以新的為準（失敗的來源沿用舊的）
    merged = {}
    for c, lst in (old.get("ev") or {}).items():
        for d, f, t in lst:
            merged[(c, d, t)] = f
    merged.update(got)
    ev = {}
    for (c, d, t), f in sorted(merged.items()):
        if d >= cut:
            ev.setdefault(c, []).append([d, f, t])
    if not ev:
        print("fetch_adj: 沒有任何資料，不輸出", errs)
        return
    res = {"updated": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"), "from": cut, "to": f"{today:%Y%m%d}", "errors": errs[:20], "ev": ev}
    OUT.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"adj.json: {len(ev)} 檔、{sum(len(v) for v in ev.values())} 筆事件（這次抓到 {n} 筆），錯誤 {len(errs)}", errs[:5])


if __name__ == "__main__":
    main()
