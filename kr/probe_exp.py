"""韓國出口數據來源探路 4：關稅廳新聞稿（搜尋「수출입 현황」）全部標題＋各年度樣本 PDF 格式 → kr/data/probe_exp.json"""
import io, json, os, re, time, urllib.request, urllib.parse

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


kw = urllib.parse.quote("수출입")
allr, seen = [], set()
for pg in range(1, 60):
    try:
        r = rows(dec(get(f"{LIST}&searchType=sj&searchValue={kw}&listCo=50&currPage={pg}")))
    except Exception as e:
        res.setdefault("errs", []).append(f"page {pg}: {e}")
        break
    new = [x for x in r if x[0] not in seen]
    if not new:
        break
    for x in new:
        seen.add(x[0])
    allr += new
    time.sleep(0.4)
res["n"] = len(allr)
res["titles"] = [[x[0], x[2], x[3]] for x in allr]
print("titles", len(allr), allr[-1] if allr else None)


def pdf_pages(b):
    from pypdf import PdfReader
    return [p.extract_text() or "" for p in PdfReader(io.BytesIO(b)).pages]


# 樣本：每年挑 1～10 日、1～20 日各一篇（含最舊的）
pat = re.compile(r"1일\s*~\s*(?:\d+월\s*)?(10|20)일")
ten = [x for x in allr if pat.search(x[2])]
by = {}
for x in ten:
    y = (x[3] or "")[:4]
    k = (y, pat.search(x[2])[1])
    by.setdefault(k, x)          # 列表由新到舊 → 每組留最新的一篇
samples = sorted(by.values(), key=lambda x: x[3] or "")
samples = samples[:3] + samples[-2:] if len(samples) > 5 else samples
sam = []
for x in ten[-2:] + [s for s in samples if s not in ten[-2:]]:
    item = {"row": [x[0], x[2], x[3]]}
    try:
        html = dec(get(f"{BASE}/kcs/na/ntt/selectNttInfo.do?mi=2891&bbsId=1362&nttSn={x[0]}&nttSnUrl={x[1]}"))
        files = re.findall(r'href="(/common/nttFileDownload\.do\?fileKey=\w+)"\s+title="([^"]+)"', html)
        item["files"] = files
        pdf = next((f for f in files if ".pdf" in f[1].lower()), None)
        if pdf:
            b = get(BASE + pdf[0])
            item["magic"] = b[:5].decode("latin1")
            pages = pdf_pages(b) if b[:4] == b"%PDF" else []
            item["npages"] = len(pages)
            item["first"] = pages[0][:1800] if pages else None
            item["last"] = pages[-1][:1600] if pages else None
    except Exception as e:
        item["err"] = f"{type(e).__name__}: {str(e)[:200]}"
    sam.append(item)
    print("sample", item["row"], item.get("npages"), item.get("err"))
    time.sleep(0.5)
res["samples"] = sam
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
