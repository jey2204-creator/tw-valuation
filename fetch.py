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
API = "https://api.finmindtrade.com/api/v4/data"
OUT = Path(__file__).resolve().parent / "data"
TOKEN = os.environ.get("FINMIND_TOKEN", "")


def get(dataset, sid, start):
    q = {"dataset": dataset, "data_id": sid, "start_date": start}
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


def build(sid, today=None, fetch=get):
    today = today or dt.date.today()
    start = f"{today.year - YEARS}-01-01"
    px = fetch("TaiwanStockPrice", sid, start)
    per = fetch("TaiwanStockPER", sid, start)
    fs = fetch("TaiwanStockFinancialStatements", sid, f"{today.year - YEARS - 1}-01-01")
    rv = fetch("TaiwanStockMonthRevenue", sid, f"{today.year - YEARS - 1}-01-01")
    bs = fetch("TaiwanStockBalanceSheet", sid, f"{today.year - 2}-01-01")
    info = fetch("TaiwanStockInfo", sid, "") if fetch is get else []

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
        if not all(k in o for k in want) or not o["Revenue"]:
            continue
        rv_ = o["Revenue"]
        q.append([f"{d[2:4]}Q{int(d[5:7]) // 3}", round(rv_ / 1e8),
                  round(o["GrossProfit"] / rv_ * 100, 1), round(o["OperatingIncome"] / rv_ * 100, 1),
                  round(o["EquityAttributableToOwnersOfParent"] / rv_ * 100, 1), round(o["EPS"], 2)])

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
                shares=round(shares, 4) if shares else None, last=last, rev=rev, q=q, riv=riv)


def main():
    ids = sys.argv[1:] or STOCKS
    OUT.mkdir(exist_ok=True)
    ok = []
    for sid in ids:
        try:
            d = build(sid)
            (OUT / f"{sid}.json").write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), "utf-8")
            ok.append({"id": sid, "name": d["name"]})
            print(f"{sid} {d['name']} ok  close={d['last']['close']} rev={d['rev'][-1][0]} q={d['q'][-1][0]}")
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
