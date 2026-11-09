#!/usr/bin/env python3
"""全市場負債結構 → data/debt.json（掃描頁「負債」排序／篩選用）

每檔向 FinMind TaiwanStockBalanceSheet 要最近 400 天，取最新一季：
  有息負債 ＝ 短期借款＋應付短期票券＋一年內到期長期負債／公司債＋長期借款＋應付公司債＋租賃負債（中文科目名正則，與 index.html buildY10 的 dbt() 同一套）
  d[代號] = [季別, 負債比%, 有息負債比%(有息÷總資產), 淨負債／權益%(有息−現金 ÷ 母公司權益), 有息(億), 現金(億), 總負債(億), 抓取日 YYYYMMDD]
每次最多 REQ_MAX 檔：主題成份股先（超過 30 天沒更新的）、再補全市場沒抓過或超過 45 天的；FinMind 402（額度用完）就停、下次繼續。
"""
import json, os, re, sys, time, urllib.request, urllib.parse
from datetime import date, timedelta
from pathlib import Path

OUT = Path("data")
F = OUT / "debt.json"
REQ_MAX = int(os.environ.get("DEBT_MAX", "250"))
IBRE = re.compile(r"^(短期借款|應付短期票券|一年或一營業週期內到期(之)?(長期負債|長期借款|應付公司債)|一年內到期(之)?(長期負債|長期借款|應付公司債)|長期借款|應付公司債|租賃負債)")


def finmind(dataset, sid, start):
    q = urllib.parse.urlencode({"dataset": dataset, "data_id": sid, "start_date": start})
    req = urllib.request.Request("https://api.finmindtrade.com/api/v4/data?" + q)
    tok = os.environ.get("FINMIND_TOKEN", "")
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=60) as r:
        js = json.load(r)
    if js.get("status") == 402:
        raise RuntimeError("402")
    return js.get("data", [])


def calc(rows):
    """最新一季的負債結構；資料不足回 None"""
    if not rows:
        return None
    d = max(r["date"] for r in rows)
    R = [r for r in rows if r["date"] == d and r.get("value") is not None]
    g = lambda res: sum(r["value"] for r in R if res.match((r.get("origin_name") or "").strip()))
    one = lambda res, types: next((r["value"] for r in R if r.get("type") in types), None) or (g(res) or None)
    ta = one(re.compile(r"^資產總(計|額)$"), ("TotalAssets",))
    tl = one(re.compile(r"^負債總(計|額)$"), ("Liabilities", "TotalLiabilities"))
    eq = one(re.compile(r"^權益總(計|額)$"), ("Equity", "TotalEquity"))
    eqp = one(re.compile(r"^歸屬於母公司業主之權益(合計|總計)?$"), ("EquityAttributableToOwnersOfParent",)) or eq
    cash = one(re.compile(r"^現金及約當現金$"), ("CashAndCashEquivalents",))
    if not ta:
        return None
    if tl is None and eq is not None:
        tl = ta - eq
    if tl is None:
        return None
    ib = g(IBRE)
    y, m = int(d[:4]), int(d[5:7])
    q = f"{str(y)[2:]}Q{(m + 2) // 3}"
    e8 = lambda v: None if v is None else round(v / 1e8, 1)
    nd = None if cash is None else ib - cash
    return [q, round(tl / ta * 100, 1), round(ib / ta * 100, 1),
            None if nd is None or not eqp or eqp <= 0 else round(nd / eqp * 100, 1),
            e8(ib), e8(cash), e8(tl), date.today().strftime("%Y%m%d")]


def main():
    today = date.today()
    cur = {}
    if F.exists():
        try:
            cur = json.loads(F.read_text("utf-8")).get("d", {})
        except Exception:
            cur = {}
    lst = json.loads((OUT / "list.json").read_text("utf-8"))
    codes = [s[0] for s in lst if re.fullmatch(r"\d{4}", str(s[0]))]
    try:
        th = json.loads((OUT / "themes.json").read_text("utf-8"))["themes"]
        theme = {s[0] for t in th for s in t["stocks"]}
    except Exception:
        theme = set()
    try:
        j = json.loads((OUT / "itrust_top.json").read_text("utf-8"))
        theme |= {r["c"] for L in (j.get("lists") or {}).values() for r in L}
    except Exception:
        pass
    age = lambda c: 9999 if c not in cur or not cur[c] or len(cur[c]) < 8 else (today - date(int(cur[c][7][:4]), int(cur[c][7][4:6]), int(cur[c][7][6:]))).days
    todo = [c for c in codes if c in theme and age(c) > 30] + [c for c in codes if c not in theme and age(c) > 45]
    start = (today - timedelta(days=400)).isoformat()
    n_req = n_ok = n_none = 0
    stop = None
    for c in todo[:REQ_MAX]:
        try:
            rows = finmind("TaiwanStockBalanceSheet", c, start)
            n_req += 1
            v = calc(rows)
            if v:
                cur[c] = v
                n_ok += 1
            else:
                cur[c] = [None, None, None, None, None, None, None, today.strftime("%Y%m%d")]  # 沒資料也記抓取日，別每天重抓
                n_none += 1
        except RuntimeError as e:
            stop = "FinMind 額度用完（402）"
            break
        except Exception as e:
            n_req += 1
            print("fail", c, e, file=sys.stderr)
        time.sleep(0.3)
    have = sum(1 for v in cur.values() if v and v[0])
    out = {"asof": today.isoformat(), "n": have, "total": len(codes), "todo": max(0, len(todo) - n_req),
           "diag": {"req": n_req, "ok": n_ok, "none": n_none, "stop": stop}, "d": cur}
    F.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"debt: req={n_req} ok={n_ok} none={n_none} have={have}/{len(codes)} todo_left={out['todo']} stop={stop}")


if __name__ == "__main__":
    main()
