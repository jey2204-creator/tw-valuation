"""主排程 方案B 步驟 14：由建好的 days／fdays 與 db 近幾日文件產生簡短回報文字（只陳述資料，不給投資建議）。

用法：python itrust/daily_report.py <out_dir> <db_dir> [mode]
  out_dir：daily_build.py 的輸出（days.json、fdays.json、report.json；若有 prev_report.json 一併摘要）
  db_dir：ArtifactData 下載的 db 副本（days/、fdays/ 近幾日，meta/industry.json）
  mode：並行 或 正式（只影響第一行）
"""
import json, sys
from pathlib import Path


def pct(r):
    chg, cl = r.get("chg"), r.get("cl")
    if chg is None or cl is None or cl - chg == 0:
        return "—"
    return f"{chg / (cl - chg) * 100:+.2f}%"


def main():
    out_dir, db_dir = Path(sys.argv[1]), Path(sys.argv[2])
    mode = sys.argv[3] if len(sys.argv) > 3 else "並行"
    days = json.loads((out_dir / "days.json").read_text(encoding="utf-8"))
    fdays = json.loads((out_dir / "fdays.json").read_text(encoding="utf-8"))
    rep = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    D = days["id"]
    ind = {}
    names = {}
    ip = db_dir / "meta" / "industry.json"
    if ip.exists():
        j = json.loads(ip.read_text(encoding="utf-8"))
        ind, names = j.get("map") or {}, j.get("names") or {}
    # 近幾日 db 文件（不含今天；今天用建好的）
    hist = {}
    for p in sorted((db_dir / "days").glob("*.json")):
        if p.stem < D:
            hist[p.stem] = json.loads(p.read_text(encoding="utf-8"))
    fhist = {}
    for p in sorted((db_dir / "fdays").glob("*.json")):
        if p.stem < D:
            fhist[p.stem] = json.loads(p.read_text(encoding="utf-8"))
    prev_ids = sorted(hist)[-4:]
    rows = days["rows"]
    frows = fdays["rows"]
    tf = fdays.get("tf") or {}
    top20 = [r for r in sorted((r for r in rows if r["v"] > 0 and r["amt"] >= 0.5), key=lambda r: -r["p"])][:20]

    def top20_of(doc):
        return [r["c"] for r in sorted((r for r in doc["rows"] if r["v"] > 0 and r["amt"] >= 0.5), key=lambda r: -r["p"])[:20]]

    prev_tops = [top20_of(hist[d]) for d in reversed(prev_ids)]  # 由近到遠

    def streak(code):
        n = 1
        for t in prev_tops:
            if code in t:
                n += 1
            else:
                break
        return n

    def cum5(code):
        s = sum(next((r["v"] for r in hist[d]["rows"] if r["c"] == code), 0) for d in prev_ids)
        r = next(r for r in rows if r["c"] == code)
        return (s + r["v"]) / r["s"] * 100

    L = []
    c, fc = days["counts"], fdays["counts"]
    L.append(f"【{mode}模式】交易日 {D}；上市 投信買 {c['twse']['trustBuy']}／賣 {c['twse']['trustSell']}／無 {c['twse']['trustZero']}，外資買 {fc['twse']['foreignBuy']}／賣 {fc['twse']['foreignSell']}" +
             (f"；上櫃 投信買 {c['tpex']['trustBuy']}／賣 {c['tpex']['trustSell']}／無 {c['tpex']['trustZero']}，外資買 {fc['tpex']['foreignBuy']}／賣 {fc['tpex']['foreignSell']}" if "tpex" in c else "；上櫃未更新") +
             (f"；{days['note']}" if days.get("note") else ""))
    pr = out_dir / "prev_report.json"
    if pr.exists():
        parts = []
        for x in json.loads(pr.read_text(encoding="utf-8")):
            if not x["fixes"] and not x["ffixes"] and not x["warnings"]:
                parts.append(f"{x['d']} OK")
            else:
                parts.append(f"{x['d']} 投信更正 {len(x['fixes'])}、外資更正 {len(x['ffixes'])}" + ("；" + "；".join(x["warnings"]) if x["warnings"] else "") +
                             ("；" + "、".join(f"{a} {b} {o}→{n}" for a, b, o, n in (x["fixes"] + x["ffixes"])[:8]) if (x["fixes"] or x["ffixes"]) else ""))
        L.append("前 2 日核對：" + "；".join(parts))
    L.append("投信買超前 5：" + "；".join(f"{r['c']} {r['n']} {r['p']:.3f}% {r['amt']}億 近5日{cum5(r['c']):+.3f}% {pct(r)}" for r in top20[:5]))
    fb = [r for r in frows if r["fv"] > 0 and r["amt"] >= 1][:5]
    L.append("外資買超前 5（≥1億）：" + "；".join(f"{r['c']} {r['n']} {r['p']:.3f}% {r['amt']}億 近5日{(sum(r['f4']) + r['fv']) / r['s'] * 100:+.3f}% 持股{r['hp']}%" for r in fb))
    ts = sorted((r for r in rows if r["v"] < 0 and abs(r["amt"]) >= 0.5), key=lambda r: r["p"])[:5]
    L.append("投信賣超前 5：" + "；".join(f"{r['c']} {r['n']} {r['p']:.3f}% {r['amt']}億" for r in ts))
    fs = [r for r in frows if r["fv"] < 0 and abs(r["amt"]) >= 1][:5]
    L.append("外資賣超前 5（≥1億）：" + "；".join(f"{r['c']} {r['n']} {r['p']:.3f}% {r['amt']}億" for r in fs))
    # 產業淨額（今日＋近5日）
    def ind_net(doc, fdoc):
        net = {}
        for r in doc["rows"]:
            k = ind.get(r["c"]) or "99"
            net[k] = net.get(k, 0) + r["amt"]
        for k, v in (fdoc.get("find") or {}).items():
            net[k] = net.get(k, 0) + v["b"] + v["s"]
        return net

    today = ind_net(days, fdays)
    five = dict(today)
    for d in prev_ids:
        if d in fhist:
            for k, v in ind_net(hist[d], fhist[d]).items():
                five[k] = five.get(k, 0) + v
    order = sorted(today, key=lambda k: today[k])
    L.append("產業淨賣超前 5：" + "；".join(f"{names.get(k, k)} {today[k]:+.2f}億（近5日 {five.get(k, 0):+.2f}）" for k in order[:5]))
    L.append("產業淨買超前 3：" + "；".join(f"{names.get(k, k)} {today[k]:+.2f}億（近5日 {five.get(k, 0):+.2f}）" for k in order[::-1][:3]))
    both = sorted((r for r in rows if r["v"] > 0 and r["amt"] >= 0.5 and tf.get(r["c"], 0) > 0), key=lambda r: -(r["p"] + tf[r["c"]] / r["s"] * 100))[:5]
    L.append("土洋同買前 5：" + "；".join(f"{r['c']} {r['n']} 投{r['p']:.3f}%＋外{tf[r['c']] / r['s'] * 100:.3f}%" for r in both))
    todays = []
    for r in top20:
        t = r.get("t") or {}
        if t.get("na") or not (t.get("bull") and t.get("hl") and not t.get("brk")):
            continue
        if streak(r["c"]) < 2 or cum5(r["c"]) < r["p"] * 0.7:
            continue
        todays.append(f"{r['c']} {r['n']} 觸發 {t['trig']} 停損 {t['sl']}（{t['slPct']}%{'，>8%' if (t['slPct'] or 0) > 8 else ''}）{'外資同買' if tf.get(r['c'], 0) > 0 else '外資未同買'}")
    L.append("今日清單（近5日≥單日×0.7、連續≥2天、多頭排列、底底高、未破底）：" + ("；".join(todays) if todays else "無"))
    flags = []
    for r in top20:
        f = []
        if streak(r["c"]) >= 3:
            f.append(f"連續{streak(r['c'])}天")
        if r.get("dp"):
            f.append("處置")
        if r.get("fd"):
            f.append("全額交割")
        if r.get("sdiff", 0) > 5:
            f.append("≠觀測站")
        if r.get("cb"):
            f.append("可轉債")
        if f:
            flags.append(f"{r['c']} {r['n']}（{'、'.join(f)}）")
    L.append("標記：" + ("；".join(flags) if flags else "無"))
    L.append(f"技術欄位缺漏：{'、'.join(rep['rows']['techMissing']) or '無'}；產業對照變動：{len(rep['industryChanged'])} 檔；觀測站股數更正：{len(rep['mopsFixed'])} 檔；剔除：{len(rep['excluded'])} 列" +
             (f"（{'、'.join(e[0] + ' ' + e[1] + ' ' + e[3] for e in rep['excluded'][:10])}）" if rep["excluded"] else ""))
    print("\n".join(L))


if __name__ == "__main__":
    main()
