#!/usr/bin/env python3
"""2026-11-17 掃描頁「🌏 海外龍頭」小卡的日 K（data/ovs.json）

名單＝data/themes.json 各主題的 us／jp／kr／cn 欄位（對應美股、日股、韓股、陸股），不另外維護。
（2026-11-17 晚加美股：us 欄位是代號清單，中文名取自 us/data/index.json 的 cn，沒有就只顯示代號）
來源＝Yahoo v8 chart（美股直接用代號；{代號}.T；韓股先試 .KS 再試 .KQ）——公開報價，跟 J-Quants 無關，所以不用加密。
價位：Yahoo 已做分割調整、未做除息調整（跟 jp/fetch_jp.py 同一基準）。

輸出：{"updated": "YYYY-MM-DD HH:MM"(台北), "s": {"jp6981": {"c": "6981", "m": "jp", "n": "村田",
        "sym": "6981.T", "b": [[YYYYMMDD, 開, 高, 低, 收, 量(股), MA240|null], …最近 130 根]}}, "err": […]}
抓不到的代號沿用上一次的資料（不會因為 Yahoo 一次失敗就讓小卡消失）。
這個雲端開發環境連不到 Yahoo，只能在 GitHub Actions 上跑。
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
OUT = "data/ovs.json"
DBG = {}
DBGK = ("6981.T", "005930.KS", "688825.SS", "MU")
KEEP = 130          # 跟台股分片一樣留 130 根（放大卡最多看 6 個月）
SFX = {"us": [""], "jp": [".T"], "kr": [".KS", ".KQ"], "cn": [".SS", ".SZ"]}


def http(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (400, 401, 403, 404):
                break
        except Exception as e:  # noqa
            last = f"{type(e).__name__}: {e}"
        time.sleep(3 * (i + 1))
    raise RuntimeError(last)


def rd(x):
    x = round(x, 1) if x >= 100 else round(x, 2)
    return int(x) if x == int(x) else x


def bars(sym, oldb=None):
    j = http(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=2y&interval=1d")
    r = (j.get("chart", {}).get("result") or [None])[0]
    if not r or not r.get("timestamp"):
        raise RuntimeError("no data")
    q = r["indicators"]["quote"][0]
    n = len(r["timestamp"])
    col = lambda k: (q.get(k) or []) + [None] * n
    by = {}
    # 日期用交易所當地時間（meta.gmtoffset；東京、首爾 +9，紐約 −5／−4）；同一天重複（盤中＋收盤各一筆）取後面那筆
    off = (r.get("meta") or {}).get("gmtoffset")
    off = 32400 if off is None else off
    for t, o, h, l, c, v in zip(r["timestamp"], col("open"), col("high"), col("low"), col("close"), col("volume")):
        if not c:
            continue
        d = (dt.datetime.utcfromtimestamp(t) + dt.timedelta(seconds=off)).strftime("%Y%m%d")
        if not (o and h and l):      # 開高低任一缺就只留收盤，避免畫出假影線
            o = h = l = c
        by[d] = [d, rd(o), rd(max(h, o, c)), rd(min(l, o, c)), rd(c), int(v or 0)]
    # 盤中執行（例如改程式觸發、排程延遲）：今天那根還沒收盤就不收，小卡一律是收盤價。
    # 「正在盤中」＝現在落在 Yahoo 給的 regular 時段內（Yahoo 報價本身延遲 20 分，不能用最後成交時間判斷：
    #   2026-11-18 10:20 韓股盤中，用「20 分鐘內有成交」判斷就漏掉，把盤中那根收進來了）。
    meta = r.get("meta") or {}
    tp = (meta.get("currentTradingPeriod") or {}).get("regular") or {}
    rmt, now = meta.get("regularMarketTime") or 0, time.time()
    ymd = lambda t: (dt.datetime.utcfromtimestamp(t) + dt.timedelta(seconds=off)).strftime("%Y%m%d")
    openNow = bool(tp.get("start") and tp.get("end") and tp["start"] <= now < tp["end"])
    if openNow:
        by.pop(ymd(tp["start"]), None)
    # 2026-11-18：Yahoo 常把「最後一根」日 K 的開高低收回成 null（台北 00:17：東京、首爾、上海 11/17 那根都是 None，22:53 還有值；
    # 台北 10:20：美股 11/17 那根也是 None）。那一天（hole）不在盤中時的補法，依序：
    #   ① 用 15 分 K 自己合成當天的開高低（收盤、量用 meta）；② 上一次存檔有那天就沿用；③ 只用 meta 補（沒有開盤價 → 開＝收）。
    tsd = {ymd(t) for t in r["timestamp"]}
    lastd = max(by) if by else ""
    hole = sorted(d for d in tsd if d > lastd and not (openNow and d == ymd(tp["start"])))
    src = ""
    if hole:
        keep = {x[0]: x for x in (oldb or [])}
        d = ymd(rmt) if rmt else ""
        px = meta.get("regularMarketPrice")
        if d in hole and px:
            try:
                j2 = http(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=5d&interval=15m", tries=2)
                r2 = j2["chart"]["result"][0]
                q2 = r2["indicators"]["quote"][0]
                bb = [(o2, h2, l2, v2) for t2, o2, h2, l2, c2, v2 in zip(r2["timestamp"], q2["open"], q2["high"], q2["low"], q2["close"], q2["volume"])
                      if ymd(t2) == d and o2 and h2 and l2 and c2]
                if len(bb) >= 4:
                    vol = meta.get("regularMarketVolume") or sum(x[3] or 0 for x in bb)
                    by[d] = [d, rd(bb[0][0]), rd(max(max(x[1] for x in bb), px)), rd(min(min(x[2] for x in bb), px)), rd(px), int(vol)]
                    src = "15m"
            except Exception as e:  # noqa
                src = f"15m失敗 {e}"[:60]
        for d2 in hole:
            if d2 not in by and d2 in keep:
                by[d2] = keep[d2][:6]
                src += " old"
        if d in hole and d not in by and px:
            hi, lo = meta.get("regularMarketDayHigh") or px, meta.get("regularMarketDayLow") or px
            by[d] = [d, rd(px), rd(max(hi, px)), rd(min(lo, px)), rd(px), int(meta.get("regularMarketVolume") or 0)]
            src += " meta"
    DBG[sym] = {"now": int(now), "rmt": rmt, "tp": [tp.get("start"), tp.get("end")], "off": off, "open": openNow, "src": src,
                "ts": r["timestamp"][-3:], "cl": (q.get("close") or [])[-3:], "last": lastd}
    DBG[sym]["hole"] = hole
    DBG[sym]["last2"] = max(by) if by else None
    rows = [by[d] for d in sorted(by)]
    if len(rows) < 30:
        raise RuntimeError(f"only {len(rows)} bars")
    cl = [x[4] for x in rows]
    for i, x in enumerate(rows):
        x.append(rd(sum(cl[i - 239:i + 1]) / 240) if i >= 239 else None)
    return rows[-KEEP:]


def main():
    themes = json.load(open("data/themes.json", encoding="utf-8"))["themes"]
    want = {}
    cn = {}
    try:
        cn = {x["id"]: x.get("cn") or "" for x in json.load(open("us/data/index.json", encoding="utf-8"))}
    except Exception:  # noqa
        pass
    for t in themes:
        for c in t.get("us") or []:
            c = str(c).strip().upper()
            if c:
                want.setdefault("us" + c, {"c": c, "m": "us", "n": c, "cn": cn.get(c, "")})
        for m in ("jp", "kr", "cn"):      # cn＝滬深 A 股（2026-11-18 加：長鑫科技 688825）
            for c, n in t.get(m) or []:
                want.setdefault(m + str(c), {"c": str(c), "m": m, "n": n})
    old = {}
    if os.path.exists(OUT):
        try:
            old = json.load(open(OUT, encoding="utf-8")).get("s") or {}
        except Exception:  # noqa
            old = {}
    out, err = {}, []
    for k, w in want.items():
        got = None
        sfx = SFX[w["m"]]
        prev = (old.get(k) or {}).get("sym")
        if prev and w["m"] != "us":   # 上次成功的代號尾碼先試
            sfx = [x for x in sfx if prev.endswith(x)] + [x for x in sfx if not prev.endswith(x)]
        why = ""
        for s in sfx:
            try:
                got = (w["c"] + s, bars(w["c"] + s, (old.get(k) or {}).get("b")))
                break
            except Exception as e:  # noqa
                why = f"{w['c']}{s} {e}"
            time.sleep(0.3)
        if got:
            out[k] = {**w, "sym": got[0], "b": got[1]}
        else:
            err.append(why)
            if k in old:
                out[k] = {**old[k], **w}
        time.sleep(0.35)
    if not out:
        print("全部失敗，不寫檔：", err)
        sys.exit(1)
    now = (dt.datetime.utcnow() + dt.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")
    json.dump({"updated": now, "ver": 5, "dbg": {k: DBG.get(k) for k in DBGK}, "s": out, "err": err}, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    last = {}
    for v in out.values():
        last[v["m"]] = max(last.get(v["m"], ""), v["b"][-1][0])
    print(f"ovs: {len(out)}／{len(want)} 檔，最新 {last}，失敗 {len(err)}：{err[:5]}，{os.path.getsize(OUT) // 1024} KB")


if __name__ == "__main__":
    main()
