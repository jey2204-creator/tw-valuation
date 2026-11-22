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

2026-11-19：週轉率前 50（掃描頁「🔄 週轉率前50」）——不另外抓資料，build() 時用本站已有的兩個檔算：
  週轉率% ＝ data/hist/日期.json 的成交股數 ÷ data/summary.json 的 sh（已發行普通股數，目前值）× 100
  門檻：成交值（收盤×成交股數，估算）≥ 1 億；不含 ETF（受益權單位天天變）。上市、上櫃各取前 50 → hist[日期][L|O]["t"]=[[代號,週轉率%]…]
  股數用「目前」的值套回過去 30 天：期間內有增減資／分割的公司，舊日期會有誤差；>100% 多半是股數資料有誤，網頁標「?」。
用法：python fetch_rank.py
"""
import json, re, sys, time, datetime as dt
from pathlib import Path
import fetch_momentum as fm

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data"
RK = OUT / "rank"
TOP, SHOW_DAYS, KEEP = 50, 30, 130
TR_MIN_AMT = 1e8                        # 週轉率榜的成交值門檻（元）
FIRST_DAYS, MORE_DAYS = 60, 35          # 第一次補幾天／之後每次再補幾天
BUDGET = 9 * 60                         # 單次最多抓 9 分鐘
ETF = re.compile(r"^00[0-9A-Z]{2,4}$")
# 2026-11-22：首頁／掃描頁「📦 ETF」主題的固定名單
# 14:40 世杰改：每類（市值／高息／科技／債券／國外）規模前 5 大＋保留 00713、00940、00892，類別內依規模由大到小
# 每列 [代號, 備註「類別｜說明」, 規模億元]；規模＝玩股網 2026/11/20 排行（00892 取證交所 ETFortune 126.12 億，不在前 60），手動填、不會自動更新
# 要增減或更新規模直接改這裡（順序＝畫面順序），下次排程就會更新 data/etf.json
ETF_AUM_ASOF = "20261120"
ETF_THEME = [["0050", "市值｜台灣50", 21619.65], ["006208", "市值｜台灣50", 3716.17], ["009816", "市值｜台灣TOP50", 1911.91],
             ["00922", "市值｜領袖50", 660.66], ["00692", "市值｜公司治理", 445.32],
             ["0056", "高息｜高股息", 6820.24], ["00878", "高息｜ESG高息", 5625.60], ["00919", "高息｜精選高息", 5379.37],
             ["00918", "高息｜優利填息", 1379.31], ["00929", "高息｜科技優息", 1311.89], ["00713", "高息｜高息低波", 981.20],
             ["00940", "高息｜價值高息", 532.19],
             ["0052", "科技｜科技", 1323.37], ["00881", "科技｜科技龍頭", 1139.73], ["00927", "科技｜半導體收益", 594.77],
             ["00891", "科技｜半導體", 562.59], ["00935", "科技｜新科技50", 413.60], ["00892", "科技｜半導體", 126.12],
             ["00937B", "債券｜投等債20+", 2313.96], ["00751B", "債券｜AAA-A公司債", 1550.39], ["00679B", "債券｜美債20年", 1539.01],
             ["00720B", "債券｜投資級公司債", 1289.85], ["00725B", "債券｜投資級公司債", 1286.23],
             # 15:47 世杰加「國外」類：規模前 5 大（不含主動式 00988A、陸股 00882）
             ["00662", "國外｜NASDAQ", 1155.98], ["00830", "國外｜費城半導體", 703.91], ["00646", "國外｜S&P500", 472.79],
             ["00712", "國外｜美國不動產", 422.12], ["00757", "國外｜FANG+", 333.70]]
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


def turnover(show, hist):
    """週轉率前 50：hist[日期][L|O]["t"]=[[代號,週轉率%]…]（成交值 ≥ 1 億、不含 ETF）。回傳有算出來的天數。"""
    try:
        mk = {r[0]: r[2] for r in json.loads((OUT / "list.json").read_text("utf-8"))}
        sh = json.loads((OUT / "summary.json").read_text("utf-8")).get("sh") or {}
    except Exception:
        return 0
    n = 0
    for d in show:
        p = load(OUT / "hist" / f"{d}.json", {}).get("p") or {}
        rows = {"L": [], "O": []}
        for c, v in p.items():
            m = {"上市": "L", "上櫃": "O"}.get(mk.get(c))
            s = sh.get(c)
            if not m or not s or ETF.match(c) or not v or v[0] is None or not v[1]:
                continue
            if v[0] * v[1] < TR_MIN_AMT:
                continue
            rows[m].append([c, round(v[1] / s * 100, 2)])
        if not rows["L"] and not rows["O"]:
            continue
        for m in ("L", "O"):
            hist[d][m]["t"] = sorted(rows[m], key=lambda x: -x[1])[:TOP]
        n += 1
    return n


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
    ntr = turnover(show, hist)
    stocks = stock_set()
    used = set()
    for d in show:
        for m in ("L", "O"):
            for k in ("v", "q"):
                used.update(c for c, _ in recs[d][m].get(k, []))
    extra = sorted({c for c in used if c not in stocks} | {x[0] for x in ETF_THEME})   # ＝上過榜的 ETF＋📦 ETF 主題的固定名單
    kd = sorted(recs)[-KEEP:]
    xk = {"days": kd, "d": {c: [r or 0 for r in split_adj([recs[d].get("e", {}).get(c) for d in kd])] for c in extra}}   # 2026-11-22：ETF 分割還原
    now = dt.datetime.utcnow() + dt.timedelta(hours=8)
    dump(OUT / "rank.json", {"asof": show[0], "builtAt": f"{now:%Y/%m/%d %H:%M}", "top": TOP, "days": show, "hist": hist,
                             "nm": {c: names.get(c, [c, ""]) for c in extra}, "xk": xk})
    home(show, hist, names)
    build_etf(recs, names)
    print(f"rank.json: 名單 {len(show)} 天（最新 {show[0]}）、ETF {len(extra)} 檔、K 線 {len(kd)} 天、週轉率 {ntr} 天、{(OUT / 'rank.json').stat().st_size // 1024} KB")


def split_adj(seq):
    """2026-11-22：ETF 分割／反分割還原（例 00662 富邦NASDAQ 11/17 一拆五：117.8 → 23.1）。
    seq＝[[收,張,開,高,低] 或 None/0,…]（舊→新）。相鄰兩個有值的收盤比 ≥1.8（或 ≤1/1.8）且接近整數倍（誤差 <8%）視為分割，
    把更早的價位 ÷ 倍數、張數 × 倍數。台股 ETF 有 10% 漲跌幅（海外型也很少單日腰斬），不會誤判一般漲跌。"""
    out = [list(r) if r else r for r in seq]
    last = None
    for i in range(len(out)):
        r = out[i]
        if not r:
            continue
        if last is not None and r[0]:
            p = out[last][0]
            for k in (p / r[0], r[0] / p):
                n = round(k)
                if k >= 1.8 and abs(k - n) / n < 0.08:
                    f = n if p > r[0] else 1 / n
                    for j in range(i):
                        q = out[j]
                        if q:
                            out[j] = [round(q[0] / f, 4), int(round(q[1] * f))] + [round(x / f, 4) if x is not None else None for x in q[2:]]
                    break
        last = i
    return out


def build_etf(recs, names):
    """📦 ETF 主題（2026-11-22）→ data/etf.json：
    {asof, n, stocks:[[代號, 備註]…], aum:{代號:規模億}, aumAsof, nm:{代號:[名稱,市場]}, px:{代號:[收, 日%, 週%, 月%, 季%, 量比, 成交值億, 20日均值億]}}
    週/月/季＝對比 5/20/60 個交易日前收盤；量比＝今日張數 ÷ 前 5 日均張；成交值≈收×張×1000。
    ETF 的價格「未還原配息」：跨除息日的漲跌會偏低（高股息 ETF 季配／月配特別明顯）。不另外發請求，只用 data/rank/日期.json 的 e。"""
    kd = sorted(d for d in recs if recs[d].get("e"))
    if not kd:
        return
    def ser(c):
        return split_adj([recs[d]["e"].get(c) for d in kd])
    px, cat = {}, {}
    for c, note, _ in ETF_THEME:
        a = ser(c)
        if not a or not a[-1]:
            continue
        cl = [r[0] if r else None for r in a]
        lots = [r[1] if r else None for r in a]
        def chg(n):                      # 基準日停止交易（分割期間等）時往前找最近一個有收盤的日子
            j = len(cl) - 1 - n
            while j >= 0 and not cl[j]:
                j -= 1
            if j < 0:
                return None
            return round((cl[-1] / cl[j] - 1) * 100, 2)
        p5 = [x for x in lots[-6:-1] if x]
        vr = round(lots[-1] / (sum(p5) / len(p5)), 2) if p5 and lots[-1] else None
        val = lambda r: r[0] * r[1] * 1000 / 1e8
        v20 = [val(r) for r in a[-20:] if r]
        px[c] = [cl[-1], chg(1), chg(5), chg(20), chg(60), vr, round(val(a[-1]), 2), round(sum(v20) / len(v20), 2) if v20 else None]
        cat[c] = note.split("｜")[0]
    order = [[c, n] for c, n, _ in ETF_THEME if c in px]          # 順序＝ETF_THEME（類別內依規模）
    dump(OUT / "etf.json", {"asof": kd[-1], "n": len(order), "stocks": order,
                            "aum": {c: v for c, _, v in ETF_THEME if c in px}, "aumAsof": ETF_AUM_ASOF,
                            "nm": {c: names.get(c, [c, ""]) for c, _ in order}, "px": px})
    print(f"etf.json: {len(order)}/{len(ETF_THEME)} 檔，資料日 {kd[-1]}")


def home(show, hist, names):
    """首頁入口清單那一列用的小檔 data/rank/home.json（rank.json 太大，首頁不讀）。
    v／q → 六種設定（a 合併、L 上市、O 上櫃 × 1 含 ETF、0 不含）各存 [第 1 名代號, 名稱, 數值, 新上榜檔數]。"""
    try:
        nm = {r[0]: r[1] for r in json.loads((OUT / "list.json").read_text("utf-8"))}
    except Exception:
        nm = {}

    def lst(d, k, m, e):
        h = hist.get(d) or {}

        def g(x):
            o = h.get(x) or {}
            return o.get(k, []) if e else (o.get(k + "s") or [r for r in o.get(k, []) if not r[0].startswith("00")])
        a = g("L") if m == "L" else g("O") if m == "O" else sorted(g("L") + g("O"), key=lambda r: -r[1])
        return a[:TOP]

    out = {"asof": show[0], "prev": show[1] if len(show) > 1 else None, "v": {}, "q": {}}
    for k in ("v", "q"):
        for m in ("a", "L", "O"):
            for e in (1, 0):
                a = lst(show[0], k, m, e)
                if not a:
                    continue
                prev = {c for c, _ in lst(show[1], k, m, e)} if len(show) > 1 else None
                c, x = a[0]
                out[k][f"{m}{e}"] = [c, nm.get(c) or (names.get(c) or [c])[0], x,
                                     sum(1 for r in a if r[0] not in prev) if prev is not None else None]
    dump(RK / "home.json", out)


def main():
    build(collect())


if __name__ == "__main__":
    main()
