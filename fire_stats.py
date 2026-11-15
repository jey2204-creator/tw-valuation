"""🔥 主力訊號「上榜後 N 日報酬」統計（2026-11-15）→ data/fire_stats.json（fstats.html 用）
回答：這個訊號過去準不準？該在連續符合的第幾天進場？
事件＝全市場某檔在某天符合 🔥（data/fire_hist.json）。依「連續符合的第幾天」分組：第 1 天（🆕 新進）、第 2 天、第 3 天、第 4～5 天、第 6 天以上。
  連續天數回推到歷史起點的不算（不知道實際第幾天）。
進場價兩種：e1＝隔天收盤（訊號收盤後才知道，實際買得到的價位，預設）；e0＝當天收盤（理想值，買不到）。
持有 1／3／5／10 個交易日，報酬＝收盤對收盤、還原除權息／減資／面額變更（data/adj.json）。
對照＝同一天進場、持有同樣天數的「全市場所有股票」報酬中位數；超額＝個股報酬 − 對照。
每格：n 筆數、nd 涵蓋幾個進場日、win 勝率、avg 平均、med 中位數、p10 最差 10%（第 10 百分位）、base 對照平均、ex 平均超額、exWin 贏過對照的比例。
2026-11-15 起事件永久存檔在 data/fire_ev/YYYYMM.json，統計從存檔算（fire_hist.json 只留 60 個交易日會滾動，存檔不會掉）。
由 fire_hist.py 的 main() 結尾呼叫；也可單獨跑：python fire_stats.py
"""
import json, datetime as dt, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
HIST = DATA / "hist"
OUT = DATA / "fire_stats.json"
EVD = DATA / "fire_ev"                 # 事件永久存檔（每月一檔）
HS = [1, 3, 5, 10]
BUCKETS = [("d1", "🆕 第 1 天", 1, 1), ("d2", "第 2 天", 2, 2), ("d3", "第 3 天", 3, 3), ("d45", "第 4～5 天", 4, 5), ("d6", "第 6 天以上", 6, 999)]


def load(p, default):
    try:
        return json.loads(Path(p).read_text("utf-8"))
    except Exception:
        return default


def pctl(a, q):
    a = sorted(a)
    if not a:
        return None
    k = (len(a) - 1) * q
    lo = int(k)
    hi = min(lo + 1, len(a) - 1)
    return a[lo] + (a[hi] - a[lo]) * (k - lo)


def main():
    fh = load(DATA / "fire_hist.json", {})
    fdays = fh.get("days") or []
    if len(fdays) < 12:
        print("fire_stats: 歷史不足 12 天，先不輸出"); return
    ADJ = load(DATA / "adj.json", {}).get("ev", {})
    recs = []
    files = sorted(HIST.glob("20*.json"))
    k0 = next((k for k, f in enumerate(files) if f.stem >= fdays[0]), 0)
    for f in files[max(0, k0 - 8):]:                 # 多讀前面幾天：要知道「前一個交易日」才能把連續天數接上存檔
        r = load(f, {})
        if not r.get("closed") and r.get("p") and "pL" in r.get("src", []):
            recs.append((f.stem, r["p"]))
    stems = [s for s, _ in recs]
    pos = {s: i for i, s in enumerate(stems)}
    last = len(stems) - 1

    def close(c, i):
        v = recs[i][1].get(c)
        return v[0] if v and v[0] else None

    def ret(c, a, b):
        x, y = close(c, a), close(c, b)
        if not x or not y:
            return None
        for d, f, *_ in ADJ.get(c, []):
            if stems[a] < d <= stems[b]:
                x *= f
        return y / x - 1

    base_cache = {}

    def base(a, b):
        if (a, b) not in base_cache:
            v = [r for r in (ret(c, a, b) for c in recs[a][1]) if r is not None]
            base_cache[(a, b)] = st.median(v) if v else None
        return base_cache[(a, b)]

    # ---- 永久存檔（2026-11-15）：data/fire_ev/YYYYMM.json = {"b": {日: [對照×8]}, "e": {日: {代號: [連續第幾天, 報酬×8]}}}
    #   8 個值的順序＝e0 的 1/3/5/10 日、e1 的 1/3/5/10 日；還沒滿天數的是 null，之後每次排程補上
    #   連續天數是負數＝回推到歷史起點、只知道「至少幾天」（統計不採用，但留著讓之後的連續天數接得上）
    #   fire_hist.json 只留 60 個交易日會滾動；這裡的舊日子不再更動也不刪，統計改從這裡算 → 樣本會一直累積
    #   2026-11-15 再加 4 欄（先存著、之後切分用；算不出來的是 null）：
    #     chip＝籌碼標籤 c 集中／r 散戶追／d 分散／"" 都不是（集保 4 週變化，只用「事件日之前」已公布的那一週，規則同首頁）
    #     nt＝1 當天列注意股、2 處置中、3 兩者（data/notice；上櫃處置 2026/10/29 前沒有資料）
    #     fr／tr＝外資／投信 5 日買超占 5 日成交量 %
    WK = []
    for f in sorted((DATA / "tdcc").glob("20*.json")):
        j = load(f, None)
        if j:
            WK.append((f.stem, j))
    D8 = lambda s: dt.datetime.strptime(s, "%Y%m%d")
    okv = lambda v: isinstance(v, list) and len(v) >= 3 and v[2] and v[2] > 1

    def chip(c, day):
        ws = [(d, w) for d, w in WK if d < day]
        if not ws or (D8(day) - D8(ws[-1][0])).days > 10:
            return None
        cd, cw = ws[-1]
        v = cw.get(c)
        if not okv(v):
            return None
        t = D8(cd) - dt.timedelta(weeks=4)
        p4 = next((w[c] for d, w in ws if abs((D8(d) - t).days) <= 3 and okv(w.get(c))), None)
        if not p4:
            return None
        b, pm = v[0] - p4[0], (v[2] / p4[2] - 1) * 100
        return "c" if b > .3 and pm < -1 else "r" if b > .3 and pm > 3 else "d" if b < -.3 and pm > 1 else ""

    NH = {k: v for k, v in load(DATA / "notice" / "hist.json", {}).items() if k.isdigit()}
    DH = [v for v in load(DATA / "notice" / "dis_hist.json", {}).values() if isinstance(v, dict) and v.get("c") and v.get("end")]

    def nt(c, day):
        if day not in NH:
            return None
        return (1 if c in NH[day].get("att", []) else 0) | (2 if c in NH[day].get("dis", []) or any(v["c"] == c and v.get("start", "") <= day < v["end"] for v in DH) else 0)

    ARC = {}
    for f in sorted(EVD.glob("20*.json")):
        j = load(f, {})
        for d, v in (j.get("e") or {}).items():
            ARC[d] = {"e": v, "b": (j.get("b") or {}).get(d)}
    run = {}
    first = pos.get(fdays[0])
    prev = stems[first - 1] if first else None       # hist 比 fire_hist 長，前一個交易日若已存檔就能把連續天數接上
    seeded = bool(prev and prev in ARC)
    if seeded:
        run = {c: (abs(v[0]), v[0] < 0) for c, v in ARC[prev]["e"].items()}
    touched = set()
    for k, day in enumerate(fdays):
        cur = fh["d"].get(day, {})
        nxt = {}
        if day in pos:
            i = pos[day]
            ent = ARC.setdefault(day, {"e": {}, "b": None})
            ent["b"] = [None if (i + e + h > last or base(i + e, i + e + h) is None) else round(base(i + e, i + e + h), 5) for e in (0, 1) for h in HS]
            touched.add(day[:6])
        for c in cur:
            n, capped = run.get(c, (0, k == 0 and not seeded))
            nxt[c] = (n + 1, capped)
            if day in pos:
                rs = []
                for e in (0, 1):
                    for h in HS:
                        r = ret(c, i + e, i + e + h) if i + e + h <= last else None
                        rs.append(None if r is None else round(r, 5))
                row = cur[c]
                ent["e"][c] = [-(n + 1) if capped else n + 1] + rs + [chip(c, day), nt(c, day), row[8] if len(row) > 8 else None, row[9] if len(row) > 9 else None]      # 已存檔但這次沒算到的代號保留不動
        run = nxt
    EVD.mkdir(exist_ok=True)
    for ym in sorted(touched):
        ds = sorted(d for d in ARC if d[:6] == ym)
        (EVD / f"{ym}.json").write_text(json.dumps({"fields": ["streak"] + [f"e{e}h{h}" for e in (0, 1) for h in HS] + ["chip", "nt", "fr", "tr"],
            "b": {d: ARC[d]["b"] for d in ds}, "e": {d: ARC[d]["e"] for d in ds}}, ensure_ascii=False, separators=(",", ":")), "utf-8")

    def cell(rows):
        """rows = [(報酬, 對照, 進場日)]"""
        if not rows:
            return None
        r = [x[0] for x in rows]
        ex = [x[0] - x[1] for x in rows if x[1] is not None]
        f = lambda v, d=4: None if v is None else round(v, d)
        return dict(n=len(r), nd=len({x[2] for x in rows}), win=f(sum(v > 0 for v in r) / len(r), 3), avg=f(st.mean(r)), med=f(st.median(r)),
                    p10=f(pctl(r, .1)), base=f(st.mean([x[1] for x in rows if x[1] is not None])) if ex else None,
                    ex=f(st.mean(ex)) if ex else None, exWin=f(sum(v > 0 for v in ex) / len(ex), 3) if ex else None)

    adays = sorted(ARC)
    ev = [(d, c, v) for d in adays for c, v in ARC[d]["e"].items() if v[0] > 0]
    out = {}
    for e in (0, 1):
        tab = {}
        for key, _, lo, hi in BUCKETS + [("all", "全部 🔥", 1, 999)]:
            tab[key] = {}
            for hi_, h in enumerate(HS):
                j = e * len(HS) + hi_
                rows = [(v[1 + j], (ARC[d]["b"] or [None] * 8)[j], d) for d, c, v in ev if lo <= v[0] <= hi and v[1 + j] is not None]
                tab[key][str(h)] = cell(rows)
        out[f"e{e}"] = tab
    fdays = adays
    res = {"updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "from": fdays[0], "to": fdays[-1], "pxAsof": stems[-1],
           "nDays": len(fdays), "nEv": len(ev), "hs": HS, "buckets": [[k, lb] for k, lb, *_ in BUCKETS] + [["all", "全部 🔥"]], "s": out}
    OUT.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), "utf-8")
    c = out["e1"]["d1"]["5"] or {}
    print(f"fire_stats: {len(ev)} 筆事件（{fdays[0]}～{fdays[-1]}）；🆕 隔日收盤進場持有 5 日：n={c.get('n')} 勝率 {c.get('win')} 平均 {c.get('avg')} 超額 {c.get('ex')}")


if __name__ == "__main__":
    main()
