"""🔥 主力訊號的每日歷史名單（2026-11-15）→ data/fire_hist.json
首頁「🔥 主力訊號」要能切日期看之前上榜的個股、標「🆕 新進／連 N 天」、列出「掉出」的股票。
網頁的自選存在手機裡 → 這裡存「全市場」每天的 🔥 名單，網頁再篩出主題＋自選。

輸出 {"asof": 最新交易日, "days": [有名單的交易日，舊→新], "fields": [...],
      "d": {YYYYMMDD: {代號: [週%, 月%, 季%, 量比, 外資5日(張), 投信5日(張), 收盤, 當日漲跌%, 外資5日占量%, 投信5日占量%]}},   ← 當天 🔥 的股票與當天收盤當下的數字
                                                                              （最後兩欄 2026-11-15 加：5 日買超 ÷ 5 日成交量，給 fire_stats.py 存檔切分用，網頁沒用到）
      "x": {YYYYMMDD: {代號: [原因, 當日漲跌%]}}}                                                  ← 前一個交易日有 🔥、這天沒有（掉出）
  原因是位元加總：1＝月漲幅 ≤ 0、2＝量比 < 1.5、4＝投信／外資 5 日買超不到 5 日成交量 1%、8＝當天沒資料
  🔥 條件與每個數字的算法跟 fetch_momentum.py 的 compute() 一致（月／季＝日曆日、還原除權息／減資／面額變更）：
    把資料截到那一天再用同一套公式算；最新一天的名單必須跟 momentum.json 的 fire 完全相同（main() 會核對並印出）。
  法人資料不足 5 個交易日的日子不算（那時 5 日買超不完整）。保留最近 KEEP_DAYS 個交易日；算不出來的舊日子沿用舊檔。
由 fetch_momentum.py 的 main() 結尾呼叫；也可單獨跑：python fire_hist.py
"""
import json, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
HIST = DATA / "hist"
OUT = DATA / "fire_hist.json"
KEEP_DAYS = 60
FIELDS = ["w", "m", "q", "vr", "f5", "t5", "close", "chg", "fr", "tr"]


def load(p, default):
    try:
        return json.loads(Path(p).read_text("utf-8"))
    except Exception:
        return default


def ret(cl, n):
    """同 fetch_momentum.compute() 的 ret：收盤對比 n 個交易日前；最新一天沒成交用 5 日內最後一筆，基準日沒成交往前找、再往後 3 天"""
    cur = next((x for x in reversed(cl[-5:]) if x), None)
    if len(cl) <= n or cur is None:
        return None
    base = next((x for x in reversed(cl[:len(cl) - n]) if x), None)
    if base is None:
        base = next((x for x in cl[len(cl) - n:len(cl) - n + 3] if x), None)
    return round((cur / base - 1) * 100, 1) if base else None


def cal_n(stems, months):
    """stems 最後一天往回 months 個月的同一天（休市取之前最近的交易日）→ 相隔幾個交易日"""
    t = dt.datetime.strptime(stems[-1], "%Y%m%d").date()
    y, mo = t.year, t.month - months
    while mo <= 0:
        y, mo = y - 1, mo + 12
    last = (dt.date(y + (mo == 12), mo % 12 + 1, 1) - dt.timedelta(days=1)).day
    tgt = f"{y:04d}{mo:02d}{min(t.day, last):02d}"
    idx = max((i for i, s in enumerate(stems) if s <= tgt), default=None)
    return len(stems) - 1 - idx if idx is not None else None


def build():
    days = []
    for f in sorted(HIST.glob("*.json")):
        rec = load(f, {})
        if not rec.get("closed") and rec.get("p"):
            days.append((f.stem, rec))
    pdays = [x for x in days if "pL" in x[1].get("src", [])]
    idays = [x for x in days if "iL" in x[1].get("src", []) and x[1].get("i")]
    stems = [s for s, _ in pdays]
    istems = [s for s, _ in idays]
    ADJ = load(DATA / "adj.json", {}).get("ev", {})
    if len(idays) < 5 or not stems:
        return {}, {}, stems
    want = [s for s in stems if s >= istems[4]][-KEEP_DAYS:]
    pos = {s: i for i, s in enumerate(stems)}
    both = [{"iL", "iO"} <= set(r.get("src", [])) for _, r in idays]

    CL, VO, IV = {}, {}, {}

    def series(c):
        if c not in CL:
            pv = [r["p"].get(c) or [None] for _, r in pdays]
            CL[c] = [v[0] for v in pv]
            VO[c] = [v[1] if len(v) > 1 else None for v in pv]
            # 某天櫃買法人沒抓到時，上櫃股那天不計（避免當成 0）——同 compute()
            IV[c] = [(s, r["i"][c] if c in r["i"] else [0, 0]) for k, (s, r) in enumerate(idays) if c in r["i"] or both[k]]
        return CL[c], VO[c], IV[c]

    def one(c, i):
        """第 i 個交易日收盤當下：回傳 (列, fire, 原因位元)；完全沒資料回傳 None"""
        day = stems[i]
        cl0, vo0, iv0 = series(c)
        cl, vo = cl0[:i + 1], vo0[:i + 1]
        st = stems[:i + 1]
        nM, nQ = NM[i], NQ[i]
        w, m20 = ret(cl, 5), ret(cl, 20)
        mc, qc = (ret(cl, nM) if nM else None), (ret(cl, nQ) if nQ else None)
        ma = None
        evs = [(d, f) for d, f, *_ in ADJ.get(c, []) if st[0] < d <= day]
        cla = cl
        if evs:
            cla = []
            for sdt, x in zip(st, cl):
                k = 1.0
                for d, f in evs:
                    if sdt < d:
                        k *= f
                cla.append(x * k if x else x)
            w, ma, qa = ret(cla, 5), (ret(cla, nM) if nM else None), (ret(cla, nQ) if nQ else None)
            mc_show, qc_show = ma, qa
        else:
            mc_show, qc_show = mc, qc
        v5 = [x for x in vo[-5:] if x is not None]
        v20 = [x for x in vo[-20:] if x is not None]
        vr = round((sum(v5) / len(v5)) / (sum(v20) / len(v20)), 2) if v5 and v20 and sum(v20) > 0 else None
        iv = [x for s, x in iv0 if s <= day]
        f5, t5 = sum(x[0] for x in iv[-5:]), sum(x[1] for x in iv[-5:])
        vol5 = sum(v5) if v5 else 0
        big = vol5 > 0 and max(f5, t5) >= vol5 * 0.01
        mf = ma if ma is not None else mc if mc is not None else m20
        fire = bool(iv) and mf is not None and mf > 0 and vr is not None and vr >= 1.5 and big
        why = (0 if (mf is not None and mf > 0) else 1) | (0 if (vr is not None and vr >= 1.5) else 2) | (0 if (iv and big) else 4)
        cur = next((x for x in reversed(cl[-5:]) if x), None)
        if cur is None:
            return None
        pv = next((x for x in reversed(cla[-6:-1]) if x), None)
        chg = round((cur / pv - 1) * 100, 2) if pv and cl[-1] else None
        k = lambda x: round(x / 1000)
        sh = lambda x: round(x / vol5 * 100, 1) if iv and vol5 > 0 else None     # 5 日買超占 5 日成交量 %（統計切分用）
        return [w, mc_show, qc_show, vr, k(f5) if iv else None, k(t5) if iv else None, cur, chg, sh(f5), sh(t5)], fire, why

    NM = {pos[s]: cal_n(stems[:pos[s] + 1], 1) for s in want}
    NQ = {pos[s]: cal_n(stems[:pos[s] + 1], 3) for s in want}
    d, x, prev = {}, {}, None
    for s in want:
        i = pos[s]
        ids = sorted({c for _, r in pdays[max(0, i - 4):i + 1] for c in r["p"]})
        row = {}
        for c in ids:
            r = one(c, i)
            if r and r[1]:
                row[c] = r[0]
        d[s] = row
        if prev is not None:
            out = {}
            for c in sorted(set(d[prev]) - set(row)):
                r = one(c, i)
                out[c] = [r[2], r[0][7]] if r else [8, None]
            x[s] = out
        prev = s
    return d, x, stems


def main():
    d, x, stems = build()
    if not d:
        print("fire_hist: 法人資料不足 5 天，先不輸出"); return
    old = load(OUT, {})
    for k, v in (old.get("d") or {}).items():          # 已經算不出來的舊日子（法人資料被瘦身）沿用舊檔
        if k not in d and k < min(d):
            d[k] = v
            if k in (old.get("x") or {}):
                x[k] = old["x"][k]
    keep = sorted(d)[-KEEP_DAYS:]
    res = {"updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "asof": keep[-1], "days": keep, "fields": FIELDS,
           "why": {"1": "月漲幅轉負", "2": "量比 < 1.5", "4": "法人 5 日買超不足", "8": "當天沒資料"},
           "d": {k: d[k] for k in keep}, "x": {k: x[k] for k in keep if k in x}}
    OUT.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), "utf-8")
    msg = f"fire_hist: {len(keep)} 個交易日（{keep[0]}～{keep[-1]}），最新一天 🔥 {len(d[keep[-1]])} 檔"
    mo = load(DATA / "momentum.json", {})
    if mo.get("asof") == keep[-1] and mo.get("d"):     # 核對：最新一天必須跟 momentum.json 的 fire 相同
        a, b = {c for c, v in mo["d"].items() if v[10]}, set(d[keep[-1]])
        msg += "，與 momentum.json 一致" if a == b else f"，⚠ 與 momentum.json 不一致：多 {sorted(b - a)[:8]} 少 {sorted(a - b)[:8]}"
    print(msg)
    try:                                 # 2026-11-15：上榜後 N 日報酬統計（fstats.html）
        import fire_stats
        fire_stats.main()
    except Exception as e:
        print("fire_stats 失敗：", e)


if __name__ == "__main__":
    main()
