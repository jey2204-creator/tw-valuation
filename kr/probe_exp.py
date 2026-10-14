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


# 樣本：2019～2025 每年 6 月 1～10 日、2023 年 6 月 1～20 日、各年 6 月確定值
pat = re.compile(r"1일\s*[~∼]\s*(?:\d+월\s*)?(10|20)일")
want = []
for y in range(2019, 2026):
    for x in allr:
        m = pat.search(x[2])
        if m and m[1] == "10" and (x[3] or "").startswith(f"{y}.06"):
            want.append(x); break
for x in allr:
    m = pat.search(x[2])
    if m and m[1] == "20" and (x[3] or "").startswith("2023.06"):
        want.append(x); break
for y in (2021, 2023, 2025, 2026):
    for x in allr:
        if "확정" in x[2] and (x[3] or "").startswith(f"{y}.07"):
            want.append(x); break
ten = want
sam = []
for x in ten:
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
            item["first"] = pages[0][:1500] if pages else None
            item["pages_semi"] = [[i, pg[:2600]] for i, pg in enumerate(pages) if "반 도 체" in pg or "반도체" in pg][-2:]
        hx = next((f for f in files if ".hwpx" in f[1].lower()), None)
        if hx and not pdf:
            import zipfile
            b = get(BASE + hx[0])
            z = zipfile.ZipFile(io.BytesIO(b))
            names = z.namelist()
            secs = [n for n in names if n.startswith("Contents/section")]
            txt = " ".join(re.sub(r"<[^>]+>", " ", z.read(n).decode("utf-8", "replace")) for n in secs)
            txt = re.sub(r"\s+", " ", txt)
            item["hwpx"] = {"names": names[:15], "semi": [txt[max(0, m.start() - 300): m.start() + 900] for m in re.finditer("반 ?도 ?체", txt)][:3]}
    except Exception as e:
        item["err"] = f"{type(e).__name__}: {str(e)[:200]}"
    sam.append(item)
    print("sample", item["row"], item.get("npages"), item.get("err"))
    time.sleep(0.5)
res["samples"] = sam
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
