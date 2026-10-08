"""美股估值看板：SEC EDGAR 財報 + FinMind 美股股價 → us/data/{TICKER}.json
用法：python us/fetch_us.py              # 抓 STOCKS 全部
     python us/fetch_us.py NVDA AVGO    # 指定代號
環境變數：FINMIND_TOKEN（選填）、SEC_UA（SEC 要求的 User-Agent，需含聯絡 email）
只用 Python 標準函式庫。
"""
import json, os, sys, time, gzip, datetime as dt
from pathlib import Path
import urllib.request, urllib.parse

# ---------- 追蹤清單：主題 → [(代號, [(台股代號, 名稱)...], 旗標)] ----------
# 旗標：C = 循環股（以淨值比為主）、D = 需求層（顯示資本支出）
THEMES = [
    ("🛰️ 低軌衛星", [("SPCX", ""), ("ASTS", ""), ("RKLB", ""), ("ECHO", ""), ("IRDM", ""), ("GSAT", ""), ("VSAT", "")],
     [("2313", "華通"), ("3491", "昇達科"), ("6285", "啟碁"), ("2314", "台揚"), ("3105", "穩懋")]),
    ("💿 矽晶圓／基板", [("WOLF", "C"), ("COHR", ""), ("ENTG", "")],
     [("6488", "環球晶"), ("5483", "中美晶"), ("6182", "合晶")]),
    ("⚡ 被動元件", [("VSH", "C"), ("LFUS", ""), ("APH", "")],
     [("2327", "國巨"), ("2492", "華新科"), ("3026", "禾伸堂"), ("3533", "嘉澤"), ("3665", "貿聯-KY")]),
    ("🟩 PCB／EMS", [("TTMI", ""), ("SANM", ""), ("JBL", ""), ("CLS", "")],
     [("4958", "臻鼎-KY"), ("3037", "欣興"), ("2368", "金像電"), ("2383", "台光電"), ("2317", "鴻海"), ("6669", "緯穎")]),
    ("💡 矽光子／CPO", [("AVGO", ""), ("MRVL", ""), ("LITE", ""), ("FN", ""), ("CRDO", ""), ("CIEN", ""), ("AAOI", "")],
     [("3081", "聯亞"), ("3363", "上詮"), ("3163", "波若威"), ("3450", "聯鈞"), ("4977", "眾達-KY"), ("4979", "華星光")]),
    ("🧱 先進封裝／設備", [("AMKR", ""), ("AMAT", "C"), ("KLAC", ""), ("ONTO", ""), ("CAMT", ""), ("LRCX", "C"), ("FORM", "")],
     [("3711", "日月光投控"), ("2449", "京元電子"), ("3131", "弘塑"), ("3583", "辛耘"), ("6187", "萬潤"), ("2360", "致茂"), ("6223", "旺矽"), ("6515", "穎崴")]),
    ("🎯 AI 晶片／記憶體", [("NVDA", ""), ("AMD", ""), ("MU", "C"), ("ARM", ""), ("SNDK", "C")],
     [("2330", "台積電"), ("3661", "世芯-KY"), ("3443", "創意"), ("2454", "聯發科"), ("2344", "華邦電"), ("2408", "南亞科"), ("8299", "群聯")]),
    ("☁️ 雲端資本支出", [("MSFT", "D"), ("GOOGL", "D"), ("AMZN", "D"), ("META", "D")], []),
    ("🖥️ 伺服器", [("SMCI", "")],
     [("2382", "廣達"), ("3231", "緯創"), ("6669", "緯穎"), ("2356", "英業達")]),
    ("❄️ 散熱／電源", [("VRT", ""), ("ETN", "")],
     [("3017", "奇鋐"), ("3324", "雙鴻"), ("3653", "健策"), ("2308", "台達電"), ("2301", "光寶科")]),
    ("🔀 網通／傳輸", [("ANET", ""), ("ALAB", "")],
     [("2345", "智邦"), ("4966", "譜瑞-KY"), ("5269", "祥碩")]),
    ("🔌 電力", [("GEV", "")],
     [("1519", "華城"), ("1503", "士電"), ("1513", "中興電"), ("1514", "亞力")]),
]
CFG = {t: dict(theme=th, flags=f, tw=tw) for th, items, tw in THEMES for t, f in items}
STOCKS = list(CFG)
PRICE_ALIAS = {"ECHO": ["SATS"]}   # 改過代號：舊代號的股價接在前面，歷史才不會斷

YEARS = 6
FM = "https://api.finmindtrade.com/api/v4/data"
OUT = Path(__file__).resolve().parent / "data"
TOKEN = os.environ.get("FINMIND_TOKEN", "")
UA = os.environ.get("SEC_UA") or "tw-valuation research jey2204-creator@users.noreply.github.com"

# 科目候選（依序）：us-gaap 與 ifrs-full 都找
REV = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
       "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet", "SalesRevenueGoodsNet",
       "Revenue"]
GP = ["GrossProfit"]
COST = ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold", "CostOfSales"]
OPI = ["OperatingIncomeLoss", "ProfitLossFromOperatingActivities"]
NI = ["NetIncomeLoss", "ProfitLossAttributableToOwnersOfParent", "ProfitLoss"]
EPS = ["EarningsPerShareDiluted", "DilutedEarningsLossPerShare", "EarningsPerShareBasicAndDiluted"]
SHR = ["WeightedAverageNumberOfDilutedSharesOutstanding",
       "WeightedAverageNumberOfShareOutstandingBasicAndDiluted"]
EQ = ["StockholdersEquity", "EquityAttributableToOwnersOfParent",
      "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]
CAPEX = ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets",
         "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"]
QFORMS = {"10-Q", "10-Q/A", "10-K", "10-K/A", "6-K", "6-K/A"}
AFORMS = {"20-F", "20-F/A", "40-F", "40-F/A"}


def http(url, headers=None, tries=3):
    req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip", **(headers or {})})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                b = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    b = gzip.decompress(b)
                return json.loads(b)
        except Exception as e:
            if i == tries - 1:
                raise RuntimeError(f"{url}: {e}")
            time.sleep(4 * (i + 1))


def sec(url):
    time.sleep(0.15)  # SEC 上限每秒 10 次
    return http(url, {"User-Agent": UA})


def finmind(dataset, sid, start):
    q = urllib.parse.urlencode({k: v for k, v in dict(dataset=dataset, data_id=sid, start_date=start).items() if v})
    h = {"Authorization": "Bearer " + TOKEN} if TOKEN else {}
    js = http(FM + "?" + q, h)
    if js.get("status") not in (200, None) and not js.get("data"):
        raise RuntimeError(f"FinMind {dataset} {sid}: {js.get('msg')}")
    return js.get("data", [])


D = lambda s: dt.date.fromisoformat(s)


def days(a, b):
    return (D(b) - D(a)).days


# ---------- SEC 事實抽取 ----------
def facts_of(cf, names, unit_pred):
    """回傳 {concept: [entries]}，entries 只保留指定單位與表單"""
    out = {}
    for ns in ("us-gaap", "ifrs-full"):
        for n in names:
            node = cf.get("facts", {}).get(ns, {}).get(n)
            if not node:
                continue
            rows = []
            for u, lst in node.get("units", {}).items():
                if unit_pred(u):
                    rows += [r for r in lst if r.get("form") in QFORMS | AFORMS]
            if rows:
                out.setdefault(n, []).extend(rows)
    return out


def latest_by_period(rows):
    """同一期間（start,end）多次申報 → 取最晚申報（含修正與分割後重述），保留最早申報日當作公布日"""
    m = {}
    for r in rows:
        k = (r.get("start"), r["end"])
        if k not in m:
            m[k] = dict(r, first=r["filed"])
        else:
            o = m[k]
            first = min(o["first"], r["filed"])
            if r["filed"] >= o["filed"]:
                m[k] = dict(r, first=first)
            else:
                o["first"] = first
    return m


def restatements(cf, names, unit_pred, inverse=False):
    """同一期間前後兩次申報的比例接近整數 n≥2 → [(後一次申報日, n)]"""
    ev = []
    for rows in facts_of(cf, names, unit_pred).values():
        by = {}
        for r in rows:
            by.setdefault((r.get("start"), r["end"]), []).append(r)
        for lst in by.values():
            lst.sort(key=lambda r: r["filed"])
            for a, b in zip(lst, lst[1:]):
                if not a["val"] or not b["val"] or (a["val"] > 0) != (b["val"] > 0):
                    continue
                ratio = b["val"] / a["val"] if inverse else a["val"] / b["val"]
                n = round(ratio)
                if 2 <= n <= 50 and abs(ratio - n) / n < 0.03:
                    ev.append((b["filed"], n))
    return ev


def split_events(cf):
    """股票分割：EPS 重述縮小 n 倍，且稀釋股數同時重述放大 n 倍（前後 200 天內）才採用。
    只看 EPS 會把會計重述、單位更正誤判成分割。回傳 [(生效日, n)]"""
    sh = restatements(cf, SHR, lambda u: u == "shares", inverse=True)
    ev = [(d, n) for d, n in restatements(cf, EPS, lambda u: "/" in u)
          if any(m == n and abs(days(d, d2)) <= 200 for d2, m in sh)]
    # 合併：同一比例、相隔 400 天內視為同一次分割，取最早重述日
    ev.sort()
    out = []
    for d, n in ev:
        if out and out[-1][1] == n and days(out[-1][0], d) < 400:
            continue
        out.append((d, n))
    return out


def split_factor(filed, splits):
    f = 1
    for d, n in splits:
        if filed < d:
            f *= n
    return f


def quarters(rows):
    """把一個科目整理成 {季末日: (值, 公布日, 起日, 採用值的申報日)}。
    優先用 3 個月數值；沒有的用累計（YTD）相減（現金流量表只有 YTD），
    10-K 只給全年時 Q4 = 全年 − 前三季"""
    m = latest_by_period(rows)
    out, cum, ann = {}, {}, []
    for (s, e), r in m.items():
        if not s:
            continue
        n = days(s, e)
        if 80 <= n <= 100:
            out[e] = (r["val"], r["first"], s, r["filed"])
        if n >= 80:
            cum.setdefault(s, []).append((e, n, r))
        if 350 <= n <= 380:
            ann.append((s, e, r))
    for s, lst in cum.items():
        lst.sort(key=lambda x: x[0])
        for (e0, n0, r0), (e1, n1, r1) in zip(lst, lst[1:]):
            if 80 <= n1 - n0 <= 100 and e1 not in out:
                st = (D(e0) + dt.timedelta(days=1)).isoformat()
                out[e1] = (r1["val"] - r0["val"], r1["first"], st, r1["filed"])
    for s, e, r in ann:
        if e in out:
            continue
        inside = sorted(k for k, v in out.items() if v[2] >= s and k < e)
        if len(inside) == 3:
            st = (D(inside[-1]) + dt.timedelta(days=1)).isoformat()
            out[e] = (r["val"] - sum(out[k][0] for k in inside), r["first"], st, r["filed"])
    return out


def direct_quarters(rows):
    m = latest_by_period(rows)
    return {e: (r["val"], r["first"], s, r["filed"]) for (s, e), r in m.items() if s and 80 <= days(s, e) <= 100}


def annuals(rows):
    m = latest_by_period(rows)
    return {e: (r["val"], r["first"], s, r["filed"]) for (s, e), r in m.items() if s and 350 <= days(s, e) <= 380}


def instants(rows):
    m = latest_by_period(rows)
    return {e: (r["val"], r["first"], None, r["filed"]) for (s, e), r in m.items() if not s}


def merged(cf, names, fn, unit_pred=lambda u: u == "USD", adj=None):
    """多個候選科目先合併成同一組期間資料再推算（公司常換科目名稱，
    例如 9 個月累計與全年分屬不同科目時才能相減出 Q4）。
    同一期間：數值取「最新資料的科目」；公布日取所有科目中最早的申報日。
    adj(row) → 調整後數值（分割還原），在推算 Q4 之前先做"""
    raw = facts_of(cf, names, unit_pred)
    if adj:
        raw = {n: [dict(r, val=adj(r)) for r in rows] for n, rows in raw.items()}
    order = sorted(raw, key=lambda n: (max(r["end"] for r in raw[n]), len(raw[n])), reverse=True)
    owner, earliest = {}, {}
    for n in order:
        for r in raw[n]:
            k = (r.get("start"), r["end"])
            owner.setdefault(k, n)
            earliest[k] = min(earliest.get(k, r["filed"]), r["filed"])
    rows = []
    for n in order:
        rows += [r for r in raw[n] if owner[(r.get("start"), r["end"])] == n]
    # 補一筆「最早申報日」的影子資料：值與採用值相同，只用來讓公布日取到最早
    chosen = latest_by_period(rows)
    for k, r in chosen.items():
        if earliest[k] < r["first"]:
            rows.append(dict(r, filed=earliest[k]))
    return fn(rows)


def cal_label(start, end):
    mid = D(start) + (D(end) - D(start)) / 2
    return f"{str(mid.year)[2:]}Q{(mid.month - 1) // 3 + 1}"


def fiscal_label(end, fye):
    """fye：最近一次會計年度結束日；回傳 FY26Q1 這種會計季別"""
    if not fye:
        return ""
    e, a = D(end), D(fye)
    fy_end = dt.date(e.year, a.month, min(a.day, 28))
    if fy_end < e - dt.timedelta(days=10):  # 52/53 週制年底日期會前後飄幾天
        fy_end = dt.date(e.year + 1, a.month, min(a.day, 28))
    y = fy_end.year
    q = 4 - round((fy_end - e).days / 91.3)
    q = min(4, max(1, q))
    return f"FY{str(y)[2:]}Q{q}"


def build_fin(cik):
    cf = sec(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")
    splits = split_events(cf)
    usd = lambda u: u == "USD"
    ps = lambda u: "/" in u and u.upper().startswith("USD")
    sh = lambda u: u == "shares"

    rev = merged(cf, REV, quarters)
    revA = merged(cf, REV, annuals)
    freq = "Q"
    if len([e for e in rev if days(e, dt.date.today().isoformat()) < 800]) < 4 and len(revA) >= 2:
        freq = "A"  # 只交 20-F/40-F：沒有季報
    pick = quarters if freq == "Q" else annuals
    rev = rev if freq == "Q" else revA
    gp, cost = merged(cf, GP, pick), merged(cf, COST, pick)
    opi, ni = merged(cf, OPI, pick), merged(cf, NI, pick)
    eps = merged(cf, EPS, pick, ps, adj=lambda r: r["val"] / split_factor(r["filed"], splits))
    shr_adj = lambda r: r["val"] * split_factor(r["filed"], splits)
    # 股數不能相加減：只用單季（3 個月）原始值，Q4 用全年加權平均股數
    shr_q = merged(cf, SHR, direct_quarters, sh, adj=shr_adj)
    shr_a = merged(cf, SHR, annuals, sh, adj=shr_adj)
    shr = {**shr_a, **shr_q} if freq == "Q" else shr_a
    capex = merged(cf, CAPEX, pick)
    eq = merged(cf, EQ, instants)
    fyes = sorted(revA) or sorted(merged(cf, NI, annuals))
    fye = fyes[-1] if fyes else None

    rows = []
    for e in sorted(rev):
        r, filed, s, _ = rev[e]
        if not r or r <= 0:
            continue
        g = gp.get(e, (None,))[0]
        if g is None and e in cost:
            g = r - cost[e][0]
        n = ni.get(e, (None,))[0]
        ep = None
        if e in eps:
            ep = eps[e][0]
        shares = None
        if e in shr and shr[e][0]:
            shares = shr[e][0]
        if ep is None and n is not None and shares:
            ep = n / shares
        implied = n / ep if n and ep else None
        if shares is None or (implied and not 0.01 < abs(shares / implied) < 100):
            shares = implied or shares   # 申報股數與 淨利÷EPS 差上百倍（單位填錯）→ 用推算值
        pct = lambda v: None if v is None else round(v / r * 100, 1)
        cx = capex.get(e, (None,))[0]
        rows.append(dict(end=e, start=s, filed=filed, cal=cal_label(s, e) if freq == "Q" else f"FY{e[2:4]}",
                         fis=fiscal_label(e, fye) if freq == "Q" else f"FY{e[2:4]}",
                         rev=round(r / 1e6, 1), gm=pct(g), om=pct(opi.get(e, (None,))[0]), nm=pct(n),
                         eps=None if ep is None else round(ep, 3), sh=None if not shares else round(shares / 1e6, 2),
                         capex=None if cx is None else round(cx / 1e6, 1), ni=None if n is None else round(n / 1e6, 1)))
    eqs = sorted((e, v / 1e6, f) for e, (v, f, _, _) in eq.items())
    return dict(name=cf.get("entityName", ""), freq=freq, fye=fye, splits=splits, q=rows,
                eq=[[e, round(v, 1), f] for e, v, f in eqs if e >= rows[0]["end"][:4] + "-01-01"] if rows else [])


# ---------- 股價 ----------
def price_splits(px, splits):
    """FinMind 的 Close 若未做分割調整，在分割日附近會有 ≈1/n 的跳空 → 回傳需要除的因子"""
    fix = []
    for d, n in splits:
        lo = (D(d) - dt.timedelta(days=200)).isoformat()
        win = [r for r in px if lo <= r["date"] <= d]
        for a, b in zip(win, win[1:]):
            if a["Close"] and b["Close"]:
                ratio = a["Close"] / b["Close"]
                if abs(ratio - n) / n < 0.12:
                    fix.append((b["date"], n))
                    break
    return fix


def build(tk, cik_map, today=None):
    today = today or dt.date.today()
    cfg = CFG.get(tk, dict(theme="", flags="", tw=[]))
    cik = cik_map.get(tk)
    fin = build_fin(cik) if cik else dict(name="", freq="Q", fye=None, splits=[], q=[], eq=[])
    px = finmind("USStockPrice", tk, f"{today.year - YEARS}-01-01")
    for old in PRICE_ALIAS.get(tk, []):
        have = {r["date"] for r in px}
        px += [r for r in finmind("USStockPrice", old, f"{today.year - YEARS}-01-01") if r["date"] not in have]
    px = sorted([r for r in px if r.get("Close")], key=lambda r: r["date"])
    if not px:
        raise RuntimeError("FinMind 沒有股價")
    fix = price_splits(px, fin["splits"])
    for r in px:
        r["c"] = r["Close"] / split_factor(r["date"], [(d, n) for d, n in fix]) if fix else r["Close"]

    Q, EQS = fin["q"], fin["eq"]
    need = 4 if fin["freq"] == "Q" else 1

    def ttm_at(day):
        av = [q for q in Q if q["filed"] <= day and q["eps"] is not None]
        if len(av) < need:
            return None
        last = av[-need:]
        if fin["freq"] == "Q" and days(last[0]["end"], last[-1]["end"]) > 300:  # 中間缺季
            return None
        return round(sum(q["eps"] for q in last), 4)

    def bvps_at(day):
        av = [e for e in EQS if e[2] <= day]
        sh = [q["sh"] for q in Q if q["filed"] <= day and q["sh"]]
        if not av or not sh:
            return None
        return av[-1][1] / sh[-1]

    # 月底收盤
    mon = {}
    for r in px:
        mon[r["date"][:7]] = r
    riv = []
    for k in sorted(mon):
        r = mon[k]
        c, t, b = r["c"], ttm_at(r["date"]), bvps_at(r["date"])
        riv.append([k, round(c, 2), None if t is None else round(t, 3), None if b is None else round(b, 2),
                    round(c / t, 1) if t and t >= 0.01 else None, round(c / b, 2) if b and b > 0 else None])
    last_r, prev_r = px[-1], px[-2] if len(px) > 1 else px[-1]
    t, b = ttm_at(last_r["date"]), bvps_at(last_r["date"])
    last = dict(date=last_r["date"], close=round(last_r["c"], 2), prev=round(prev_r["c"], 2),
                ttm=None if t is None else round(t, 3), bvps=None if b is None else round(b, 2),
                pe=round(last_r["c"] / t, 1) if t and t >= 0.01 else None,
                pb=round(last_r["c"] / b, 2) if b and b > 0 else None)
    q = [[x["cal"], x["fis"], x["rev"], x["gm"], x["om"], x["nm"], x["eps"], x["capex"], x["sh"], x["end"], x["filed"]]
         for x in Q if x["end"] >= f"{today.year - YEARS - 1}-01-01"]
    note = []
    if not cik:
        note.append("SEC 查無此代號（可能剛上市尚未申報），沒有財報資料")
    if fin["freq"] == "A":
        note.append("外國發行人只交年報（20-F／40-F），財報為年度資料")
    elif cik and len(Q) < 4:
        note.append(f"上市不久，財報只有 {len(Q)} 季，歷史資料不足")
    if tk in PRICE_ALIAS:
        note.append("原代號 " + "、".join(PRICE_ALIAS[tk]) + "，股價歷史已合併")
    if fix:
        note.append("股價已依分割調整：" + "、".join(f"{d} 1拆{n}" for d, n in fix))
    elif fin["splits"]:
        note.append("EPS 已依分割調整：" + "、".join(f"{d[:7]} 1拆{n}" for d, n in fin["splits"]))
    return dict(id=tk, name=fin["name"], theme=cfg["theme"], cyclical="C" in cfg["flags"],
                demand="D" in cfg["flags"], tw=cfg["tw"], freq=fin["freq"], fye=fin["fye"], cik=cik,
                updated=dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"), last=last, q=q, riv=riv, note=note)


def main():
    ids = [a.upper() for a in sys.argv[1:]] or STOCKS
    OUT.mkdir(parents=True, exist_ok=True)
    tick = sec("https://www.sec.gov/files/company_tickers.json")
    cik_map = {v["ticker"].upper(): int(v["cik_str"]) for v in tick.values()}
    ok, bad = [], []
    for tk in ids:
        try:
            d = build(tk, cik_map)
            (OUT / f"{tk}.json").write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), "utf-8")
            lq = d["q"][-1] if d["q"] else None
            L = d["last"]
            ok.append(dict(id=tk, name=d["name"], theme=d["theme"], freq=d["freq"], n=len(d["q"]),
                           close=L["close"], chg=round((L["close"] / L["prev"] - 1) * 100, 2) if L["prev"] else None,
                           pe=L["pe"], pb=L["pb"], lq=lq[0] if lq else None, cyc=d["cyclical"], dem=d["demand"],
                           tw=d["tw"], date=L["date"]))
            print(f"{tk:5} ok  {d['name'][:28]:28} close={d['last']['close']} pe={d['last']['pe']} "
                  f"pb={d['last']['pb']} q={lq[0] if lq else '-'}({lq[1] if lq else ''}) rev={lq[2] if lq else '-'} "
                  f"eps={lq[6] if lq else '-'} {';'.join(d['note'])}")
        except Exception as e:
            bad.append(tk)
            print(f"{tk:5} FAILED: {e}", file=sys.stderr)
        time.sleep(0.5)
    idx = OUT / "index.json"
    old = json.loads(idx.read_text("utf-8")) if idx.exists() else []
    m = {s["id"]: s for s in old if s["id"] in CFG}
    m.update({s["id"]: s for s in ok})
    idx.write_text(json.dumps([m[t] for t in STOCKS if t in m], ensure_ascii=False), "utf-8")
    print(f"完成 {len(ok)}／{len(ids)}，失敗：{bad}")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
