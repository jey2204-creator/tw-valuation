"""從 itrust/data.js 抽最新名單日的「投信前20／外資前20／土洋同買前20」→ data/itrust_top.json

給根目錄的個股估值頁（index.html）當成三個會每天自動換名單的內建主題用。
口徑與分享版排行頁（itrust/index.html）預設值相同：
  投信、外資：買超金額 ≥ 0.5 億、不設張數門檻、市值不限；依買超佔股本％由高到低取前 20
  土洋同買：投信買超（套用投信門檻）且外資當天也淨買超；依投本比＋外本比由高到低取前 20
  連買天數：連續幾個交易日都在該榜前 20 名（土洋＝連續幾天投信、外資同時淨買超）

用法：python itrust/top_extract.py          （data.js 變了就由 .github/workflows/itrust_top.yml 自動跑）
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "itrust" / "data.js"
OUT = ROOT / "data" / "itrust_top.json"
MIN_AMT = 0.5     # 億


def load():
    s = SRC.read_text("utf-8")
    return json.loads(s[s.index("{"): s.rindex("}") + 1])


def pass_t(r):
    return (r.get("v") or 0) > 0 and (r.get("amt") or 0) >= MIN_AMT


def pass_f(r):
    return (r.get("fv") or 0) > 0 and (r.get("amt") or 0) >= MIN_AMT


def top_set_t(days, d):
    doc = days.get(d)
    if not doc:
        return None
    rows = [r for r in doc.get("rows", []) if pass_t(r)]
    rows.sort(key=lambda r: -r["p"])
    return {r["c"] for r in rows[:20]}


def top_set_f(fdays, d):
    doc = fdays.get(d)
    if not doc:
        return None
    rows = [r for r in doc.get("rows", []) if pass_f(r)]
    rows.sort(key=lambda r: -r["p"])
    return {r["c"] for r in rows[:20]}


def fv_of(fdays, d, c):
    f = fdays.get(d)
    if not f:
        return None
    for r in f.get("rows", []):
        if r["c"] == c:
            return r.get("fv")
    tf = f.get("tf") or {}
    return tf.get(c)


def tv_of(days, d, c):
    doc = days.get(d)
    if not doc:
        return None
    for r in doc.get("rows", []):
        if r["c"] == c:
            return r.get("v")
    return 0


def streak(set_fn, c, td, pos):
    n = 0
    for k in range(pos, -1, -1):
        st = set_fn(td[k])
        if st is None or c not in st:
            break
        n += 1
    return n


def main():
    j = load()
    days, fdays = j["days"], j.get("fdays", {})
    cur = j["latest"]
    cal = sorted(set(j.get("cal", [])) | set(days))
    pos = cal.index(cur)
    sub = (j.get("sub") or {}).get("map") or {}
    ind = j.get("ind") or {"map": {}, "names": {}}
    tsh = ((j.get("tsh") or {}).get("t")) or {}

    def tsh_pct(c, s):
        a = tsh.get(c)
        if not a or not s:
            return None
        a = [x for x in a if x[0] <= cur]
        return round(a[-1][1] * 1000 / s * 100, 2) if a else None

    def base(r):
        s = r.get("s") or 0
        cap = round(s * r["cl"] / 1e8) if s and r.get("cl") else None
        return {
            "c": r["c"], "n": r["n"], "m": r.get("m", ""),
            "cl": r.get("cl"), "chg": r.get("chg"),
            "cap": cap,
            "sub": sub.get(r["c"]) or ind["names"].get(ind["map"].get(r["c"], ""), ""),
            "tsh": tsh_pct(r["c"], s),
        }

    # 投信前 20
    cache_t = {}
    set_t = lambda d: cache_t.setdefault(d, top_set_t(days, d))
    rows = sorted([r for r in days[cur].get("rows", []) if pass_t(r)], key=lambda r: -r["p"])[:20]
    it = []
    for i, r in enumerate(rows):
        fv = fv_of(fdays, cur, r["c"])
        it.append({**base(r), "rank": i + 1, "p": round(r["p"], 2), "amt": r.get("amt"), "lots": r.get("lots"),
                   "streak": streak(set_t, r["c"], cal, pos), "fx": bool(fv and fv > 0)})

    # 外資前 20
    cache_f = {}
    set_f = lambda d: cache_f.setdefault(d, top_set_f(fdays, d))
    fi = []
    if fdays.get(cur):
        rows = sorted([r for r in fdays[cur].get("rows", []) if pass_f(r)], key=lambda r: -r["p"])[:20]
        tmap = {r["c"]: r for r in days[cur].get("rows", [])}
        for i, r in enumerate(rows):
            t = tmap.get(r["c"])
            fi.append({**base(r), "rank": i + 1, "p": round(r["p"], 2), "amt": r.get("amt"), "lots": r.get("lots"),
                       "streak": streak(set_f, r["c"], cal, pos), "both": bool(t and (t.get("v") or 0) > 0)})

    # 土洋同買前 20
    both = []
    if fdays.get(cur):
        kept = []
        for r in days[cur].get("rows", []):
            if not pass_t(r):
                continue
            fv = fv_of(fdays, cur, r["c"])
            if not fv or fv <= 0:
                continue
            fp = fv / r["s"] * 100
            ds = 0
            for k in range(pos, -1, -1):
                d = cal[k]
                if not days.get(d) or not fdays.get(d):
                    break
                tv = tv_of(days, d, r["c"]) or 0
                f = fv_of(fdays, d, r["c"]) or 0
                if tv > 0 and f > 0:
                    ds += 1
                else:
                    break
            kept.append((r, fp, ds))
        kept.sort(key=lambda x: -(x[0]["p"] + x[1]))
        for i, (r, fp, ds) in enumerate(kept[:20]):
            both.append({**base(r), "rank": i + 1, "p": round(r["p"], 2), "fp": round(fp, 2),
                         "sum": round(r["p"] + fp, 2), "amt": r.get("amt"), "lots": r.get("lots"), "streak": ds})

    out = {"asof": cur, "builtAt": j.get("builtAt"), "minAmt": MIN_AMT,
           "lists": {"it": it, "fi": fi, "both": both}}
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"{cur}: 投信 {len(it)}、外資 {len(fi)}、土洋 {len(both)} 檔 → {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    sys.exit(main())
