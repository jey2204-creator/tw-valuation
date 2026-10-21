"""主排程 方案B 步驟 13：用 GitHub Actions 重抓的前 4 個交易日法人資料，核對並更正 db 裡「最新 2 份」days／fdays 文件。

用法：python itrust/daily_prevcheck.py <raw.json> <db_dir> <out_dir>
  db_dir：ArtifactData 下載的 db 副本（days/<d>.json、fdays/<d>.json；要核對的 2 份＝id＜D 的最新 2 份）
輸出：<out_dir>/prev/<d>.days.json、<d>.fdays.json（只有需要更正的才輸出，整份文件、已含 autofix 欄位）、prev_report.json；stdout 印摘要。
規則（與電腦版相同）：
  - 投信：v 不同就更新 v、lots、p、amt；由賣轉買補 t（有該檔日K就用 d 當天以前的 40 根算，沒有就 {"na":…}），由買轉賣刪 t；
    代號集合不同（多或少一檔）不自動補，只回報；重算 trustBuy／trustSell／trustZero；rows 依 p 重排。
  - 外資：更新全行列的 fv、lots、p、amt 與 tf 的值；用重抓的全市場 fv 與該日收盤重算 find；全行列成員變動只回報。
  - 文件加 "autofix": "YYYY/MM/DD HH:MM 自動核對更正 N 檔：代號 名稱 舊→新、…"。
"""
import json, sys, datetime as dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from daily_build import half_up, js_round, tech_calc, NA_T  # noqa: E402


def H(pairs):
    return sum(v * (int(c) % 97) for c, v in pairs)


def check_day(d, raw, days, fdays, now):
    rep = {"d": d, "twse": {}, "tpex": {}, "fixes": [], "ffixes": [], "warnings": []}
    changed, fchanged = False, False
    D = raw["D"]
    for mk, label in (("twse", "上市"), ("tpex", "上櫃")):
        prev = (raw[mk].get("prev") or {}).get(d)
        if prev is None:
            rep["warnings"].append(f"{label} {d} 原始資料未涵蓋，跳過")
            continue
        raw_v = {c: v for c, fv, v in prev if v != 0}
        raw_fv = {c: fv for c, fv, v in prev}
        db_rows = [r for r in days["rows"] if r["m"] == label]
        db_v = {r["c"]: r["v"] for r in db_rows}
        m = {"rawN": len(raw_v), "rawSum": sum(raw_v.values()), "rawHv": H(raw_v.items()),
             "dbN": len(db_v), "dbSum": sum(db_v.values()), "dbHv": H(db_v.items())}
        rep[mk] = m
        if set(raw_v) != set(db_v):
            rep["warnings"].append(f"{label} 投信代號集合不同：只在原始 {sorted(set(raw_v) - set(db_v))}，只在 db {sorted(set(db_v) - set(raw_v))}（不自動增刪）")
        mk_changed = False
        for r in db_rows:
            c = r["c"]
            if c not in raw_v or raw_v[c] == r["v"]:
                continue
            old, new = r["v"], raw_v[c]
            mk_changed = True
            r["v"] = new
            r["lots"] = half_up(new / 1000)
            r["p"] = half_up(new / r["s"] * 100, 4)
            r["amt"] = half_up(r["lots"] * 1000 * r["cl"] / 1e8, 2)
            if old < 0 < new:
                if "t" not in r:
                    bars = [b for b in (raw[mk].get("ohlc") or {}).get(c, []) if b[0] <= d]
                    ex = [e for e in raw[mk].get("ex") or [] if e[1] <= d]
                    r["t"] = tech_calc({c: bars}, ex, d).get(c) or dict(NA_T)
            elif new < 0:
                r.pop("t", None)
            rep["fixes"].append([c, r["n"], old, new])
            changed = True
        if mk_changed:
            cnt = days["counts"][mk]
            cnt["trustBuy"] = sum(1 for r in db_rows if r["v"] > 0)
            cnt["trustSell"] = sum(1 for r in db_rows if r["v"] < 0)
            cnt["trustZero"] = cnt["stocks"] - cnt["trustBuy"] - cnt["trustSell"]
        # 外資
        if fdays:
            frows = [r for r in fdays["rows"] if r["m"] == label]
            fm = {"dbHfv": H((r["c"], r["fv"]) for r in frows), "rawHfv": H((r["c"], raw_fv.get(r["c"], 0)) for r in frows)}
            m.update(fm)
            for r in frows:
                c = r["c"]
                if c not in raw_fv or raw_fv[c] == r["fv"]:
                    continue
                old, new = r["fv"], raw_fv[c]
                r["fv"] = new
                r["lots"] = half_up(new / 1000)
                r["p"] = half_up(new / r["s"] * 100, 4)
                r["amt"] = half_up(r["lots"] * 1000 * r["cl"] / 1e8, 2)
                if (old > 0) != (new > 0):
                    rep["warnings"].append(f"{label} {c} {r['n']} 外資由{'買' if old > 0 else '賣'}轉{'買' if new > 0 else '賣'}，t 欄位未重算")
                if abs(r["amt"]) < 0.5:
                    rep["warnings"].append(f"{label} {c} {r['n']} 更正後金額 {r['amt']} 已低於 0.5 億（成員未自動增刪）")
                rep["ffixes"].append([c, r["n"], old, new])
                fchanged = True
            tf = fdays.get("tf") or {}
            for c in list(tf):
                if c in raw_fv and raw_fv[c] != tf[c] and (c in {r["c"] for r in db_rows}):
                    rep["ffixes"].append([c, "tf", tf[c], raw_fv[c]])
                    tf[c] = raw_fv[c]
                    fchanged = True
    # 重算 find（兩市場合併；需要該日全市場收盤）
    if fdays and fchanged:
        ind_map = raw.get("_industry_map") or {}
        pxp = {mk: (raw[mk].get("px_prev") or {}).get(d) for mk in ("twse", "tpex")}
        if all(pxp.get(mk) is not None for mk in ("twse", "tpex") if (raw[mk].get("prev") or {}).get(d) is not None):
            acc = {}
            for mk in ("twse", "tpex"):
                prev = (raw[mk].get("prev") or {}).get(d) or []
                cl_map = pxp.get(mk) or {}
                for c, fv, _v in prev:
                    if fv == 0:
                        continue
                    ind = ind_map.get(c) or "99"
                    lots = half_up(fv / 1000)
                    cl = cl_map.get(c)
                    rawv = lots * 1000 * js_round(cl * 100) if (cl is not None and cl > 0) else 0
                    a = acc.setdefault(ind, [0, 0, 0, 0])
                    if fv > 0:
                        a[0] += rawv
                        a[2] += 1
                    else:
                        a[1] += rawv
                        a[3] += 1
            fdays["find"] = {ind: {"b": half_up(a[0] / 1e10, 2), "s": half_up(a[1] / 1e10, 2), "nb": a[2], "ns": a[3]} for ind, a in acc.items()}
        else:
            rep["warnings"].append(f"{d} 缺全市場收盤，find 未重算")
    if changed:
        days["rows"].sort(key=lambda r: -r["p"])
        days["autofix"] = f"{now} 自動核對更正 {len(rep['fixes'])} 檔：" + "、".join(f"{c} {n} {o}→{nw}" for c, n, o, nw in rep["fixes"])
    if fchanged:
        fdays["rows"].sort(key=lambda r: (r["fv"] < 0, -r["p"] if r["fv"] > 0 else r["p"]))
        fdays["autofix"] = f"{now} 自動核對更正 {len(rep['ffixes'])} 檔：" + "、".join(f"{c} {n} {o}→{nw}" for c, n, o, nw in rep["ffixes"])
    rep["changed"], rep["fchanged"] = changed, fchanged
    return rep


def main():
    raw_p, db_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    raw = json.loads(raw_p.read_text(encoding="utf-8"))
    D = raw["D"]
    ind_p = db_dir / "meta" / "industry.json"
    if ind_p.exists():
        raw["_industry_map"] = (json.loads(ind_p.read_text(encoding="utf-8")).get("map") or {})
    ids = sorted(p.stem for p in (db_dir / "days").glob("*.json") if p.stem < D)[-2:]
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y/%m/%d %H:%M")
    (out_dir / "prev").mkdir(parents=True, exist_ok=True)
    reports = []
    for d in ids:
        days = json.loads((db_dir / "days" / f"{d}.json").read_text(encoding="utf-8"))
        fp = db_dir / "fdays" / f"{d}.json"
        fdays = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else None
        rep = check_day(d, raw, days, fdays, now)
        if rep["changed"]:
            (out_dir / "prev" / f"{d}.days.json").write_text(json.dumps(days, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        if rep["fchanged"]:
            (out_dir / "prev" / f"{d}.fdays.json").write_text(json.dumps(fdays, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        reports.append(rep)
        ok = not rep["changed"] and not rep["fchanged"] and not rep["warnings"]
        print(f"{d}：{'OK' if ok else ''}" + ("" if ok else f" 投信更正 {len(rep['fixes'])}、外資更正 {len(rep['ffixes'])}、警告 {len(rep['warnings'])}"))
        for w in rep["warnings"]:
            print("  ⚠", w)
        for c, n, o, nw in rep["fixes"] + rep["ffixes"]:
            print(f"  {c} {n} {o}→{nw}")
    (out_dir / "prev_report.json").write_text(json.dumps(reports, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
