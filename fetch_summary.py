"""全市場每日摘要（給主題頁／產業頁的清單用）→ data/summary.json

來源：證交所與櫃買中心 OpenAPI（全市場一次抓完，不耗 FinMind 額度）
  上市：STOCK_DAY_ALL（收盤）、BWIBBU_ALL（本益比／淨值比／殖利率）、t187ap05_L（月營收）
  上櫃：tpex_mainboard_daily_close_quotes、tpex_mainboard_peratio_analysis、mopsfin_t187ap05_O
輸出 d[代號] = [收盤, 漲跌%, 本益比, 淨值比, 殖利率%, 月營收年增%, 月營收(億), 營收年月, 今年累計營收(億)]
     sh[代號] = 已發行普通股數（公司基本資料 t187ap03_L／mopsfin_t187ap03_O；網頁用 收盤 × 股數 算市值）
任何一個來源失敗只會讓該欄位空白，不會讓整支程式失敗。
用法：python fetch_summary.py
"""
import json, sys, time, datetime as dt
from pathlib import Path
import urllib.request

OUT = Path(__file__).resolve().parent / "data"
TWSE = "https://openapi.twse.com.tw/v1"
TPEX = "https://www.tpex.org.tw/openapi/v1"
FIELDS = ["close", "chg", "pe", "pb", "yld", "revYoY", "rev", "revYM", "revYTD"]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 tw-valuation", "Accept": "application/json"})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8-sig"))
        except Exception as e:
            if i == 2:
                raise RuntimeError(f"{url}: {e}")
            time.sleep(5 * (i + 1))


def num(v):
    if v is None:
        return None
    s = str(v).replace(",", "").replace("+", "").strip()
    if s in ("", "-", "--", "---", "N/A", "X0.00"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def pick(row, *names):
    """欄位名稱各來源不一，依序找；找不到再用「包含」比對。"""
    for n in names:
        if n in row:
            return row[n]
    for n in names:
        for k in row:
            if n in k:
                return row[k]
    return None


def code_of(row):
    c = pick(row, "Code", "SecuritiesCompanyCode", "公司代號")
    return str(c).strip() if c is not None else ""


def ym_of(v):
    """資料年月：民國 11509 / 115/09 / 2026-09 → '2026-09'"""
    s = "".join(ch for ch in str(v or "") if ch.isdigit())
    if len(s) == 5:      # 民國 3 碼年 + 2 碼月
        return f"{int(s[:3]) + 1911}-{s[3:]}"
    if len(s) == 6 and int(s[:4]) > 1900:   # 西元
        return f"{s[:4]}-{s[4:]}"
    return None


def finmind(dataset, sid, start):
    import os, urllib.parse
    q = urllib.parse.urlencode({"dataset": dataset, "data_id": sid, "start_date": start})
    req = urllib.request.Request("https://api.finmindtrade.com/api/v4/data?" + q)
    tok = os.environ.get("FINMIND_TOKEN", "")
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r).get("data", [])


def theme_ids():
    th = json.loads((OUT / "themes.json").read_text("utf-8"))["themes"]
    return sorted({s[0] for t in th for s in t["stocks"]} | itrust_top_ids())

def itrust_top_ids():
    """估值頁的投本比自動主題（data/itrust_top.json：投信／外資／土洋前 20）也當成主題成份股一起抓。"""
    try:
        j = json.loads((OUT / "itrust_top.json").read_text("utf-8"))
        return {r["c"] for L in (j.get("lists") or {}).values() for r in L}
    except Exception:
        return set()


def eps_of(rows):
    """FinMind 單季財報 → [季別, 本季EPS, 去年同季EPS, 年增%, 業外旗標, 近四季EPS, 前四季EPS, 近四季年增%, 近四季業外旗標]
    年增% 只有去年同季 EPS > 0 才算；業外旗標 = 本季淨利率比營益率高 5 個百分點以上"""
    q = {}
    for r in rows:
        q.setdefault(r["date"], {})[r["type"]] = r["value"]
    ds = sorted(d for d in q if q[d].get("EPS") is not None)
    if not ds:
        return None
    last = ds[-1]
    o = q[last]
    prev_d = f"{int(last[:4]) - 1}{last[4:]}"
    prev = q.get(prev_d, {}).get("EPS")
    cur = o["EPS"]
    yoy = round((cur / prev - 1) * 100, 1) if prev is not None and prev > 0 else None
    rv, oi, ni = o.get("Revenue"), o.get("OperatingIncome"), o.get("EquityAttributableToOwnersOfParent")
    nonop = 1 if rv and oi is not None and ni is not None and (ni - oi) / rv * 100 > 5 else 0
    label = f"{last[2:4]}Q{(int(last[5:7]) + 2) // 3}"
    # 近四季：最新 4 季 EPS 合計 vs 前 4 季合計（8 季要連續，差一季就不算）；業外旗標＝4 季任一季中
    e4 = p4 = yoy4 = None
    nonop4 = 0
    if len(ds) >= 8:
        ks = ds[-8:]
        qn = [int(d[:4]) * 4 + (int(d[5:7]) + 2) // 3 for d in ks]
        if all(b - a == 1 for a, b in zip(qn, qn[1:])):
            e4 = round(sum(q[d]["EPS"] for d in ks[4:]), 2)
            p4 = round(sum(q[d]["EPS"] for d in ks[:4]), 2)
            yoy4 = round((e4 / p4 - 1) * 100, 1) if p4 > 0 else None
            for d in ks[4:]:
                x = q[d]
                r_, o_, n_ = x.get("Revenue"), x.get("OperatingIncome"), x.get("EquityAttributableToOwnersOfParent")
                if r_ and o_ is not None and n_ is not None and (n_ - o_) / r_ * 100 > 5:
                    nonop4 = 1
    return [label, round(cur, 2), round(prev, 2) if prev is not None else None, yoy, nonop, e4, p4, yoy4, nonop4]


def fetch_eps(ids):
    start = f"{dt.date.today().year - 3}-01-01"   # 近四季年增要 8 季：往前抓 3 年
    out, fail = {}, 0
    for c in ids:
        try:
            e = eps_of(finmind("TaiwanStockFinancialStatements", c, start))
            if e:
                out[c] = e
        except Exception as ex:
            fail += 1
            print(f"  {c} EPS 失敗: {ex}", file=sys.stderr)
        time.sleep(0.3)
    print(f"FinMind EPS：{len(ids)} 檔，成功 {len(out)}，失敗 {fail}")
    return out


def carry_revenue(d):
    """證交所 t187ap05_L 換新月份時是分批補進來的（2026/10/12 起 9 月只有 868 檔，台塑、中鋼、崇越等 200 多檔整列消失）
    → 這次沒抓到營收的股票，沿用上一版 summary.json 的舊月份，不要讓欄位變成「—」。"""
    try:
        old = json.loads((OUT / "summary.json").read_text("utf-8")).get("d", {})
    except Exception:
        return 0
    n = 0
    for c, x in d.items():
        o = old.get(c)
        if x[7] is None and o and len(o) > 7 and o[7]:
            x[5], x[6], x[7] = o[5], o[6], o[7]
            x[8] = o[8] if len(o) > 8 else None
            n += 1
    print(f"營收沿用上一版：{n} 檔")
    return n


PAR = {}   # 面額分布（診斷用）


def shares_of(r):
    """公司基本資料的已發行普通股數；欄名各來源不一，找不到就用 實收資本額 ÷ 每股面額"""
    v = num(pick(r, "已發行普通股數或TDR原股發行股數", "已發行普通股數", "IssueShares", "NumberOfSharesIssued"))
    if v is None:
        for k in r:
            if ("股數" in k or "shares" in k.lower()) and not any(w in k for w in ("私募", "特別", "Private", "Preferred")):
                v = num(r[k])
                if v:
                    break
    if v:
        return int(v)
    # 證交所／櫃買公司基本資料沒有股數欄 → 實收資本額 ÷ 普通股面額 − 特別股股數
    cap = num(pick(r, "實收資本額", "Paidin.Capital.NTDollars", "PaidInCapital"))
    par = pick(r, "普通股每股面額", "ParValueOfCommonStock", "ParValue")
    pv = num("".join(ch for ch in str(par or "") if ch.isdigit() or ch == ".")) or 10
    pref = num(pick(r, "特別股", "PreferredStock.shares")) or 0
    if not cap:
        return None
    PAR[pv] = PAR.get(pv, 0) + 1
    return int(cap / pv - pref) if pref * 1.0 < cap / pv else int(cap / pv)


def fetch_shares(errs, src, diag):
    sh = {}
    for name, url in (("上市股數", f"{TWSE}/opendata/t187ap03_L"), ("上櫃股數", f"{TPEX}/mopsfin_t187ap03_O")):
        try:
            rows = get(url)
            n = 0
            for r in rows:
                c = code_of(r)
                if len(c) == 4 and c.isdigit() and c[0] != "0":
                    v = shares_of(r)
                    if v and v > 0:
                        sh[c] = v
                        n += 1
            src[name] = n
            if rows:
                ex = [r for r in rows if code_of(r) in ("2330", "4958", "3665", "2002", "6669")]
                diag[name + "樣本"] = [{k: r.get(k) for k in r if any(w in k for w in ("代號", "Code", "面額", "Par", "資本", "Capital", "特別", "Preferred", "私募", "Private"))} for r in ex]
            print(f"{name}: {n} 檔")
        except Exception as e:
            errs.append(f"{name}: {e}")
            print(f"{name} FAILED: {e}", file=sys.stderr)
    diag["面額分布"] = {str(k): v for k, v in sorted(PAR.items())}
    try:                                     # 抓不到的沿用上一版
        old = json.loads((OUT / "summary.json").read_text("utf-8")).get("sh", {})
        for c, v in old.items():
            sh.setdefault(c, v)
    except Exception:
        pass
    return sh


REV_MAX = 260   # FinMind 補營收每次上限（主題成份股優先）


def patch_revenue(d, latest):
    """證交所開放資料的上市月營收常晚幾天才更新；落後最新月份的股票用 FinMind 補（主題成份股優先，其餘上限 REV_MAX）。"""
    th = set(theme_ids())
    lag = [c for c in d if (d[c][7] or "") < latest and d[c][0] is not None]
    lag.sort(key=lambda c: (c not in th, c))
    lag = lag[:REV_MAX]
    if not lag:
        return
    start = (dt.date.today() - dt.timedelta(days=430)).strftime("%Y-%m-01")
    n = 0
    for c in lag:
        try:
            rows = finmind("TaiwanStockMonthRevenue", c, start)
        except Exception as e:
            print(f"  {c} 補營收失敗: {e}", file=sys.stderr)
            continue
        m = {f"{r['revenue_year']}-{r['revenue_month']:02d}": r["revenue"] for r in rows}
        k = max(m) if m else None
        if not k or k <= (d[c][7] or ""):
            continue
        prev = m.get(f"{int(k[:4]) - 1}{k[4:]}")
        d[c][5] = round((m[k] / prev - 1) * 100, 1) if prev else None
        d[c][6] = round(m[k] / 1e8, 1)
        d[c][7] = k
        ytd = [m.get(f"{k[:4]}-{i:02d}") for i in range(1, int(k[5:]) + 1)]
        d[c][8] = round(sum(ytd) / 1e8, 1) if all(v is not None for v in ytd) else None
        n += 1
        time.sleep(0.3)
    print(f"FinMind 補營收：落後 {len(lag)} 檔，補到 {n} 檔")


def main():
    OUT.mkdir(exist_ok=True)
    d, errs, src = {}, [], {}

    def row(c):
        return d.setdefault(c, [None] * len(FIELDS))

    def load(name, url, fn):
        try:
            rows = get(url)
            n = 0
            for r in rows:
                c = code_of(r)
                if len(c) == 4 and c.isdigit() and c[0] != "0":
                    if fn(c, r) is not False:
                        n += 1
            src[name] = n
            print(f"{name}: {n} 檔")
            if n == 0 and rows:
                print(f"  ⚠️ 欄位對不上，第一列：{rows[0]}", file=sys.stderr)
        except Exception as e:
            errs.append(f"{name}: {e}")
            print(f"{name} FAILED: {e}", file=sys.stderr)

    def price(c, r, close_keys, chg_keys):
        close, chg = num(pick(r, *close_keys)), num(pick(r, *chg_keys))
        if close is None:
            return False
        x = row(c)
        x[0] = close
        if chg is not None and close - chg > 0:
            x[1] = round(chg / (close - chg) * 100, 2)

    def val(c, r, pe_k, pb_k, y_k):
        x = row(c)
        x[2], x[3], x[4] = num(pick(r, *pe_k)), num(pick(r, *pb_k)), num(pick(r, *y_k))

    def rev(c, r):
        x = row(c)
        cur = num(pick(r, "營業收入-當月營收", "當月營收"))
        y = num(pick(r, "營業收入-去年同月增減(%)", "去年同月增減"))
        x[5] = round(y, 1) if y is not None else None
        x[6] = round(cur / 1e5, 1) if cur is not None else None   # 千元 → 億
        x[7] = ym_of(pick(r, "資料年月"))
        cum = num(pick(r, "營業收入-當月累計營收", "當月累計營收"))
        x[8] = round(cum / 1e5, 1) if cum is not None else None

    load("上市收盤", f"{TWSE}/exchangeReport/STOCK_DAY_ALL",
         lambda c, r: price(c, r, ("ClosingPrice", "收盤價"), ("Change", "漲跌價差")))
    load("上櫃收盤", f"{TPEX}/tpex_mainboard_daily_close_quotes",
         lambda c, r: price(c, r, ("Close", "收盤"), ("Change", "漲跌")))
    load("上市本益比", f"{TWSE}/exchangeReport/BWIBBU_ALL",
         lambda c, r: val(c, r, ("PEratio", "本益比"), ("PBratio", "股價淨值比"), ("DividendYield", "殖利率")))
    load("上櫃本益比", f"{TPEX}/tpex_mainboard_peratio_analysis",
         lambda c, r: val(c, r, ("PriceEarningRatio", "本益比"), ("PriceBookRatio", "股價淨值比"), ("YieldRatio", "殖利率")))
    load("上市月營收", f"{TWSE}/opendata/t187ap05_L", rev)
    load("上櫃月營收", f"{TPEX}/mopsfin_t187ap05_O", rev)

    if not d:
        print("全部來源都失敗，保留舊檔", file=sys.stderr)
        sys.exit(1)
    diag = {}
    sh = fetch_shares(errs, src, diag)
    yms = sorted({x[7] for x in d.values() if x[7]})
    carry_revenue(d)
    if yms:
        try:
            patch_revenue(d, yms[-1])
        except Exception as e:
            errs.append(f"FinMind 補營收: {e}")
            print(f"FinMind 補營收 FAILED: {e}", file=sys.stderr)
    for x in d.values():                     # 本益比 0 = 虧損或不適用
        if x[2] == 0:
            x[2] = None
    yms = sorted({x[7] for x in d.values() if x[7]})
    try:
        eps = fetch_eps(theme_ids())
    except Exception as e:
        eps = {}
        errs.append(f"FinMind EPS: {e}")
    if not eps:                              # 抓不到就沿用上一版，避免整欄消失
        try:
            eps = json.loads((OUT / "summary.json").read_text("utf-8")).get("eps", {})
        except Exception:
            eps = {}
    out = dict(updated=dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"), fields=FIELDS,
               revYM=yms[-1] if yms else None, sources=src, errors=errs, d=d,
               epsFields=["q", "eps", "epsPrev", "yoy", "nonop", "e4", "p4", "yoy4", "nonop4"], eps=eps, sh=sh, diag=diag)
    (OUT / "summary.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"summary.json: {len(d)} 檔，最新營收月份 {out['revYM']}，失敗 {len(errs)} 個來源")


if __name__ == "__main__":
    main()
