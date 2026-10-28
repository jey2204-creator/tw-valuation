"""個股逐日籌碼（類主力）：三大法人（外資／投信／自營商）＋融資融券 → data/chip.json

免費替代「主力買賣超」：券商分點資料要付費，這裡只用證交所／櫃買公開資料。
來源（可指定日期查歷史）：
  上市三大法人  www.twse.com.tw/rwd/zh/fund/T86
  上櫃三大法人  www.tpex.org.tw/www/zh-tw/insti/dailyTrade
  上市融資融券  www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN
  上櫃融資融券  www.tpex.org.tw/www/zh-tw/margin/balance（舊版 php 備援，會核對回應日期）

交易日清單沿用 fetch_momentum.py 的 data/hist（要在它之後執行）。
每個交易日一個檔 data/chip/YYYYMMDD.json = {"src":[...], "i":{代號:[外資,投信,自營商]}(股), "m":{代號:[融資增減,融券增減,融資餘額]}(張)}
輸出 data/chip.json：只放 themes.json 成份股＋EXTRA（全市場每天約 2,000 檔，全放會太大）
  days = [YYYYMMDD…]（舊→新）
  d[代號] = 每天一列 [收盤, 成交張數, 外資張, 投信張, 自營張, 融資增減張, 融券增減張, 融資餘額張]，缺資料為 null
另輸出全市場分片 data/chip_s/NN.json（NN = 代號前兩碼，約 70 個檔）：{days, d:{代號:[同上列 + 開, 高, 低]}}，價格 130 天、籌碼 60 天
  個股頁先查 chip.json，沒有再抓對應分片 → 任何上市櫃股票都看得到逐日籌碼（2026/10/27 起）
用法：python fetch_chip.py
"""
import json, sys, time, datetime as dt
from pathlib import Path
import urllib.parse
import fetch_momentum as fm                     # 共用節流 get()、欄位工具

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data"
HIST = OUT / "hist"
CHIP = OUT / "chip"
NDAYS = 60                                      # 籌碼圖顯示幾個交易日
KDAYS = 130                                     # K 線分片保留幾個交易日（120 日均線）
EXTRA = ["2467"]                                # 主題以外也想看的股票（志聖）
MAX_REQ = 200
BUDGET = 13 * 60
T0 = time.time()
diag, fails = {}, {}


def note(k, fields, n, extra=None):
    d = diag.setdefault(k, {})
    d["rows"] = n
    if fields:
        d["fields"] = [str(f) for f in fields][:26]
    if extra:
        d.update(extra)


# ---------- 三大法人 ----------
def twse_inst(d):
    js = fm.get(f"https://www.twse.com.tw/rwd/zh/fund/T86?date={d:%Y%m%d}&selectType=ALLBUT0999&response=json", "twse")
    for fields, rows in fm.tables_of(js):
        fs = [str(f) for f in fields]
        ic = fm.col(fs, "證券代號")
        jf = fm.col(fs, "外", "買賣超", prefer="不含")
        jt = fm.col(fs, "投信", "買賣超")
        jd = next((i for i, f in enumerate(fs) if f == "自營商買賣超股數"), None)
        ja = fm.col(fs, "三大法人買賣超")
        if None in (ic, jf, jt) or (jd is None and ja is None):
            continue
        out = {}
        for r in rows:
            c = fm.ok_code(r[ic])
            if not c:
                continue
            f_, t_ = fm.num(r[jf]) or 0, fm.num(r[jt]) or 0
            if jd is not None:
                dl = fm.num(r[jd]) or 0
            else:                                         # 沒有自營商合計欄 → 三大合計 − 外資(含自營) − 投信
                dl = (fm.num(r[ja]) or 0) - f_ - t_
            out[c] = [f_, t_, dl]
        note("iL", fields, len(out))
        return out or None
    note("iL", [], 0)
    return None


def tpex_inst(d):
    u = f"https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade?type=Daily&sect=EW&date={d:%Y}%2F{d:%m}%2F{d:%d}&response=json"
    js = fm.get(u, "tpex")
    rd = fm.resp_date(js)
    if rd is not None and rd != d:
        note("iO", [], 0, {"date": str(rd)})
        return None
    for fields, rows in fm.tables_of(js):
        if fields and len(fields) < 24:
            continue
        # 欄位（0 起算）：0 代號、4 外資(不含自營)買賣超、10 外資合計買賣超、13 投信買賣超、22 自營商合計買賣超、23 三大法人合計
        out = {}
        for r in rows:
            c = fm.ok_code(r[0])
            if not c or len(r) < 24:
                continue
            f_, fa, t_, a = fm.num(r[4]) or 0, fm.num(r[10]) or 0, fm.num(r[13]) or 0, fm.num(r[23]) or 0
            out[c] = [f_, t_, a - fa - t_]                 # 自營商 = 三大合計 − 外資合計 − 投信（不受欄位位置變動影響）
        if out:
            note("iO", fields, len(out))
            return out
    note("iO", [], 0)
    return None


# ---------- 融資融券 ----------
def twse_margin(d):
    js = fm.get(f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={d:%Y%m%d}&selectType=ALL&response=json", "twse")
    for fields, rows in fm.tables_of(js):
        fs = [str(f) for f in fields]
        ic = fm.col(fs, "代號")
        prev = [i for i, f in enumerate(fs) if "前日餘額" in f]
        now = [i for i, f in enumerate(fs) if "今日餘額" in f]
        if ic is None:
            continue
        if len(prev) >= 2 and len(now) >= 2:
            p1, n1, p2, n2 = prev[0], now[0], prev[1], now[1]
        elif len(fs) >= 13 and not prev:
            p1, n1, p2, n2 = 5, 6, 11, 12
        else:
            continue
        out = {}
        for r in rows:
            c = fm.ok_code(r[ic])
            if not c or len(r) <= n2:
                continue
            a, b, x, y = (fm.num(r[k]) for k in (p1, n1, p2, n2))
            if b is None:
                continue
            out[c] = [b - (a or 0), (y or 0) - (x or 0), b]
        if out:
            note("mL", fields, len(out), {"cols": [p1, n1, p2, n2]})
            return out
    note("mL", [], 0, {"stat": str(js.get("stat", ""))[:40] if isinstance(js, dict) else ""})
    return None


def tpex_margin(d):
    roc = f"{d.year - 1911}/{d:%m/%d}"
    urls = [f"https://www.tpex.org.tw/www/zh-tw/margin/balance?date={d:%Y}%2F{d:%m}%2F{d:%d}&id=&response=json",
            f"https://www.tpex.org.tw/web/stock/margin_trading/margin_balance/margin_bal_result.php?l=zh-tw&o=json&d={urllib.parse.quote(roc)}"]
    err = None
    for u in urls:
        try:
            js = fm.get(u, "tpex")
        except Exception as e:
            err = e
            continue
        rd = fm.resp_date(js)
        diag.setdefault("mO_dates", []).append(f"{d:%m%d}->{rd:%m%d}" if rd else f"{d:%m%d}->?")
        if rd != d:                                       # 舊版會忽略日期參數 → 日期不符不採用
            continue
        for fields, rows in fm.tables_of(js):
            fs = [str(f) for f in fields]
            # 新版欄名：前資餘額、資餘額、前券餘額、券餘額；舊版 aaData 依位置：2 前資餘額、6 資餘額、10 前券餘額、14 券餘額
            def f_(key, avoid=None):
                return next((i for i, f in enumerate(fs) if key in f and not (avoid and avoid in f)), None)
            if fs:
                p1, n1 = f_("前資餘額"), f_("資餘額", "前")
                p2, n2 = f_("前券餘額"), f_("券餘額", "前")
                if None in (p1, n1, p2, n2):
                    if len(fs) >= 15:
                        p1, n1, p2, n2 = 2, 6, 10, 14
                    else:
                        continue
            else:
                p1, n1, p2, n2 = 2, 6, 10, 14
            out = {}
            for r in rows:
                c = fm.ok_code(r[0])
                if not c or len(r) <= n2:
                    continue
                a, b, x, y = (fm.num(r[k]) for k in (p1, n1, p2, n2))
                if b is None:
                    continue
                out[c] = [b - (a or 0), (y or 0) - (x or 0), b]
            if out:
                note("mO", fields, len(out), {"cols": [p1, n1, p2, n2], "url": u.split("?")[0][-40:]})
                return out
        note("mO", [], 0)
    if err:
        raise err
    return None


SOURCES = {"iL": (twse_inst, "i"), "iO": (tpex_inst, "i"), "mL": (twse_margin, "m"), "mO": (tpex_margin, "m")}


def trade_days(n=NDAYS):
    """data/hist 裡有上市收盤的交易日（舊→新）"""
    out = []
    for f in sorted(HIST.glob("*.json")):
        try:
            rec = json.loads(f.read_text("utf-8"))
        except Exception:
            continue
        if not rec.get("closed") and "pL" in rec.get("src", []):
            out.append((f.stem, rec))
    return out[-n:]


def load(day):
    f = CHIP / f"{day}.json"
    if f.exists():
        try:
            return json.loads(f.read_text("utf-8"))
        except Exception:
            pass
    return {}


def collect(days):
    CHIP.mkdir(parents=True, exist_ok=True)
    errs = []
    now = dt.datetime.utcnow() + dt.timedelta(hours=8)
    for day, _ in reversed(days):                         # 新的先抓
        d = dt.date(int(day[:4]), int(day[4:6]), int(day[6:]))
        rec = load(day)
        src = set(rec.get("src", []))
        changed = False
        for k, (fn, slot) in SOURCES.items():
            if k in src or fails.get(k, 0) >= 3:
                continue
            if k.startswith("m") and d == now.date() and now.hour < 21:   # 融資券約晚上 9 點後才公布
                continue
            if fm.nreq >= MAX_REQ or time.time() - T0 > BUDGET:
                break
            try:
                r = fn(d)
            except Exception as e:
                fails[k] = fails.get(k, 0) + 1
                errs.append(f"{day} {k}: {str(e)[:80]}")
                continue
            if r is None:
                if d < now.date():
                    fails[k] = fails.get(k, 0) + 1
                    errs.append(f"{day} {k}: 無資料或日期不符")
                continue
            fails[k] = 0
            rec.setdefault(slot, {}).update(r)
            src.add(k)
            rec["src"] = sorted(src)
            changed = True
        if changed:
            (CHIP / f"{day}.json").write_text(json.dumps(rec, ensure_ascii=False, separators=(",", ":")), "utf-8")
        if fm.nreq >= MAX_REQ or time.time() - T0 > BUDGET:
            errs.append(f"達到單次上限（{fm.nreq} 次請求），下次繼續回補")
            break
    keep = {d for d, _ in days}
    for f in CHIP.glob("*.json"):
        if f.stem not in keep and f.stem < min(keep):
            f.unlink()
    return errs


def targets():
    ids = set(EXTRA)
    try:
        for t in json.loads((OUT / "themes.json").read_text("utf-8"))["themes"]:
            ids.update(s[0] for s in t.get("stocks", []))
    except Exception:
        pass
    ids.update(itrust_top_ids())
    return sorted(ids)

def itrust_top_ids():
    """估值頁的投本比自動主題（data/itrust_top.json：投信／外資／土洋前 20）也當成主題成份股一起抓。"""
    try:
        j = json.loads((OUT / "itrust_top.json").read_text("utf-8"))
        return {r["c"] for L in (j.get("lists") or {}).values() for r in L}
    except Exception:
        return set()


def rows_of(c, recs, ma=None):
    k = lambda x: None if x is None else round(x / 1000)          # 股 → 張
    rows = []
    for day, px, rec in recs:
        p = px.get("p", {}).get(c) or [None, None]
        src = set(rec.get("src", []))
        iv = rec.get("i", {}).get(c)
        mv = rec.get("m", {}).get(c)
        # 該來源當天有抓到但沒有這檔 = 0；來源沒抓到 = null
        if iv is None and {"iL", "iO"} <= src:
            iv = [0, 0, 0]
        rows.append([p[0], k(p[1]),
                     *(k(x) for x in (iv or [None] * 3)),
                     *((round(x) if x is not None else None) for x in (mv or [None] * 3)),
                     *(p[2:5] if len(p) >= 5 else [None] * 3)])  # 開高低（K 線用）
    if ma is not None:                                             # 第 12 欄：240 日均線（年線）
        for r, m in zip(rows, ma):
            r.append(m)
    return rows


def ma240(c, closes, n_out):
    """closes = 全部交易日 {代號: 收盤} 列表（舊→新）；回傳最後 n_out 天的 240 日均線"""
    xs = [d.get(c) for d in closes]
    out = []
    for i in range(len(xs) - n_out, len(xs)):
        w = xs[max(0, i - 239):i + 1]
        w = [x for x in w if x is not None]
        out.append(round(sum(w) / 240, 2) if i >= 239 and len(w) >= 228 else None)   # 停牌少於 5% 才算
    return out


def build_shards(days):
    """全市場逐日籌碼＋K 線，依代號前兩碼分片存 data/chip_s/NN.json（檔案只在內容有變時改寫）
    價格取最近 KDAYS 個交易日（K 線＋均線用），籌碼只有最近 NDAYS 天有值"""
    allp = trade_days(10 ** 6)                                     # 含瘦身的舊收盤
    closes = [{c: v[0] for c, v in px.get("p", {}).items() if v} for _, px in allp]
    days = allp[-KDAYS:]
    recs = [(day, px, load(day)) for day, px in days]
    codes = set()
    for _, px, _ in recs:
        codes.update(px.get("p", {}).keys())
    SH = OUT / "chip_s"
    SH.mkdir(parents=True, exist_ok=True)
    groups = {}
    for c in codes:
        if c.isdigit() and len(c) >= 4:
            groups.setdefault(c[:2], []).append(c)
    n = 0
    for g, cs in groups.items():
        d = {c: rows_of(c, recs, ma240(c, closes, len(days))) for c in sorted(cs)}
        d = {c: r for c, r in d.items() if any(x[0] for x in r)}
        if not d:
            continue
        txt = json.dumps({"days": [x for x, _ in days], "d": d}, ensure_ascii=False, separators=(",", ":"))
        f = SH / f"{g}.json"
        if not f.exists() or f.read_text("utf-8") != txt:
            f.write_text(txt, "utf-8")
        n += len(d)
    live = {f"{g}.json" for g in groups}
    for f in SH.glob("*.json"):
        if f.name not in live:
            f.unlink()
    return n, len(groups)


def build(days):
    ids = targets()
    recs = [(day, px, load(day)) for day, px in days]
    k = lambda x: None if x is None else round(x / 1000)          # 股 → 張
    d = {}
    for c in ids:
        rows = []
        for day, px, rec in recs:
            p = px.get("p", {}).get(c) or [None, None]
            src = set(rec.get("src", []))
            iv = rec.get("i", {}).get(c)
            mv = rec.get("m", {}).get(c)
            # 該來源當天有抓到但沒有這檔 = 0；來源沒抓到 = null
            if iv is None and {"iL", "iO"} <= src:
                iv = [0, 0, 0]
            rows.append([p[0], k(p[1]),
                         *(k(x) for x in (iv or [None] * 3)),
                         *((round(x) if x is not None else None) for x in (mv or [None] * 3))])
        if any(r[0] for r in rows):
            d[c] = rows
    done = lambda key: sum(1 for _, _, r in recs if key in r.get("src", []))
    return d, {k_: done(k_) for k_ in SOURCES}


def main():
    days = trade_days()
    if not days:
        print("data/hist 沒有交易日，請先跑 fetch_momentum.py", file=sys.stderr)
        sys.exit(1)
    errs = collect(days)
    d, cover = build(days)
    try:
        ns, ng = build_shards(days)
        print(f"chip_s/: {ns} 檔分成 {ng} 片")
    except Exception as e:
        errs.append(f"shards: {str(e)[:80]}")
    res = dict(updated=dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"), days=[x for x, _ in days],
               fields=["close", "vol", "foreign", "trust", "dealer", "marginChg", "shortChg", "marginBal"],
               cover=cover, req=fm.nreq, secs=int(time.time() - T0), fails=fails, errors=errs[:30],
               diag={k: (v[-12:] if isinstance(v, list) else v) for k, v in diag.items()}, d=d)
    (OUT / "chip.json").write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"chip.json: {len(d)} 檔、{len(days)} 天；各來源已完成天數 {cover}；請求 {fm.nreq} 次；錯誤 {len(errs)}")


if __name__ == "__main__":
    main()
