"""「投信＋外資買超佔股本 每日更新」主排程 方案B：把 daily_fetch.py 的原始資料算成 db 的 days／fdays 文件。

在 claude.ai 雲端排程執行（不在 GitHub Actions），觸發價／停損等技術欄位只在這裡產生、不進 repo。
用法：python itrust/daily_build.py <raw.json> <out_dir> [db_dir]
  db_dir：ArtifactData 下載的 db 副本（需要 meta/industry.json；沒有就只用 t187 的產業別）
輸出：<out_dir>/days.json、fdays.json、industry.json（產業對照有變才寫）、report.json
計算口徑與電腦版（內建瀏覽器＋javascript techCalc）完全相同：
  half-up 四捨五入（Decimal ROUND_HALF_UP，負數遠離 0）；技術欄位的 r2＝JS Math.round(x*100+EPS*sign)/100。
"""
import json, math, re, sys, datetime as dt
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

EPS = 2.0 ** -52
NA_T = {"na": "上市櫃未滿 21 個交易日或資料不足"}


def half_up(x, nd=0):
    q = Decimal(1).scaleb(-nd)
    v = Decimal(str(x)).quantize(q, rounding=ROUND_HALF_UP)
    if nd == 0:
        return int(v)
    f = float(v)
    return 0 if f == 0 else f  # -0.0 → 0


def js_round(v):
    f = math.floor(v)
    return f + 1 if v - f >= 0.5 else f


def r2(x):
    return js_round(x * 100 + EPS * (1 if x >= 0 else -1)) / 100


def clean(x):
    if isinstance(x, float):
        if x != x:
            return None
        if x.is_integer():
            return int(x)
    return x


def nan(x):
    return float("nan") if x is None else x


def roc_norm(s):
    """'1151020' 或 '115/10/20' → '115/10/20'。"""
    s = str(s or "").strip()
    m = re.match(r"^(\d{3})(\d{2})(\d{2})$", s)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
    return s


def tech_calc(bars_by_code, ex, D):
    """逐字移植頁面／電腦版的 javascript techCalc。bars: [[d,o,h,l,c],…]，ex: [[code,d,pre,ref],…]（API 順序）。"""
    out = {}
    for code, bars in bars_by_code.items():
        b = [{"d": x[0], "o": nan(x[1]), "h": nan(x[2]), "l": nan(x[3]), "c": nan(x[4])} for x in sorted(bars, key=lambda x: x[0])]
        if not b or b[-1]["d"] != D:
            continue
        adj = False
        for e in ex:
            if e[0] != code:
                continue
            pre, ref = nan(e[2]), nan(e[3])
            f = ref / pre if pre else float("nan")
            if not (f > 0) or f == 1:
                continue
            for x in b:
                if x["d"] < e[1]:
                    x["o"] *= f
                    x["h"] *= f
                    x["l"] *= f
                    x["c"] *= f
                    adj = True
        n = len(b)
        if n < 21:
            continue
        C = [x["c"] for x in b]

        def ma(k, off=0):
            s = 0.0
            for v in C[n - off - k: n - off]:
                s = s + v
            return s / k

        ma5, ma10, ma20, ma20p = ma(5), ma(10), ma(20), ma(20, 1)
        trig = max(x["h"] for x in b[-20:])
        piv = []
        for i in range(2, n - 2):
            L = b[i]["l"]
            if L < b[i - 1]["l"] and L < b[i - 2]["l"] and L <= b[i + 1]["l"] and L <= b[i + 2]["l"]:
                piv.append(i)
        p1 = piv[-1] if len(piv) >= 1 else None
        p0 = piv[-2] if len(piv) >= 2 else None
        sl = b[p1]["l"] if p1 is not None else None
        sl0 = b[p0]["l"] if p0 is not None else None
        c = C[-1]
        t = {"n": n, "adj": adj, "c": r2(c), "ma5": r2(ma5), "ma10": r2(ma10), "ma20": r2(ma20), "ma20p": r2(ma20p),
             "trig": r2(trig), "sl": None if sl is None else r2(sl), "slD": b[p1]["d"] if p1 is not None else None,
             "sl0": None if sl0 is None else r2(sl0), "sl0D": b[p0]["d"] if p0 is not None else None,
             "slPct": None if sl is None else r2((trig - sl) / trig * 100), "bias": r2((c - ma20) / ma20 * 100)}
        t["bull"] = t["ma5"] > t["ma10"] > t["ma20"]
        t["up"] = t["ma20"] > t["ma20p"]
        t["hl"] = t["sl"] is not None and t["sl0"] is not None and t["sl"] > t["sl0"]
        t["brk"] = t["sl"] is not None and t["c"] < t["sl"]
        out[code] = {k: clean(v) for k, v in t.items()}
    return out


def build(raw, dbmap, names, now=None):
    D = raw["D"]
    report = {"D": D, "excluded": [], "warnings": [], "mopsFixed": [], "industryChanged": [], "newIndustryCodes": []}
    if not raw.get("open"):
        report["warnings"].append("休市或資料未發布：" + str(raw.get("reason")))
        return None, None, None, report
    now = now or dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    P4 = raw["p4"]
    tw, tp = raw["twse"], raw["tpex"]
    tpex_ok = bool(tp.get("daily"))

    # ── 產業對照：db map ＋ t187（新增／變動以 t187 為準）
    ind_map = dict(dbmap or {})
    for src in (tw.get("t187") or [], tp.get("t187") or []):
        for code, _sm, _priv, ind, _base in src:
            if not ind:
                continue
            if ind_map.get(code) != ind:
                report["industryChanged"].append([code, ind_map.get(code), ind])
                ind_map[code] = ind
            if names is not None and ind not in names and ind not in report["newIndustryCodes"]:
                report["newIndustryCodes"].append(ind)

    def ind_of(code):
        return ind_map.get(code) or "99"

    # ── 各市場原始表 → dict
    def market_tables(mk):
        if mk == "twse":
            rows = tw["t86"]["rows"]
            px = {r[0]: (r[1], r[2]) for r in tw["px"]["rows"]}                       # cl, chg
            shares = {r[0]: (r[1], r[2], r[3]) for r in tw["qfiis"]["rows"]}         # s, rm, hp
            sx = tw["qfiis"]["date"]
            t187 = {r[0]: r for r in tw.get("t187") or []}
            punish, fd = tw.get("punish") or [], set(tw.get("fd") or [])
            prev, ohlc, ex = tw.get("prev") or {}, tw.get("ohlc") or {}, tw.get("ex") or []
            t86rows = tw["t86"]["t86Rows"]
        else:
            rows = tp["daily"]["rows"]
            px = {r[0]: (r[1], r[2]) for r in tp["px"]["rows"]}
            q = {r[0]: (r[1], r[2]) for r in (tp.get("qfii") or {}).get("rows") or []}  # rm, hp
            shares = {r[0]: (r[6], q.get(r[0], (None, None))[0], q.get(r[0], (None, None))[1]) for r in tp["px"]["rows"]}
            sx = tp["px"]["date"]
            t187 = {r[0]: r for r in tp.get("t187") or []}
            punish, fd = tp.get("punish") or [], set(tp.get("fd") or [])
            prev, ohlc, ex = tp.get("prev") or {}, tp.get("ohlc") or {}, tp.get("ex") or []
            t86rows = tp["daily"]["t86Rows"]
        dp = {c for c, a, b in punish if a <= D <= b}
        tech = tech_calc(ohlc, ex, D)
        return rows, px, shares, sx, t187, dp, fd, prev, tech, t86rows

    mops = raw.get("mops") or {}
    days_rows, f_rows_buy, f_rows_sell, tf, counts, fcounts, sxDate, bases = [], [], [], {}, {}, {}, {}, {}
    find_raw = {}
    for mk, label in (("twse", "上市"), ("tpex", "上櫃")):
        if mk == "tpex" and not tpex_ok:
            continue
        rows, px, shares, sx, t187, dp, fd, prev, tech, t86rows = market_tables(mk)
        sxDate[mk] = sx
        # 觀測站出表日期（取最多數）
        base_cnt = {}
        for r in t187.values():
            base_cnt[roc_norm(r[4])] = base_cnt.get(roc_norm(r[4]), 0) + 1
        bases[mk] = max(base_cnt, key=base_cnt.get) if base_cnt else ""
        stocks = len(rows)
        tb = sum(1 for r in rows if r[3] > 0)
        ts = sum(1 for r in rows if r[3] < 0)
        counts[mk] = {"t86Rows": t86rows, "stocks": stocks, "trustBuy": tb, "trustSell": ts, "trustZero": stocks - tb - ts}
        fb = sum(1 for r in rows if r[2] > 0)
        fs = sum(1 for r in rows if r[2] < 0)
        fcounts[mk] = {"stocks": stocks, "foreignBuy": fb, "foreignSell": fs, "foreignZero": stocks - fb - fs}
        for code, name_raw, fv, v in rows:
            n = re.sub(r"[\s*]", "", name_raw)
            par = "*" in name_raw
            s, rm, hp = shares.get(code, (None, None, None))
            cl, chg = px.get(code, (None, None))
            t187r = t187.get(code)
            # 投信列
            if v != 0:
                tf[code] = fv
                sm = t187r[1] if t187r else None
                if s is None or sm is None or cl is None:
                    report["excluded"].append([code, n, label, "缺" + "/".join(k for k, x in (("s", s), ("sm", sm), ("cl", cl)) if x is None)])
                else:
                    priv = t187r[2] or 0
                    mp = mops.get(code) if (v > 0 and s != sm) else None   # 步驟 7 只查投信買超且 s≠sm 的公司
                    cb = bool(mp.get("cb")) if (mp and mp.get("cb") is not None) else False
                    if mp and mp.get("sm") is not None and mp["sm"] != sm:
                        report["mopsFixed"].append([code, n, sm, mp["sm"]])
                        sm = mp["sm"]
                    lots = half_up(v / 1000)
                    row = {"c": code, "n": n, "m": label, "v": v, "lots": lots, "s": s, "sm": sm, "smBase": roc_norm(t187r[4]), "priv": priv,
                           "cl": cl, "chg": chg, "p": half_up(v / s * 100, 4), "amt": half_up(lots * 1000 * cl / 1e8, 2),
                           "sdiff": half_up(abs(s - sm) / s * 100, 2), "cb": cb, "par": par, "dp": code in dp, "fd": code in fd}
                    if s != sm:
                        row["why"] = "priv" if sm - priv == s else ("up" if s > sm else "down")
                    if v > 0:
                        row["t"] = tech.get(code) or dict(NA_T)
                    days_rows.append(row)
            # 外資產業彙總（全市場 fv≠0）
            if fv != 0:
                ind = ind_of(code)
                lots = half_up(fv / 1000)
                rawv = lots * 1000 * js_round(cl * 100) if (cl is not None and cl > 0) else 0
                acc = find_raw.setdefault(ind, [0, 0, 0, 0])
                if fv > 0:
                    acc[0] += rawv
                    acc[2] += 1
                else:
                    acc[1] += rawv
                    acc[3] += 1
            # 外資全行列
            if fv != 0 and s is not None and cl is not None:
                lots = half_up(fv / 1000)
                amt = half_up(lots * 1000 * cl / 1e8, 2)
                if abs(amt) >= 0.5:
                    f4 = [next((r[1] for r in prev.get(d, []) if r[0] == code), 0) for d in P4]
                    frow = {"c": code, "n": n, "m": label, "fv": fv, "lots": lots, "s": s, "cl": cl, "chg": chg,
                            "p": half_up(fv / s * 100, 4), "amt": amt, "hp": hp, "rm": rm, "dp": code in dp, "fd": code in fd, "par": par, "f4": f4}
                    if fv > 0:
                        frow["t"] = tech.get(code) or dict(NA_T)
                        f_rows_buy.append(frow)
                    else:
                        f_rows_sell.append(frow)
    # 排序
    days_rows.sort(key=lambda r: -r["p"])
    f_rows_buy.sort(key=lambda r: -r["p"])
    f_rows_sell.sort(key=lambda r: r["p"])
    find = {ind: {"b": half_up(a[0] / 1e10, 2), "s": half_up(a[1] / 1e10, 2), "nb": a[2], "ns": a[3]} for ind, a in find_raw.items()}

    # ── 完整性檢查
    for mk in counts:
        c = counts[mk]
        assert c["trustBuy"] + c["trustSell"] + c["trustZero"] == c["stocks"], mk
        fc = fcounts[mk]
        assert fc["foreignBuy"] + fc["foreignSell"] + fc["foreignZero"] == fc["stocks"], mk
        got = sum(1 for r in days_rows if r["m"] == ("上市" if mk == "twse" else "上櫃"))
        exc = sum(1 for e in report["excluded"] if e[2] == ("上市" if mk == "twse" else "上櫃"))
        assert got + exc == c["trustBuy"] + c["trustSell"], f"{mk} rows {got}+{exc} ≠ {c['trustBuy'] + c['trustSell']}"
    assert set(tf) >= {r["c"] for r in days_rows}, "tf 代號集合"
    assert sum(v["nb"] for v in find.values()) == sum(fc["foreignBuy"] for fc in fcounts.values()), "find nb"
    assert sum(v["ns"] for v in find.values()) == sum(fc["foreignSell"] for fc in fcounts.values()), "find ns"
    for r in days_rows + f_rows_buy + f_rows_sell:
        assert "chg" in r, r["c"]
    # 被剔除的列也要從 tf 拿掉（tf 代號集合＝days rows 代號集合）
    tf = {r["c"]: tf[r["c"]] for r in days_rows}

    # ── 文件
    sx_tw = sxDate.get("twse")
    notes = []
    shares_basis = ("佔股本分母＝交易所／櫃買當日掛牌股數（上市：證交所外資及陸資投資持股統計「發行股數」；上櫃：櫃買收盤行情「發行股數」）。"
                    f"對照欄＝公開資訊觀測站已發行普通股數（上市 {bases.get('twse', '')}、上櫃 {bases.get('tpex', '')} 出表）。差異率＝|掛牌−觀測站|÷掛牌。")
    if sx_tw != D:
        shares_basis += f"上市掛牌股數因證交所當日尚未發布，暫用 {sx_tw[:4]}/{sx_tw[4:6]}/{sx_tw[6:]} 資料。"
        notes.append(f"上市掛牌股數暫用 {sx_tw} 資料")
    if not tpex_ok:
        notes.append("上櫃未更新")
    amt_rule = "張數＝股數÷1000 四捨五入成整數；金額＝張數×1000×收盤價÷1e8，四捨五入到小數第2位"
    tech_basis = ("技術欄位以 D 日收盤後資料計算：近 40 個交易日日K（證交所 MI_INDEX／櫃買收盤行情），除權息日之前的價格依「參考價÷前收盤」向前還原（證交所 TWT49U、櫃買 exDailyQ）。"
                  "5/10/20MA＝收盤平均；20MA上揚＝今日20MA＞昨日20MA；觸發價＝近20日最高價；波段低點＝前後各2日的最低點（需右側2日確認）；停損＝最近一個波段低點；"
                  "底底高＝最近波段低點＞前一個波段低點；停損%＝(觸發價−停損)÷觸發價；乖離＝(收盤−20MA)÷20MA。")
    upd, upd_iso = now.strftime("%Y/%m/%d %H:%M"), now.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    days = {"id": D, "updatedAt": upd, "updatedAtIso": upd_iso, "counts": counts, "sxDate": sxDate,
            "rowsScope": "全市場普通股中，投信買賣超不為 0 的全部個股（含賣超，v 為負值）", "sharesBasis": shares_basis, "amtRule": amt_rule,
            "techDate": D, "techBasis": tech_basis, "rows": days_rows}
    fdays = {"id": D, "updatedAt": upd, "updatedAtIso": upd_iso, "counts": fcounts, "sxDate": sxDate,
             "def": "外資＝外陸資買賣超（不含外資自營商）：上市取證交所三大法人買賣超日報 T86「外陸資買賣超股數(不含外資自營商)」；上櫃取櫃買三大法人買賣明細「外資及陸資(不含外資自營商)買賣超股數」。",
             "rowsScope": "全市場普通股中，外資買超或賣超金額 ≥0.5 億的個股（賣超 fv 為負值）；f4＝前 4 個交易日外資買賣超股數（由舊到新），用來算近5日累計；tf＝當天投信有買賣超個股的外資買賣超股數，用來算土洋同買／同賣；find＝外資各產業買超金額 b、賣超金額 s（億，全市場普通股）與買超家數 nb、賣超家數 ns。",
             "indBasis": "產業別：上市取證交所 t187ap03_L「產業別」，上櫃取櫃買 mopsfin_t187ap03_O「SecuritiesIndustryCode」；各股金額＝張數×1000×收盤價，加總後換算成億。",
             "sharesBasis": "佔股本分母＝交易所／櫃買當日掛牌股數（與投信相同）。",
             "holdBasis": "外資持股比率、尚可投資比率：上市取證交所外資及陸資投資持股統計（MI_QFIIS），上櫃取櫃買僑外資及陸資持股比例排行表。",
             "amtRule": amt_rule, "techDate": D, "techBasis": "同投信。", "rows": f_rows_buy + f_rows_sell, "tf": tf, "find": find}
    if notes:
        days["note"] = fdays["note"] = "；".join(notes)
    industry = None
    if report["industryChanged"]:
        industry = {"map": ind_map, "updatedAt": now.strftime("%Y/%m/%d")}
    report["counts"], report["fcounts"] = counts, fcounts
    report["rows"] = {"days": len(days_rows), "fbuy": len(f_rows_buy), "fsell": len(f_rows_sell), "tf": len(tf), "find": len(find),
                      "techMissing": [r["c"] for r in days_rows + f_rows_buy if r.get("t", {}).get("na")]}
    return days, fdays, industry, report


def main():
    raw_p, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    db_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    raw = json.loads(raw_p.read_text(encoding="utf-8"))
    dbmap, names = {}, None
    if db_dir and (db_dir / "meta" / "industry.json").exists():
        ind = json.loads((db_dir / "meta" / "industry.json").read_text(encoding="utf-8"))
        dbmap, names = ind.get("map") or {}, ind.get("names") or {}
    days, fdays, industry, report = build(raw, dbmap, names)
    out_dir.mkdir(parents=True, exist_ok=True)
    dump = lambda name, obj: (out_dir / name).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if days:
        dump("days.json", days)
        dump("fdays.json", fdays)
    if industry:
        dump("industry.json", industry)
    dump("report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__":
    main()
