"""即時看線（itrust/live/）用的歷史日K：把每晚 itrust 日K workflow 產生的 itrust/kline/<D>.json 接進 itrust/live/hist.json。

每日檔多半只有「當月」的日K（db 已有的股票只補最近月份），所以頁面不能直接用；這裡每晚把新的那幾根併進來，
每檔保留最近 120 根日K、60 筆法人張數，加權指數收盤保留 80 筆。超過 40 個交易日沒再出現在名單聯集的股票會移除，控制檔案大小。
由 .github/workflows/itrust_live_hist.yml 在日K workflow 跑完後執行；只用 Python 標準函式庫；同一天重跑結果相同。
"""
import datetime as dt
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
KLINE = HERE.parent / "kline"
HIST = HERE / "hist.json"
KEEP_B, KEEP_I, KEEP_IDX, RETAIN = 120, 60, 80, 40


def merge(old, new, keep):
    m = {r[0]: r for r in (old or []) if r}
    for r in new or []:
        if r:
            m[r[0]] = r
    return [m[k] for k in sorted(m)][-keep:]


def body(h):
    return json.dumps({k: v for k, v in h.items() if k != "updatedAt"}, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def main():
    h = json.loads(HIST.read_text(encoding="utf-8"))
    before = body(h)
    files = [p for p in sorted(KLINE.glob("2???????.json")) if p.stem >= h["asOf"]]   # 只看每日檔；同一天也重併（排程重跑的修正）
    if not files:
        print(f"nothing to merge (hist asOf {h['asOf']})")
        return
    S = h["s"]
    for p in files:
        k = json.loads(p.read_text(encoding="utf-8"))
        mk = {}
        for spec in k.get("codes") or []:
            parts = str(spec).split(":")
            mk[parts[0]] = parts[1] if len(parts) > 1 else ""
        for c, bars in (k.get("bars") or {}).items():
            if not bars:
                continue
            e = S.setdefault(c, {"m": mk.get(c, ""), "b": [], "i": [], "x": []})
            if mk.get(c):
                e["m"] = mk[c]
            e["b"] = merge(e["b"], bars, KEEP_B)
        for c, rows in (k.get("inst") or {}).items():   # 抓失敗的代號不會出現在 inst，保留原本的
            if c in S and rows:
                S[c]["i"] = merge(S[c].get("i"), rows, KEEP_I)
        for c, rows in (k.get("ex") or {}).items():
            if c in S and rows:
                S[c]["x"] = merge(S[c].get("x"), rows, 999)
        tx = (k.get("idx") or {}).get("TAIEX") or []
        if tx:
            h.setdefault("idx", {})["TAIEX"] = merge(h.get("idx", {}).get("TAIEX"), tx, KEEP_IDX)
        h["asOf"] = max(h["asOf"], k.get("D") or p.stem)
        print(f"merged {p.name}: bars {len(k.get('bars') or {})} inst {len(k.get('inst') or {})} taiex {len(tx)}")
    dates = sorted({b[0] for e in S.values() for b in e["b"]})
    cutoff = dates[-RETAIN] if len(dates) >= RETAIN else (dates[0] if dates else "0")
    drop = [c for c, e in S.items() if not e["b"] or e["b"][-1][0] < cutoff]
    for c in drop:
        del S[c]
    for e in S.values():
        first = e["b"][0][0]
        e["x"] = [x for x in e.get("x") or [] if x[0] >= first]
        e["i"] = [x for x in e.get("i") or [] if x[0] >= first]
    if body(h) == before:   # 內容沒變就不寫，避免空提交
        print(f"unchanged asOf={h['asOf']} codes={len(S)}")
        return
    h["updatedAt"] = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y/%m/%d %H:%M")
    HIST.write_text(json.dumps(h, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"ok asOf={h['asOf']} codes={len(S)} dropped={len(drop)} bytes={HIST.stat().st_size}")


if __name__ == "__main__":
    main()
