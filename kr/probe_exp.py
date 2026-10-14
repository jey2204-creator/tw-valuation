"""韓國出口數據探路 6：用 kr/hwp.py 解析各年度 HWP／HWPX／PDF 新聞稿 → kr/data/probe_exp.json"""
import json, os, re, sys, time, urllib.request, urllib.parse

sys.path.insert(0, os.path.dirname(__file__))
from hwp import any_text  # noqa: E402

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
OUT = os.path.join(os.path.dirname(__file__), "data", "probe_exp.json")
BASE = "https://www.customs.go.kr"
LIST = BASE + "/kcs/na/ntt/selectNttList.do?mi=2891&bbsId=1362"
res = {}


def get(url):
    h = {"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9", "Accept": "*/*", "Referer": LIST}
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=60) as r:
        return r.read()


def dec(b):
    for e in ("utf-8", "euc-kr", "cp949"):
        try:
            return b.decode(e)
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", "replace")


def rows(html):
    out = []
    for tr in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        a = re.search(r'data-id="(\d+)"\s+data-url="([^"]*)"[^>]*title="([^"]*)"', tr)
        d = re.search(r'data-table="date">([\d.]+)<', tr)
        if a:
            out.append([a[1], a[2], re.sub(r"\s+", " ", a[3]).strip(), d[1] if d else None])
    return out


try:
    kw = urllib.parse.quote("수출입")
    allr = []
    for pg in range(1, 8):          # 2022 年以後就夠
        allr += rows(dec(get(f"{LIST}&searchType=sj&searchValue={kw}&listCo=50&currPage={pg}")))
        time.sleep(0.3)
    pat = re.compile(r"1일\s*[~∼]\s*(?:\d+월\s*)?(10|20)일")


    def pick(pred):
        for x in allr:
            try:
                if pred(x):
                    return x
            except Exception:
                pass
        return None


    want = [
        pick(lambda x: (m := pat.search(x[2])) and m[1] == "10" and x[3].startswith("2023.06")),
        pick(lambda x: (m := pat.search(x[2])) and m[1] == "20" and x[3].startswith("2024.02")),
        pick(lambda x: (m := pat.search(x[2])) and m[1] == "10" and x[3].startswith("2025.06")),
        pick(lambda x: (m := pat.search(x[2])) and m[1] == "20" and x[3].startswith("2025.12")),
        pick(lambda x: (m := pat.search(x[2])) and m[1] == "10" and x[3].startswith("2026.01")),
        pick(lambda x: "확정" in x[2] and x[3].startswith("2023.07")),
        pick(lambda x: "확정" in x[2] and x[3].startswith("2026.09")),
    ]
    sam = []
    for x in [w for w in want if w]:
        item = {"row": [x[0], x[2], x[3]]}
        try:
            html = dec(get(f"{BASE}/kcs/na/ntt/selectNttInfo.do?mi=2891&bbsId=1362&nttSn={x[0]}&nttSnUrl={x[1]}"))
            files = re.findall(r'href="(/common/nttFileDownload\.do\?fileKey=\w+)"\s+title="([^"]+)"', html)
            item["files"] = [f[1] for f in files]
            # 優先 PDF → HWPX → HWP
            order = sorted(files, key=lambda f: [".pdf" in f[1].lower(), ".hwpx" in f[1].lower(), ".hwp" in f[1].lower()], reverse=True)
            f = order[0]
            b = get(BASE + f[0])
            t = time.time()
            txt = any_text(b, f[1])
            item["used"] = f[1]
            item["sec"] = round(time.time() - t, 2)
            item["len"] = len(txt)
            item["head"] = txt[:2500]
            item["semi"] = [txt[max(0, m.start() - 150): m.start() + 250] for m in re.finditer(r"반\s*도\s*체", txt)][:8]
            item["days"] = [txt[max(0, m.start() - 60): m.start() + 160] for m in re.finditer("조업일수", txt)][:3]
            # 也試 HWP（若剛剛用的是 PDF/HWPX，順便驗證 HWP 解析）
            hw = next((g for g in files if g[1].lower().endswith(".hwp 다운로드")), None)
            if hw and hw is not f:
                t2 = any_text(get(BASE + hw[0]), hw[1])
                item["hwp_check"] = [t2[max(0, m.start() - 100): m.start() + 200] for m in re.finditer(r"반\s*도\s*체", t2)][:3]
        except Exception as e:
            import traceback
            item["err"] = traceback.format_exc()[-600:]
        sam.append(item)
        print("sample", item["row"], item.get("used"), item.get("len"), item.get("err", "")[:200])
        time.sleep(0.5)
    res["samples"] = sam
except Exception:
    import traceback
    res["fatal"] = traceback.format_exc()[-1500:]
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "wb").write(json.dumps(res, ensure_ascii=False, indent=1).encode("utf-8", "replace"))
