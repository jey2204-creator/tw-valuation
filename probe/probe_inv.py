"""探路：抓幾檔的資產負債表／損益表／現金流量表原始科目，供存貨健康度卡開發用（開發完會刪）"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fetch import get
OUT = Path(__file__).resolve().parent / "inv"; OUT.mkdir(exist_ok=True)
IDS = ["2330", "6488", "2344", "3711", "2454", "2317", "2383", "1301", "2881", "3037", "2408", "8299"]
DS = {"bs": "TaiwanStockBalanceSheet", "fs": "TaiwanStockFinancialStatements", "cf": "TaiwanStockCashFlowsStatement"}
names = {}
for sid in IDS:
    o = {}
    for k, ds in DS.items():
        try:
            rows = get(ds, sid, "2018-01-01")
        except Exception as e:
            o[k] = {"err": str(e)}; continue
        o[k] = [[r["date"], r["type"], r.get("origin_name"), r["value"]] for r in rows if not r["type"].endswith("_per")]
        for r in o[k]:
            names.setdefault(k, {}).setdefault(r[1] + " | " + (r[2] or ""), set()).add(sid)
    (OUT / f"{sid}.json").write_text(json.dumps(o, ensure_ascii=False, separators=(",", ":")))
(OUT / "names.json").write_text(json.dumps({k: {n: sorted(s) for n, s in sorted(v.items())} for k, v in names.items()}, ensure_ascii=False, indent=0))
print("ok")
