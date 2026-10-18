"""從 FinMind 抓台股資料，輸出 data/{股票代號}.json 供網頁讀取。
用法：python fetch.py            # 抓 STOCKS 清單
     python fetch.py 2330 2344  # 指定代號
環境變數 FINMIND_TOKEN（選填）：有 token 可提高請求上限。
"""
import json, os, sys, time, datetime as dt
from pathlib import Path
import urllib.request, urllib.parse

STOCKS = ["2330", "2344", "6488"]   # 想追蹤的股票加在這裡
CYCLICAL = {"2344", "6488"}          # 景氣循環股：網頁會提醒以淨值比為主
YEARS = 6                  # 河流圖回溯年數
# 資本支出：現金流量表「取得不動產、廠房及設備」（優先比對中文科目名，其次英文 type）
CAPEX_NAMES = ("取得不動產、廠房及設備",)
CAPEX_TYPES = ("PropertyAndPlantAndEquipment", "AcquisitionOfPropertyPlantAndEquipment",
               "PaymentsToAcquirePropertyPlantAndEquipment")
DEP_NAMES = ("折舊費用",)
DEP_TYPES = ("Depreciation", "DepreciationExpense")
API = "https://api.finmindtrade.com/api/v4/data"
OUT = Path(__file__).resolve().parent / "data"
TOKEN = os.environ.get("FINMIND_TOKEN", "")


def get(dataset, sid, start):
    q = {k: v for k, v in {"dataset": dataset, "data_id": sid, "start_date": start}.items() if v}
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(q))
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                js = json.load(r)
            if js.get("status") not in (200, None) and not js.get("data"):
                raise RuntimeError(js.get("msg"))
            return js.get("data", [])
        except Exception as e:  # 重試
            if i == 2:
                raise RuntimeError(f"{dataset} {sid}: {e}")
            time.sleep(5 * (i + 1))


def month_last(rows, key):
    m = {}
    for r in sorted(rows, key=lambda r: r["date"]):
        m[r["date"][:7]] = r
    return m


def cf_item(rows, names, types):
    """從現金流量表取出單一科目 {日期: 金額絕對值}，中文科目名優先"""
    for ok in (lambda r: (r.get("origin_name") or "").strip() in names,
               lambda r: r.get("type") in types):
        d = {r["date"]: abs(r["value"]) for r in rows if ok(r) and r.get("value") is not None}
        if d:
            return d
    return {}


def to_quarter(d):
    """{日期: 值} → {(年, 季): 單季值}。台灣現金流量表多為年初至今累計，自動判斷後相鄰相減"""
    ys = {}
    for k, v in d.items():
        if k[5:] in ("03-31", "06-30", "09-30", "12-31"):
            ys.setdefault(int(k[:4]), {})[int(k[5:7]) // 3] = v
    ratio = sorted(y[4] / y[1] for y in ys.values() if 1 in y and 4 in y and y[1] > 0)
    cum = bool(ratio) and ratio[len(ratio) // 2] > 2.5   # 累計數：Q4 約為 Q1 的 4 倍
    out = {}
    for y, qs in ys.items():
        for n, v in qs.items():
            if not cum or n == 1:
                out[(y, n)] = v
            elif n - 1 in qs:
                out[(y, n)] = v - qs[n - 1]
    return out


def build_capex(cf, q):
    """[季別, 資本支出(億), 折舊(億或None), 資本支出÷營收(%)]，只保留有營收的季度"""
    cx = to_quarter(cf_item(cf, CAPEX_NAMES, CAPEX_TYPES))
    dp = to_quarter(cf_item(cf, DEP_NAMES, DEP_TYPES))
    out = []
    for lbl, rv_, *_ in q:
        k = (2000 + int(lbl[:2]), int(lbl[3]))
        if k in cx:
            c = cx[k] / 1e8
            out.append([lbl, round(c, 1), round(dp[k] / 1e8, 1) if k in dp else None,
                        round(c / rv_ * 100, 1) if rv_ else None])
    return out


def _ser(rows, types):
    """{日期: 值}，依序找第一個有資料的科目（保留正負號）"""
    for t in types:
        d = {r["date"]: r["value"] for r in rows if r.get("type") == t and r.get("value") is not None}
        if d:
            return d
    return {}


def to_quarter_signed(d):
    """同 to_quarter，但保留正負號（營業現金流可能為負）；用絕對值判斷是否為年初累計"""
    ys = {}
    for k, v in d.items():
        if k[5:] in ("03-31", "06-30", "09-30", "12-31"):
            ys.setdefault(int(k[:4]), {})[int(k[5:7]) // 3] = v
    ratio = sorted(abs(y[4]) / abs(y[1]) for y in ys.values() if 1 in y and 4 in y and y[1])
    cum = bool(ratio) and ratio[len(ratio) // 2] > 2.5
    out = {}
    for y, qs in ys.items():
        for n, v in qs.items():
            if not cum or n == 1:
                out[(y, n)] = v
            elif n - 1 in qs:
                out[(y, n)] = v - qs[n - 1]
    return out


def build_inv(bs, fs, cf, q):
    """存貨健康度：[季別, 存貨, 營業成本, 應收帳款(含關係人), 合約負債或None, 稅後淨利(合併), 單季營業現金流或None]（億）"""
    inv = _ser(bs, ("Inventories",))
    cogs = _ser(fs, ("CostOfGoodsSold",))
    ar, arr = _ser(bs, ("AccountsReceivableNet",)), _ser(bs, ("AccountsReceivableDuefromRelatedPartiesNet",))
    cl = _ser(bs, ("CurrentContractLiabilities",))
    ni = _ser(fs, ("IncomeAfterTaxes", "NetIncome"))
    ocf = to_quarter_signed(_ser(cf, ("CashFlowsFromOperatingActivities", "NetCashInflowFromOperatingActivities")))
    b = lambda v: None if v is None else round(v / 1e8, 2)
    out = []
    for lbl, *_ in q:
        y, n = 2000 + int(lbl[:2]), int(lbl[3])
        d = f"{y}-{('03-31', '06-30', '09-30', '12-31')[n - 1]}"
        if inv.get(d) is None or not cogs.get(d) or cogs[d] <= 0:
            continue
        a = ar.get(d)
        out.append([lbl, b(inv[d]), b(cogs[d]), b(None if a is None else a + (arr.get(d) or 0)),
                    b(cl.get(d)), b(ni.get(d)), b(ocf.get((y, n)))])
    return out


def build(sid, today=None, fetch=get):
    today = today or dt.date.today()
    start = f"{today.year - YEARS}-01-01"
    px = fetch("TaiwanStockPrice", sid, start)
    per = fetch("TaiwanStockPER", sid, start)
    fs = fetch("TaiwanStockFinancialStatements", sid, f"{today.year - YEARS - 1}-01-01")
    rv = fetch("TaiwanStockMonthRevenue", sid, f"{today.year - YEARS - 1}-01-01")
    bs = fetch("TaiwanStockBalanceSheet", sid, f"{today.year - YEARS - 1}-01-01")   # 存貨健康度要 20 季以上
    info = fetch("TaiwanStockInfo", sid, "") if fetch is get else []
    try:
        cf = fetch("TaiwanStockCashFlowsStatement", sid, f"{today.year - YEARS - 1}-01-01")
    except Exception as e:   # 現金流量表失敗不影響其他圖
        print(f"{sid} cashflow FAILED: {e}", file=sys.stderr)
        cf = []

    # 股數（億股）＝ 普通股股本 / 面額10元
    cap = [r for r in bs if r["type"] in ("OrdinaryShare", "CapitalStock")]
    cap.sort(key=lambda r: r["date"])
    shares = cap[-1]["value"] / 10 / 1e8 if cap else None

    # 月營收（億）+ 年增率
    rvd = {}
    for r in rv:
        rvd[f'{r["revenue_year"]}-{r["revenue_month"]:02d}'] = r["revenue"] / 1e8
    rev = []
    for k in sorted(rvd):
        y, m = k.split("-")
        p = rvd.get(f"{int(y) - 1}-{m}")
        rev.append([k, round(rvd[k]), round((rvd[k] / p - 1) * 100, 1) if p else None])
    rev = [r for r in rev if r[2] is not None]

    # 季財報：營收、毛利、營益、母公司淨利、EPS
    want = ["Revenue", "GrossProfit", "OperatingIncome", "EquityAttributableToOwnersOfParent", "EPS"]
    qd = {}
    for r in fs:
        if r["type"] in want:
            qd.setdefault(r["date"], {})[r["type"]] = r["value"]
    q = []
    for d in sorted(qd):
        o = qd[d]
        rv_, ni, eps = o.get("Revenue"), o.get("EquityAttributableToOwnersOfParent"), o.get("EPS")
        if eps is None and ni is not None and shares:   # 金融股財報沒有 EPS 欄位
            eps = ni / 1e8 / shares
        if not rv_ or eps is None:
            continue
        pct = lambda v: None if v is None else round(v / rv_ * 100, 1)
        q.append([f"{d[2:4]}Q{int(d[5:7]) // 3}", round(rv_ / 1e8),
                  pct(o.get("GrossProfit")), pct(o.get("OperatingIncome")), pct(ni), round(eps, 2)])

    # 月底股價 + PE/PB → 近四季EPS、每股淨值
    pm, em = month_last(px, "close"), month_last(per, "PER")
    riv = []
    for k in sorted(pm):
        if k not in em:
            continue
        c, pe, pb = pm[k]["close"], em[k]["PER"], em[k]["PBR"]
        riv.append([k, c, round(c / pe, 2) if pe else None, round(c / pb, 2) if pb else None, pe, pb])

    pxs = sorted(px, key=lambda r: r["date"])
    pers = sorted(per, key=lambda r: r["date"])
    last = dict(date=pxs[-1]["date"], close=pxs[-1]["close"],
                prev=pxs[-2]["close"] if len(pxs) > 1 else pxs[-1]["close"],
                pe=pers[-1]["PER"], pb=pers[-1]["PBR"])
    name = info[0].get("stock_name", "") if info else ""
    return dict(id=sid, name=name, cyclical=sid in CYCLICAL, updated=dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
                shares=round(shares, 4) if shares else None, last=last, rev=rev, q=q, riv=riv,
                capex=build_capex(cf, q), inv=build_inv(bs, fs, cf, q))


def build_list():
    """全部上市櫃普通股清單（給網頁搜尋用）：[代號, 名稱, 上市/上櫃, 產業]"""
    m = {}
    for s in get("TaiwanStockInfo", "", ""):
        sid = s.get("stock_id", "")
        if s.get("type") in ("twse", "tpex") and len(sid) == 4 and sid.isdigit() and sid[0] != "0":
            if sid not in m or s.get("date", "") > m[sid].get("date", ""):
                m[sid] = s
    rows = [[k, v["stock_name"], "上市" if v["type"] == "twse" else "上櫃", v.get("industry_category", "")]
            for k, v in sorted(m.items())]
    (OUT / "list.json").write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"list.json: {len(rows)} 檔")


def main():
    ids = sys.argv[1:] or STOCKS
    OUT.mkdir(exist_ok=True)
    try:
        build_list()
    except Exception as e:
        print(f"list FAILED: {e}", file=sys.stderr)
    ok = []
    for sid in ids:
        try:
            d = build(sid)
            (OUT / f"{sid}.json").write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), "utf-8")
            ok.append({"id": sid, "name": d["name"]})
            print(f"{sid} {d['name']} ok  close={d['last']['close']} rev={d['rev'][-1][0]} q={d['q'][-1][0]}"
                  f" capex={d['capex'][-1][:2] if d['capex'] else '無'}")
        except Exception as e:
            print(f"{sid} FAILED: {e}", file=sys.stderr)
        time.sleep(1)
    if ok:
        idx = OUT / "index.json"
        old = json.loads(idx.read_text("utf-8")) if idx.exists() else []
        merged = {s["id"]: s for s in old}
        merged.update({s["id"]: s for s in ok})
        idx.write_text(json.dumps(list(merged.values()), ensure_ascii=False), "utf-8")
    if len(ok) < len(ids):
        sys.exit(1)


if __name__ == "__main__":
    main()
