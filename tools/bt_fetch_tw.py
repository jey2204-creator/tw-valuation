#!/usr/bin/env python3
"""回測用：台股主題成份股 2020 起「月底還原收盤」→ tools/bt_data/tw_month.json（batch21 B，只在 Actions 跑）
先試 FinMind TaiwanStockPriceAdj（還原股價）；沒權限就用 TaiwanStockPrice＋TaiwanStockDividendResult 自己還原。
成份股＝data/themes.json 有 us 欄的主題裡的全部台股。只用標準函式庫。
"""
import json, os, sys, time, urllib.request, urllib.parse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
TOKEN = os.environ.get("FINMIND_TOKEN", "")
START = "2019-12-01"
OUT = ROOT / "tools/bt_data/tw_month.json"


def fm(dataset, sid, start=START):
    q = urllib.parse.urlencode({"dataset": dataset, "data_id": sid, "start_date": start})
    req = urllib.request.Request("https://api.finmindtrade.com/api/v4/data?" + q, headers={"Authorization": "Bearer " + TOKEN} if TOKEN else {})
    for k in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                j = json.loads(r.read())
            if j.get("status") == 200:
                return j.get("data") or []
            msg = j.get("msg", "")
            if "level" in msg.lower() or "permission" in msg.lower() or "sponsor" in msg.lower():
                return None   # 方案權限不足
            print(sid, dataset, j.get("status"), msg[:80], file=sys.stderr)
        except urllib.error.HTTPError as e:
            if e.code == 402:
                print("額度用完，等 10 分鐘", file=sys.stderr); time.sleep(600); continue
            if e.code in (400, 403):
                return None
            print(sid, dataset, "HTTP", e.code, file=sys.stderr)
        except Exception as e:
            print(sid, dataset, e, file=sys.stderr)
        time.sleep(3 * (k + 1))
    return []


def month_end(rows, key="close"):
    m = {}
    for r in rows:
        if r.get(key):
            m[r["date"][:7]] = [round(float(r[key]), 4), r["date"]]   # 依日期排序，最後一筆＝月底
    return [[k] + v for k, v in sorted(m.items())]


def main():
    th = json.loads((ROOT / "data/themes.json").read_text("utf-8"))["themes"]
    ids = sorted({c for t in th if t.get("us") for c, *_ in t["stocks"]})
    old = json.loads(OUT.read_text("utf-8")) if OUT.exists() else {"d": {}}
    out = {"src": None, "start": START, "d": old.get("d", {})}
    adj_ok = None
    for i, sid in enumerate(ids):
        if sid in out["d"] and len(out["d"][sid]) > 60 and "--force" not in sys.argv:
            continue
        rows = None
        if adj_ok is not False:
            rows = fm("TaiwanStockPriceAdj", sid)
            if rows is None:
                adj_ok = False; print("TaiwanStockPriceAdj 沒權限，改自己還原", file=sys.stderr)
            elif rows:
                adj_ok = True
        if adj_ok:
            out["src"] = "TaiwanStockPriceAdj"
            out["d"][sid] = month_end(rows)
        else:
            out["src"] = "TaiwanStockPrice+DividendResult"
            px = fm("TaiwanStockPrice", sid) or []
            dv = fm("TaiwanStockDividendResult", sid) or []
            # 還原因子：除權息日之前的價格 × (參考價 / 前一日收盤)
            ev = sorted((d["date"], float(d["after_price"]) / float(d["before_price"])) for d in dv
                        if d.get("before_price") and d.get("after_price") and float(d["before_price"]) > 0)
            for r in px:
                f = 1.0
                for ed, k in ev:
                    if r["date"] < ed:
                        f *= k
                r["adj"] = (r.get("close") or 0) * f
            out["d"][sid] = month_end(px, "adj")
        print(f"{i + 1}/{len(ids)} {sid} {len(out['d'][sid])} 月", flush=True)
        time.sleep(0.4)
        if (i + 1) % 40 == 0:
            OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(out, separators=(",", ":")), "utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":")), "utf-8")
    print("完成", out["src"], len(out["d"]))


if __name__ == "__main__":
    main()
