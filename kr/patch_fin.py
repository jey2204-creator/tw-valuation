"""一次性：用現有財報快取（kr/data/fin/*.json）把 fin 財報明細表補進各股 json，不打 OpenDART。
之後 fetch_kr.py 每次更新都會自己帶 fin，這支只在改版時用。  用法：python kr/patch_fin.py"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_kr as F

n = 0
for p in sorted(F.OUT.glob("[0-9]*.json")):
    c = p.stem
    fp = F.OUT / "fin" / f"{c}.json"
    if not fp.exists():
        continue
    cache = json.loads(fp.read_text("utf-8"))
    Q = F.quarters(cache)
    d = json.loads(p.read_text("utf-8"))
    d["fin"] = F.fin_rows(Q)
    p.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), "utf-8")
    n += 1
    print(c, len(Q), "季")
print("done", n)
