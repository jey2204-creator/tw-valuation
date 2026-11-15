"""成交值／成交量排行（掃描頁「💰 成交值前50／📊 成交量前50」用）→ data/rank.json（2026-11-15）

來源跟 fetch_momentum.py 同一組官網（可指定日期，不耗 FinMind 額度），每個交易日各 1 次請求：
  上市  www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?type=ALLBUT0999   欄位：成交股數、成交金額
  上櫃  www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes              欄位：成交股數、成交金額(元)
範圍＝data/list.json 的上市櫃股票＋ETF（代號 00 開頭；世杰 2026/11/15 選「ETF 保留」）。權證、特別股、TDR、ETN 不收。

每個交易日存一個不再改動的檔 data/rank/YYYYMMDD.json：
  {"L":{"v":[[代號,成交值億]…前50],"q":[[代號,成交張]…前50],"vs":[…],"qs":[…]},"O":{…同上},"e":{ETF代號:[收,張,開,高,低]}}
  v／q＝含 ETF 的前 50；vs／qs＝不含 ETF 的前 50（掃描頁「ETF 含·不含」開關用）
  L＝上市、O＝上櫃；「合併」由網頁把兩邊前 50 合起來再取前 50（合併前 50 一定落在兩邊前 50 的聯集裡）。
  e＝當天所有 ETF 的日K（本站 data/chip_s 分片沒有 ETF，掃描頁小卡要畫 K 線就靠這個）。
data/rank/names.json＝{代號:[名稱,市場]}（ETF 名稱；list.json 沒有）
data/rank/state.json＝{日期:失敗次數}（某天一直抓不到就不再重試）

輸出 data/rank.json（網頁只讀這一個）：
  {asof, builtAt, top, days:[新→舊，最多 30 天], hist:{日期:{L:{v,q},O:{v,q}}}, nm:{ETF代號:[名稱,市場]},
   xk:{days:[舊→新，最多 130 天], d:{ETF代號:[[收,張,開,高,低] 或 0,…]}}}   ← 只放近 30 天上過榜的 ETF

第一次執行往回補 60 個交易日（約 6 分鐘），之後每次再補 35 天，直到 130 天（ETF 的 K 線＋均線用）。
用法：python fetch_rank.py
"""
import json, re, sys, time, datetime as dt
from pathlib import Path
import fetch_momentum as fm

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data"
RK = OUT / "rank"
TOP, SHOW_DAYS, KEEP = 50, 30, 130
FIRST_DAYS, MORE_DAYS = 60, 35          # 第一次補幾天／之後每次再補幾天
BUDGET = 9 * 60                         # 單次最多抓 9 分鐘
ETF = re.compile(r"^00[0-9A-Z]{2,4}$")
T0 = time.time()


def stock_set():
    try:
        return {r[0] for r in json.loads((OUT / "list.json").read_text("utf-8"))}
    except Exception:
        return set()


def trading_days():
    """data/hist 裡有收盤價的交易日（新→舊）。休市日檔案是 {"closed":1}。"""
    out = []
    for f in sorted((OUT / "hist").glob("2*.json"), reverse=True):
        try:
            if f.stat().st_size < 200:
                continue
        except OSError:
            continue
        out.append(f.stem)
        if len(out) >= KEEP:
            break
    return out


def parse(tables, old_tpex=False):
    """[(fields, rows)] → {代號:[名稱,收,股數,金額,開,高,低]}；找不到必要欄位回 None。"""
    for fields, rows in tables:
        if fields:
            ic = fm.col(fields, "代號")
            inn = fm.col(fields, "名稱")
            ip = fm.col(fields, "收盤")
            iv = fm.col(fields, "成交股數")
            ia = fm.col(fields, "成交金額")
            io, ih, il = fm.col(fields, "開盤"), fm.col(fields, "最高"), fm.col(fields, "最低")
        elif old_tpex:                      # 舊版 aaData：代號,名稱,收盤,漲跌,開,高,低,均價,成交股數,成交金額,成交筆數
            ic, inn, ip, iv, ia, io, ih, il = 0, 1, 2, 8, 9, 4, 5, 6
        else:
            continue
        if ic is None or ip is None or iv is None:
            continue
        out = {}
        for r in rows:
            try:
                c = str(r[ic]).strip()
                cl, sh = fm.num(r[ip]), fm.num(r[iv])
                am = fm.num(r[ia]) if ia is not None and ia < len(r) else None
                if am is None and cl is not None and sh is not None:
                    am = cl * sh            # 沒有成交金額欄位就用 收盤×股數 近似
                g = lambda i: fm.num(r[i]) if i is not None and i < len(r) else None
                out[c] = [str(r[inn]).strip() if inn is not None else "", cl, sh, am, g(io), g(ih), g(il)]
            except Exception:
                continue
        if len(out) > 100:
            return out
    return None


def twse_day(d):
    js = fm.get(f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={d:%Y%m%d}&type=ALLBUT0999&response=json", "twse")
    rd = fm.resp_date(js)
    if rd and rd != d:
        return None
    return parse(fm.tables_of(js))


def tpex_day(d):
    import urllib.parse
    roc = f"{d.year - 1911}/{d:%m/%d}"
    urls = [f"https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes?date={d:%Y}%2F{d:%m}%2F{d:%d}&id=&response=json",
            f"https://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/stk_quote_result.php?l=zh-tw&o=json&d={urllib.parse.quote(roc)}"]
    err = None
    for u in urls:
        try:
            js = fm.get(u, "tpex")
        except Exception as e:
            err = e
            continue
        if fm.resp_date(js) != d:           # 舊版 php 會忽略日期、永遠回最新一天 → 日期對不上就不採用
            continue
        out = parse(fm.tables_of(js), old_tpex=True)
        if out:
            return out
    if err:
        raise err
    return None


def day_rec(raw, stocks, mkt, names):
    """單一市場：{代號:[名稱,收,股數,金額,開,高,低]} → ({"v":[…],"q":[…]}, {ETF:[收,張,開,高,低]})"""
    rows, etf = [], {}
    for c, (nm, cl, sh, am, o, h, l) in raw.items():
        is_etf = bool(ETF.match(c))
        if not is_etf and not ((c in stocks) if stocks else fm.ok_code(c)):
            continue
        if cl is None or not sh:
            continue
        lots = int(round(sh / 1000))
        rows.append((c, am or 0, lots))
        if is_etf:
            etf[c] = [cl, lots, o if o is not None else cl, h if h is not None else cl, l if l is not None else cl]
            if nm:
                names[c] = [nm, mkt]
    def top(i, only_stock):
        r = [x for x in rows if not (only_stock and ETF.match(x[0]))]
        return sorted(r, key=lambda x: -x[i])[:TOP]
    out = {}
    for key, only in (("v", False), ("vs", True)):          # v＝含 ETF、vs＝不含 ETF（2026-11-15 加，掃描頁「ETF 含·不含」開關用）
        out[key] = [[c, round(am / 1e8, 2)] for c, am, _ in top(1, only) if am > 0]
    for key, only in (("q", False), ("qs", True)):
        out[key] = [[c, lots] for c, _, lots in top(2, only) if lots > 0]
    return out, etf


def load(f, default):
    try:
        return json.loads(f.read_text("utf-8"))
    except Exception:
        return default


def dump(f, obj):
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), "utf-8")


def collect():
    stocks = stock_set()
    names = load(RK / "names.json", {})
    state = load(RK / "state.json", {})
    tdays = trading_days()
    # 舊格式的日檔（沒有 vs／qs）視同還沒抓，重抓後覆蓋
    have = {f.stem for f in RK.glob("2*.json") if '"vs"' in f.read_text("utf-8")} if RK.exists() else set()
    quota = FIRST_DAYS if len(have) < 5 else MORE_DAYS
    todo = [d for d in tdays if d not in have and state.get(d, 0) < 3][:quota]
    got, errs = 0, []
    for ds in todo:
        if time.time() - T0 > BUDGET:
            break
        d = dt.date(int(ds[:4]), int(ds[4:6]), int(ds[6:]))
        try:
            L, O = twse_day(d), tpex_day(d)
        except Exception as e:
            errs.append(f"{ds}: {e}")
            if len(errs) >= 4:              # 連續被擋就先停，下次再來
                break
            continue
        if not L or not O:                  # 其中一邊還沒公布（或查無資料）→ 這次不存，下次再試
            if ds != tdays[0]:
                state[ds] = state.get(ds, 0) + 1
            errs.append(f"{ds}: 上市 {'有' if L else '無'}／上櫃 {'有' if O else '無'}")
            continue
        rl, el = day_rec(L, stocks, "上市", names)
        ro, eo = day_rec(O, stocks, "上櫃", names)
        dump(RK / f"{ds}.json", {"L": rl, "O": ro, "e": {**eo, **el}})
        got += 1
    dump(RK / "names.json", names)
    dump(RK / "state.json", state)
    for f in sorted(RK.glob("2*.json"))[:-KEEP]:      # 只留最近 130 個交易日
        f.unlink()
    print(f"rank: 新抓 {got} 天，待補 {max(0, len([d for d in tdays if d not in have]) - got)} 天，請求 {fm.nreq} 次，{int(time.time() - T0)} 秒")
    for e in errs[:12]:
        print("  ", e)
    return names


def build(names):
    files = sorted(RK.glob("2*.json"))
    if not files:
        print("rank.json: 還沒有任何一天的資料")
        return
    recs = {f.stem: load(f, {}) for f in files}
    days = [d for d in sorted(recs, reverse=True) if recs[d].get("L") and recs[d].get("O")]
    show = days[:SHOW_DAYS]
    hist = {d: {"L": recs[d]["L"], "O": recs[d]["O"]} for d in show}
    stocks = stock_set()
    used = set()
    for d in show:
        for m in ("L", "O"):
            for k in ("v", "q"):
                used.update(c for c, _ in recs[d][m].get(k, []))
    extra = sorted(c for c in used if c not in stocks)             # ＝上過榜的 ETF
    kd = sorted(recs)[-KEEP:]
    xk = {"days": kd, "d": {c: [recs[d].get("e", {}).get(c) or 0 for d in kd] for c in extra}}
    now = dt.datetime.utcnow() + dt.timedelta(hours=8)
    dump(OUT / "rank.json", {"asof": show[0], "builtAt": f"{now:%Y/%m/%d %H:%M}", "top": TOP, "days": show, "hist": hist,
                             "nm": {c: names.get(c, [c, ""]) for c in extra}, "xk": xk})
    print(f"rank.json: 名單 {len(show)} 天（最新 {show[0]}）、ETF {len(extra)} 檔、K 線 {len(kd)} 天、{(OUT / 'rank.json').stat().st_size // 1024} KB")


def main():
    build(collect())


if __name__ == "__main__":
    main()
