"""方案B（GitHub Actions＋daily_build.py）與電腦版（內建瀏覽器）寫進 db 的 days／fdays 文件逐欄比對。

用法：python itrust/daily_compare.py <built_dir> <db_dir> <D>
  built_dir：daily_build.py 的輸出（days.json、fdays.json）
  db_dir：ArtifactData 下載的 db 副本（days/<D>.json、fdays/<D>.json）
輸出：<built_dir>/compare.md（給人看）與 compare.json（summary），stdout 印 compare.md。
不比 updatedAt／updatedAtIso（兩邊執行時間本來就不同）。
"""
import json, sys
from pathlib import Path

SKIP = {"updatedAt", "updatedAtIso", "autofix", "autofix2"}


def same(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= 1e-9 * max(1, abs(a), abs(b))
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def diff_rows(name, built, db, lines, summary):
    bm = {r["c"]: r for r in built}
    dm = {r["c"]: r for r in db}
    only_b, only_d = sorted(set(bm) - set(dm)), sorted(set(dm) - set(bm))
    field_diffs = []
    for c in sorted(set(bm) & set(dm)):
        rb, rd = bm[c], dm[c]
        for k in sorted(set(rb) | set(rd)):
            if k in SKIP:
                continue
            if k == "t":
                tb, td = rb.get("t"), rd.get("t")
                if (tb is None) != (td is None):
                    field_diffs.append((c, rb.get("n"), "t", "有" if tb else "無", "有" if td else "無"))
                elif tb and td:
                    for kk in sorted(set(tb) | set(td)):
                        if not same(tb.get(kk), td.get(kk)):
                            field_diffs.append((c, rb.get("n"), "t." + kk, tb.get(kk), td.get(kk)))
                continue
            if not same(rb.get(k), rd.get(k)):
                field_diffs.append((c, rb.get("n"), k, rb.get(k), rd.get(k)))
    summary[name] = {"built": len(built), "db": len(db), "onlyBuilt": only_b, "onlyDb": only_d, "fieldDiffs": len(field_diffs),
                     "codesWithDiff": len({d[0] for d in field_diffs})}
    lines.append(f"### {name}：方案B {len(built)} 列／電腦版 {len(db)} 列；只在方案B {len(only_b)}、只在電腦版 {len(only_d)}、欄位差異 {len(field_diffs)} 處（{summary[name]['codesWithDiff']} 檔）")
    if only_b:
        lines.append("- 只在方案B：" + "、".join(f"{c} {bm[c].get('n')}" for c in only_b[:30]))
    if only_d:
        lines.append("- 只在電腦版：" + "、".join(f"{c} {dm[c].get('n')}" for c in only_d[:30]))
    if field_diffs:
        from collections import Counter
        byf = Counter(d[2] for d in field_diffs)
        lines.append("- 差異欄位統計：" + "、".join(f"{k}×{v}" for k, v in byf.most_common()))
        lines.append("")
        lines.append("| 代號 | 名稱 | 欄位 | 方案B | 電腦版 |")
        lines.append("|---|---|---|---|---|")
        for c, n, k, a, b in field_diffs[:80]:
            lines.append(f"| {c} | {n} | {k} | {a} | {b} |")
        if len(field_diffs) > 80:
            lines.append(f"（其餘 {len(field_diffs) - 80} 處略）")
    lines.append("")


def top20(rows):
    return [r["c"] for r in sorted((r for r in rows if r["v"] > 0 and r["amt"] >= 0.5), key=lambda r: -r["p"])[:20]]


def ftop20(rows, thr):
    return [r["c"] for r in sorted((r for r in rows if r["fv"] > 0 and r["amt"] >= thr), key=lambda r: -r["p"])[:20]]


def main():
    built_dir, db_dir, D = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    lines, summary = [f"## 方案B vs 電腦版 比對 {D}", ""], {}
    pairs = []
    for coll in ("days", "fdays"):
        bp, dp = built_dir / f"{coll}.json", db_dir / coll / f"{D}.json"
        if not bp.exists():
            lines.append(f"- {coll}：方案B沒有輸出")
            continue
        if not dp.exists():
            lines.append(f"- {coll}：db 沒有 {D} 文件（電腦版尚未寫入），無法比對")
            summary[coll] = {"dbMissing": True}
            continue
        pairs.append((coll, json.loads(bp.read_text(encoding="utf-8")), json.loads(dp.read_text(encoding="utf-8"))))
    for coll, b, d in pairs:
        # 頂層欄位
        top = []
        for k in sorted(set(b) | set(d)):
            if k in SKIP or k in ("rows", "tf", "find"):
                continue
            if not same(b.get(k), d.get(k)):
                top.append((k, b.get(k), d.get(k)))
        if top:
            lines.append(f"### {coll} 頂層欄位差異 {len(top)} 處")
            for k, a, bb in top:
                lines.append(f"- {k}：方案B＝{json.dumps(a, ensure_ascii=False)[:300]}；電腦版＝{json.dumps(bb, ensure_ascii=False)[:300]}")
            lines.append("")
        summary[coll + "_top"] = [t[0] for t in top]
        diff_rows(coll + " rows", b["rows"], d["rows"], lines, summary)
        if coll == "days":
            tb, td = top20(b["rows"]), top20(d["rows"])
            summary["top20Same"] = tb == td
            lines.append(f"### 投信買超前 20 名（v>0、amt≥0.5、p 排序）{'完全一致 ✅' if tb == td else '不一致 ❌'}")
            if tb != td:
                lines.append(f"- 方案B：{' '.join(tb)}")
                lines.append(f"- 電腦版：{' '.join(td)}")
            lines.append("")
        else:
            for thr, nm in ((1, "外資前20（amt≥1）"), (0.5, "外資前20（amt≥0.5）")):
                tb, td = ftop20(b["rows"], thr), ftop20(d["rows"], thr)
                summary[f"ftop20_{thr}"] = tb == td
                lines.append(f"### {nm} {'完全一致 ✅' if tb == td else '不一致 ❌'}")
                if tb != td:
                    lines.append(f"- 方案B：{' '.join(tb)}")
                    lines.append(f"- 電腦版：{' '.join(td)}")
            # tf、find
            tfb, tfd = b.get("tf") or {}, d.get("tf") or {}
            tfdiff = [(c, tfb.get(c), tfd.get(c)) for c in sorted(set(tfb) | set(tfd)) if tfb.get(c) != tfd.get(c)]
            summary["tfDiff"] = len(tfdiff)
            lines.append(f"### tf：方案B {len(tfb)}、電腦版 {len(tfd)}，差異 {len(tfdiff)} 檔" + ("" if not tfdiff else "：" + "、".join(f"{c} {a}→{bb}" for c, a, bb in tfdiff[:20])))
            fb, fd = b.get("find") or {}, d.get("find") or {}
            finddiff = [(k, fb.get(k), fd.get(k)) for k in sorted(set(fb) | set(fd)) if not same(fb.get(k), fd.get(k))]
            summary["findDiff"] = len(finddiff)
            lines.append(f"### find 產業彙總：方案B {len(fb)} 類、電腦版 {len(fd)} 類，差異 {len(finddiff)} 類")
            for k, a, bb in finddiff[:40]:
                lines.append(f"- {k}：方案B＝{a}；電腦版＝{bb}")
            lines.append("")
    ok = all(not v.get("onlyBuilt") and not v.get("onlyDb") and not v.get("fieldDiffs") for k, v in summary.items() if isinstance(v, dict) and "built" in v) \
        and summary.get("top20Same", True) and not summary.get("tfDiff") and not summary.get("findDiff") and not any(summary.get(k) for k in summary if k.endswith("_top"))
    summary["allSame"] = ok
    lines.insert(2, "**結論：" + ("完全一致 ✅" if ok else "有差異，見下表") + "**")
    lines.insert(3, "")
    md = "\n".join(lines)
    (built_dir / "compare.md").write_text(md, encoding="utf-8")
    (built_dir / "compare.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
