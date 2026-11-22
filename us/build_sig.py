#!/usr/bin/env python3
"""美股每檔的「財報動能」三項＋近一月漲跌 → us/data/sig.json（給台股站主題表的美股燈號用，batch19）
算法跟美股站 us/index.html 的 statOf()／lastER()／monRet() 一樣：
  racc  營收加速＝最新季營收年增 − 上一季營收年增（百分點；兩季要連續、只算季報）
  surp  EPS 驚喜率＝earnings_auto.json hist 最近一筆有預估的財報（%）
  react 同一筆財報的首日漲跌（%；首日還沒收盤＝null）
  m1    近一月漲跌＝最後收盤對上個月同一天（遇假日往前找）的收盤（%，日 K 依分割調整）
主題燈號由前端用主題自己的成份股算：三項各取中位數（不到一半檔數有值不算），全正 🟢、全負 🔴、其他 🟡、可算不到 2 項 ⚪
只用標準函式庫；在 update_us_earnings.yml 抓完驚喜率後跑。
"""
import json, calendar
from pathlib import Path

D = Path(__file__).resolve().parent / "data"


def nq(l):
    y, q = int(l[:2]), int(l[3]) + 1
    if q > 4:
        q, y = 1, y + 1
    return f"{y:02d}Q{q}"


def racc(d):
    q = d.get("q") or []
    if d.get("freq") != "Q" or len(q) < 2:
        return None
    lq, pq = q[-1], q[-2]
    by = {x[0]: x for x in q}
    yoy = lambda r: (lambda p: (r[2] / p[2] - 1) * 100 if p and p[2] and p[2] > 0 and r[2] is not None else None)(by.get(f"{int(r[0][:2]) - 1:02d}{r[0][2:]}"))
    a, b = yoy(lq), yoy(pq)
    if a is None or b is None or nq(pq[0]) != lq[0]:
        return None
    return a - b


def last_er(h):
    for r in reversed(h or []):
        if len(r) > 3 and r[3] is not None:
            return r
    return None


def m1(o):
    k = (o or {}).get("k") or []
    if len(k) < 2:
        return None
    l = k[-1]
    y, mo, dd = map(int, l[0].split("-"))
    py, pm = (y - 1, 12) if mo == 1 else (y, mo - 1)
    b = f"{py}-{pm:02d}-{min(dd, calendar.monthrange(py, pm)[1]):02d}"
    i = len(k) - 1
    while i >= 0 and k[i][0] > b:
        i -= 1
    return None if i < 0 or not (k[i][4] or 0) > 0 else (l[4] / k[i][4] - 1) * 100


def rd(x, n=1):
    return None if x is None else round(x, n)


def main():
    idx = json.loads((D / "index.json").read_text("utf-8"))
    auto = json.loads((D / "earnings_auto.json").read_text("utf-8")).get("q", {})
    out, asof = {}, ""
    for s in idx:
        t = s["id"]
        try:
            d = json.loads((D / f"{t}.json").read_text("utf-8"))
        except Exception:
            continue
        try:
            o = json.loads((D / "ohlc" / f"{t}.json").read_text("utf-8"))
        except Exception:
            o = None
        r = last_er((auto.get(t) or {}).get("hist"))
        row = [rd(racc(d)), rd(r[3]) if r else None, rd(r[6]) if r and len(r) > 6 else None, rd(m1(o)), r[4] if r and len(r) > 4 else None]
        if any(v is not None for v in row[:4]):
            out[t] = row
        asof = max(asof, s.get("date") or "")
    res = {"asof": asof, "f": ["racc 營收加速(點)", "surp EPS驚喜%", "react 首日%", "m1 近一月%", "er 財報日"], "d": out}
    p = D / "sig.json"
    old = p.read_text("utf-8") if p.exists() else ""
    new = json.dumps(res, ensure_ascii=False, separators=(",", ":"))
    if new != old:
        p.write_text(new, "utf-8")
    print(f"sig.json：{len(out)} 檔，資料日 {asof}")


if __name__ == "__main__":
    main()
