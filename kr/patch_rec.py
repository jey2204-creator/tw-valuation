"""一次性：用現有快取（kr/data/earn/*.json、fin/*.json、各股 json 的 fr 日線）把「最近公布財報事件」rec 補進各股 json 與 index.json，不打網路。
之後 fetch_kr.py 每次更新都會自己帶 rec，這支只在改版時用。  用法：python kr/patch_rec.py"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_kr as F

idx_p = F.OUT / "index.json"
idx = {s["id"]: s for s in json.loads(idx_p.read_text("utf-8"))}
n = 0
for p in sorted(F.OUT.glob("[0-9]*.json")):
    c = p.stem
    d = json.loads(p.read_text("utf-8"))
    fp, ep = F.OUT / "fin" / f"{c}.json", F.OUT / "earn" / f"{c}.json"
    Q = F.quarters(json.loads(fp.read_text("utf-8"))) if fp.exists() else []
    # 暫定列（fin 第 16 欄 =1）正式快取裡沒有 → 從個股 json 的 fin 補回
    for r in d.get("fin") or []:
        if len(r) > 15 and r[15] and not any(x["cal"] == r[0] for x in Q):
            Q.append(dict(cal=r[0], rev=r[1], opa=r[6], nia=r[7], filed=(d.get("earn") or {}).get("pre"), pre=True))
    px = [dict(date=a, c=b) for a, b, _ in d.get("fr") or []]
    rec = F.recent_ann(json.loads(ep.read_text("utf-8")) if ep.exists() else {}, Q, px)
    d["rec"] = rec
    p.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), "utf-8")
    if c in idx:
        idx[c]["rec"] = rec
    n += 1
    print(c, d["name"], rec)
idx_p.write_text(json.dumps(list(idx.values()), ensure_ascii=False), "utf-8")
print("done", n)
