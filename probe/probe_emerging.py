"""探測 FinMind 對興櫃股（預設 3595 山太士）有哪些資料集可用。只讀。"""
import json, os, sys, urllib.request
sid = sys.argv[1] if len(sys.argv) > 1 else "3595"
tok = os.environ.get("FINMIND_TOKEN", "")
out = {}
for ds, st in [("TaiwanStockInfo", ""), ("TaiwanStockPrice", "2026-09-01"), ("TaiwanStockPER", "2026-09-01"),
               ("TaiwanStockMonthRevenue", "2025-01-01"), ("TaiwanStockFinancialStatements", "2025-01-01"),
               ("TaiwanStockBalanceSheet", "2025-06-01"), ("TaiwanStockCashFlowsStatement", "2025-06-01"),
               ("TaiwanStockDividend", "2023-01-01")]:
    u = f"https://api.finmindtrade.com/api/v4/data?dataset={ds}&data_id={sid}" + (f"&start_date={st}" if st else "")
    if tok: u += f"&token={tok}"
    try:
        d = json.load(urllib.request.urlopen(u, timeout=30)); r = d.get("data", [])
        out[ds] = {"msg": d.get("msg"), "n": len(r), "first": r[0] if r else None, "last": r[-1] if r else None,
                   "dates": sorted({x.get("date") for x in r})[-6:]}
    except Exception as e:
        out[ds] = {"err": str(e)}
os.makedirs("probe", exist_ok=True)
json.dump(out, open(f"probe/{sid}.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1)[:6000])
