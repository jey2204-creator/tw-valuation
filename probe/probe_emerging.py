"""探測 FinMind 對興櫃股（預設 3595 山太士）的財報季別與數值。只讀。"""
import json, os, sys, urllib.request
sid = sys.argv[1] if len(sys.argv) > 1 else "3595"
tok = os.environ.get("FINMIND_TOKEN", "")
def get(ds, st):
    u = f"https://api.finmindtrade.com/api/v4/data?dataset={ds}&data_id={sid}&start_date={st}" + (f"&token={tok}" if tok else "")
    return json.load(urllib.request.urlopen(u, timeout=30)).get("data", [])
out = {}
fs = get("TaiwanStockFinancialStatements", "2018-01-01")
q = {}
for r in fs:
    if r["type"] in ("Revenue", "GrossProfit", "OperatingIncome", "EquityAttributableToOwnersOfParent", "EPS", "IncomeAfterTaxes"):
        q.setdefault(r["date"], {})[r["type"]] = r["value"]
out["fs"] = q
bs = get("TaiwanStockBalanceSheet", "2018-01-01")
out["bs"] = {r["date"]: {} for r in bs}
for r in bs:
    if r["type"] in ("OrdinaryShare", "CapitalStock", "EquityAttributableToOwnersOfParent", "TotalEquity", "Equity"):
        out["bs"][r["date"]][r["type"]] = r["value"]
px = get("TaiwanStockPrice", "2019-01-01")
out["px_n"] = len(px); out["px_first"] = px[0] if px else None
out["px_month_end"] = {}
for r in px: out["px_month_end"][r["date"][:7]] = r["close"]
rv = get("TaiwanStockMonthRevenue", "2018-01-01")
out["rv"] = {f'{r["revenue_year"]}-{r["revenue_month"]:02d}': r["revenue"] for r in rv}
os.makedirs("probe", exist_ok=True)
json.dump(out, open(f"probe/{sid}.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False)[:3000])
