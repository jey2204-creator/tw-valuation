"""全市場每日摘要（給主題頁／產業頁的清單用）→ data/summary.json

來源：證交所與櫃買中心 OpenAPI（全市場一次抓完，不耗 FinMind 額度）
  上市：STOCK_DAY_ALL（收盤）、BWIBBU_ALL（本益比／淨值比／殖利率）、t187ap05_L（月營收）
  上櫃：tpex_mainboard_daily_close_quotes、tpex_mainboard_peratio_analysis、mopsfin_t187ap05_O
輸出 d[代號] = [收盤, 漲跌%, 本益比, 淨值比, 殖利率%, 月營收年增%, 月營收(億), 營收年月]
任何一個來源失敗只會讓該欄位空白，不會讓整支程式失敗。
用法：python fetch_summary.py
"""
import json, sys, time, datetime as dt
from pathlib import Path
import urllib.request

OUT = Path(__file__).resolve().parent / "data"
TWSE = "https://openapi.twse.com.tw/v1"
TPEX = "https://www.tpex.org.tw/openapi/v1"
FIELDS = ["close", "chg", "pe", "pb", "yld", "revYoY", "rev", "revYM"]


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
    return sorted({s[0] for t in th for s in t["stocks"]})


def eps_of(rows):
    """FinMind 單季財報 → [季別, 本季EPS, 去年同季EPS, 年增%, 業外旗標]
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
    return [label, round(cur, 2), round(prev, 2) if prev is not None else None, yoy, nonop]


def fetch_eps(ids):
    start = f"{dt.date.today().year - 2}-01-01"
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


def patch_revenue(d, latest):
    """證交所開放資料的上市月營收常晚幾天才更新；主題成份股若落後，用 FinMind 補到最新月份。"""
    ids = theme_ids()
    lag = [c for c in ids if c in d and (d[c][7] or "") < latest]
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
    yms = sorted({x[7] for x in d.values() if x[7]})
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
               epsFields=["q", "eps", "epsPrev", "yoy", "nonop"], eps=eps)
    (OUT / "summary.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"summary.json: {len(d)} 檔，最新營收月份 {out['revYM']}，失敗 {len(errs)} 個來源")


if __name__ == "__main__":
    main()
