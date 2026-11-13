"""注意／處置名單「當日數字」快照（2026-11-13）→ data/notice/mo_hist.json
首頁注意股主題表切到某個名單日、按「數字：當日」時，週／月／季、量比、投外 5 日、收盤要回到那天收盤當下的值；
另外「列入後%」＝名單日收盤 → 最新收盤，也用這裡的收盤算。

輸出 {"asof": 最新名單日, "fields": [...], "d": {YYYYMMDD: {代號: [週%, 月%, 季%, 量比, 外資5日(張), 投信5日(張), 收盤, 當日漲跌%]}}}
  週＝5 個交易日前；月／季＝上個月／三個月前同一天（休市取前一交易日）——跟 fetch_momentum.py 的 dc 一致
  量比＝近 5 日均量 ÷ 近 20 日均量；法人不足 5 天的給 null
每個名單日只收當天五名單會用到的代號（注意、處置中、快達處置估算、處置剛結束、近 10 個名單日列過注意的），保留 40 個名單日。
由 fetch_notice.py 結尾呼叫；也可單獨跑：python notice_mo.py
"""
import json, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
HIST = DATA / "hist"
NDIR = DATA / "notice"
OUT = NDIR / "mo_hist.json"
KEEP_DAYS = 40
FIELDS = ["w", "m", "q", "vr", "f5", "t5", "close", "chg"]


def load(p, default):
    try:
        return json.loads(Path(p).read_text("utf-8"))
    except Exception:
        return default


def wd_count(a, b):
    """a 之後到 b（含）有幾個平日——跟網頁 wdCount 一致"""
    if not a or not b or a >= b:
        return 0
    x, n = dt.datetime.strptime(a, "%Y%m%d").date(), 0
    for _ in range(120):
        x += dt.timedelta(days=1)
        if x.strftime("%Y%m%d") > b:
            break
        if x.weekday() < 5:
            n += 1
    return n


def codes_for(day, hist, dh, ldays, extra):
    i = ldays.index(day)
    att = lambda d: hist.get(d, {}).get("att", [])
    s = set(att(day)) | set(hist.get(day, {}).get("dis", []))
    for d in ldays[max(0, i - 9):i + 1]:
        s |= set(att(d))
    cnt = {}
    for k, d in enumerate(ldays[max(0, i - 29):i + 1]):
        for c in att(d):
            cnt[c] = cnt.get(c, 0) + 1
    last10 = ldays[max(0, i - 9):i + 1]
    for c, n30 in cnt.items():
        if n30 >= 11 or sum(c in att(d) for d in last10) >= 5:
            s.add(c)
    for v in dh.values():
        if not isinstance(v, dict) or not v.get("end"):
            continue
        if (v.get("start", "") <= day < v["end"]) or (v["end"] <= day and wd_count(v["end"], day) <= 10):
            s.add(v["c"])
    return s | set(extra.get(day, []))


def main():
    hist = {k: v for k, v in load(NDIR / "hist.json", {}).items() if k.isdigit()}
    dh = load(NDIR / "dis_hist.json", {})
    ldays = sorted(d for d in hist if hist[d].get("att"))
    if not ldays:
        print("notice_mo: 沒有名單歷史"); return
    want = ldays[-KEEP_DAYS:]
    extra = {}                                          # 官方快達處置等不在 hist 的代號（最新、前一份）
    for f in (DATA / "notice.json", NDIR / "prev.json"):
        j = load(f, {})
        if j.get("asof"):
            extra[j["asof"]] = [x["c"] for k in ("att", "dis", "pre", "dend", "dpost") for x in j.get(k, [])]

    # 價量：最近 ~150 個交易日就夠（40 個名單日 + 一季 65 天 + 緩衝）
    recs = []
    for f in sorted(HIST.glob("20*.json"))[-170:]:
        r = load(f, {})
        if not r.get("closed") and r.get("p") and "pL" in r.get("src", []):
            recs.append((f.stem, r))
    stems = [s for s, _ in recs]
    pos = {s: i for i, s in enumerate(stems)}
    irecs = [(s, r) for s, r in recs if r.get("i") and "iL" in r.get("src", [])]

    def cal_idx(i, months):
        t = dt.datetime.strptime(stems[i], "%Y%m%d").date()
        y, mo = t.year, t.month - months
        while mo <= 0:
            y, mo = y - 1, mo + 12
        last = (dt.date(y + (mo == 12), mo % 12 + 1, 1) - dt.timedelta(days=1)).day
        tgt = f"{y:04d}{mo:02d}{min(t.day, last):02d}"
        return max((k for k in range(i + 1) if stems[k] <= tgt), default=None)

    def close(c, k):
        v = recs[k][1]["p"].get(c)
        return v[0] if v and v[0] else None

    def ret(c, i, k):
        """收盤對比第 k 個交易日；基準日沒成交往前找最近一筆，再不行往後 3 天內"""
        now = close(c, i)
        if now is None or k is None or k < 0:
            return None
        base = next((x for x in (close(c, j) for j in range(k, -1, -1)) if x), None)
        if base is None:
            base = next((x for x in (close(c, j) for j in range(k + 1, min(k + 3, i))) if x), None)
        return round((now / base - 1) * 100, 1) if base else None

    old = load(OUT, {}).get("d", {})
    out = {}
    recalc = set(want[-3:])                            # 最近 3 個名單日每次重算（法人、收盤可能晚到），更早的沿用
    for day in want:
        if day in old and day not in recalc:
            out[day] = old[day]; continue
        if day not in pos:                             # 那天的收盤還沒進 data/hist
            if day in old:
                out[day] = old[day]
            continue
        i = pos[day]
        iM, iQ = cal_idx(i, 1), cal_idx(i, 3)
        idays = [(s, r) for s, r in irecs if s <= day]
        row = {}
        for c in sorted(codes_for(day, hist, dh, ldays, extra)):
            cl = close(c, i)
            if cl is None:
                continue
            vo = [recs[j][1]["p"].get(c) for j in range(max(0, i - 19), i + 1)]
            vo = [v[1] for v in vo if v and len(v) > 1 and v[1] is not None]
            v5 = vo[-5:]
            vr = round((sum(v5) / len(v5)) / (sum(vo) / len(vo)), 2) if v5 and vo and sum(vo) > 0 else None
            iv = [r["i"][c] if c in r["i"] else [0, 0] for _, r in idays
                  if c in r["i"] or {"iL", "iO"} <= set(r.get("src", []))]
            f5 = round(sum(x[0] for x in iv[-5:]) / 1000) if len(iv) >= 5 else None
            t5 = round(sum(x[1] for x in iv[-5:]) / 1000) if len(iv) >= 5 else None
            pv = next((x for x in (close(c, j) for j in range(i - 1, max(-1, i - 6), -1)) if x), None)
            row[c] = [ret(c, i, i - 5), ret(c, i, iM), ret(c, i, iQ), vr, f5, t5, cl,
                      round((cl / pv - 1) * 100, 2) if pv else None]
        out[day] = row
    res = {"updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "asof": max(out) if out else None,
           "pxAsof": stems[-1] if stems else None, "fields": FIELDS, "d": {k: out[k] for k in sorted(out)}}
    OUT.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"notice_mo: {len(out)} 個名單日、共 {sum(len(v) for v in out.values())} 筆，最新 {res['asof']}（價到 {res['pxAsof']}）")


if __name__ == "__main__":
    main()
