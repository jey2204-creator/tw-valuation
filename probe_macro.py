"""探路：主計總處 GDP 從 GitHub Actions 抓得到哪一種格式 → data/macro_probe.json（只存回應片段，給 Claude 調整 fetch_macro.py 用）"""
import json, re, time, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_macro import http, BUA

B = "https://nstatdb.dgbas.gov.tw/dgbasall/webMain.aspx"
C = []
for outmode in (0, 1, 2, 8):
    for cycle in (4, 3):
        C.append(f"{B}?sys=220&ym=10501&ymt=11504&kind=21&type=1&funid=A018101010&cycle={cycle}&outmode={outmode}&compmode=0&outkind=1&fldspc=0,40,&codspc0=0,10,&rdm=R1")
C += [f"{B}?sys=210&funid=A018101010",
      "https://www.stat.gov.tw/cp.aspx?n=2673",
      "https://ws.dgbas.gov.tw/public/data/open/Stat/NA/NA8101A1Q.xml",
      "https://www.stat.gov.tw/public/data/open/Stat/NA/NA8101A1Q.xml",
      "https://data.gov.tw/api/v2/rest/dataset/6799",
      "https://data.nat.gov.tw/api/v2/rest/dataset/6799"]
out = []
for u in C:
    t0 = time.time()
    st, raw = http(u, timeout=60, headers={"User-Agent": BUA, "Accept": "*/*", "Accept-Language": "zh-TW,zh;q=0.9"})
    txt = raw.decode("utf-8", "replace") if raw[:3] != b"PK\x03" else "(zip/xlsx)"
    i = txt.find("<table")
    tables = len(re.findall(r"<table", txt))
    links = sorted(set(re.findall(r'href="([^"]+\.(?:xlsx?|csv|ods|xml|json)[^"]*)"', txt)))[:40]
    out.append({"url": u, "status": st, "len": len(raw), "sec": round(time.time() - t0, 1), "tables": tables,
                "head": txt[:400], "table": txt[i:i + 4000] if i >= 0 else "", "links": links,
                "gdpHit": [m.start() for m in re.finditer("國內生產毛額", txt)][:5],
                "around": txt[max(0, txt.find("國內生產毛額") - 300):txt.find("國內生產毛額") + 1500] if "國內生產毛額" in txt else ""})
    time.sleep(2)
Path("data/macro_probe.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8")
print("\n".join(f"{o['status']} {o['len']} tables={o['tables']} {o['url'][:110]}" for o in out))
