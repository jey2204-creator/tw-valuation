"""韓國出口數據來源探路（在 GitHub Actions 上跑）→ kr/data/probe_exp.json
測試：① KDI 經濟教育資訊中心轉載的關稅廳新聞稿 PDF  ② 關稅廳官網新聞稿列表  ③ 政策簡報 korea.kr
"""
import io, json, os, re, shutil, time, urllib.request, urllib.parse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
OUT = os.path.join(os.path.dirname(__file__), "data", "probe_exp.json")
res = {"pdftotext": shutil.which("pdftotext")}


def get(url, headers=None, data=None):
    h = {"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9", "Accept": "*/*"}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h, data=data)
    t = time.time()
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.status, r.read(), dict(r.headers), round(time.time() - t, 2)


def dec(b):
    for e in ("utf-8", "euc-kr", "cp949"):
        try:
            return b.decode(e)
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", "replace")


def snip(txt, kw, n=1500, maxhits=3):
    out = []
    for m in list(re.finditer(re.escape(kw), txt))[:maxhits]:
        out.append(txt[max(0, m.start() - 300): m.start() + n])
    return out


def probe(name, fn):
    try:
        res[name] = fn()
    except Exception as e:
        res[name] = {"err": f"{type(e).__name__}: {str(e)[:300]}"}
    print(name, json.dumps(res[name], ensure_ascii=False)[:300])


def pdf_text(b):
    from pypdf import PdfReader
    r = PdfReader(io.BytesIO(b))
    return [p.extract_text() or "" for p in r.pages]


def kdi(num):
    def f():
        s, b, h, t = get(f"https://eiec.kdi.re.kr/policy/materialView.do?num={num}")
        html = dec(b)
        title = re.search(r"<title>(.*?)</title>", html, re.S)
        links = sorted(set(re.findall(r"callDownload\.do\?[^\"'\s<>]+", html)))
        js = re.findall(r"(fn\w*[Dd]own\w*\([^)]*\))", html)[:5]
        out = {"status": s, "sec": t, "title": title[1].strip()[:200] if title else None, "links": links[:5], "js": js,
               "len": len(html)}
        if links:
            u = "https://eiec.kdi.re.kr/policy/" + links[0].replace("&amp;", "&")
            s2, b2, h2, t2 = get(u, {"Referer": f"https://eiec.kdi.re.kr/policy/materialView.do?num={num}"})
            out["dl"] = {"status": s2, "sec": t2, "ctype": h2.get("Content-Type"), "disp": h2.get("Content-Disposition"),
                         "size": len(b2), "magic": b2[:8].hex()}
            if b2[:4] == b"%PDF":
                pages = pdf_text(b2)
                out["pages"] = [p[:5000] for p in pages]
        return out
    return f


def customs():
    out = {}
    for name, url in [
        ("list", "https://www.customs.go.kr/kcs/na/ntt/selectNttList.do?mi=2891&bbsId=1362"),
        ("search", "https://www.customs.go.kr/kcs/na/ntt/selectNttList.do?mi=2891&bbsId=1362&searchCnd=1&searchKrwd="
         + urllib.parse.quote("수출입 현황")),
    ]:
        try:
            s, b, h, t = get(url)
            html = dec(b)
            out[name] = {"status": s, "sec": t, "len": len(html),
                         "titles": re.findall(r"[^>]{0,40}수출입 현황[^<]{0,60}", html)[:10],
                         "ntt": sorted(set(re.findall(r"nttSn[=\"':\s]+(\d+)", html)))[:20],
                         "snip": snip(html, "수출입 현황", 1200, 2)}
        except Exception as e:
            out[name] = {"err": str(e)[:200]}
    return out


def korea_kr():
    out = {}
    for name, url in [
        ("rss_kcs", "https://www.korea.kr/rss/dept_kcs.xml"),
        ("rss_customs", "https://www.korea.kr/rss/dept_customs.xml"),
        ("search", "https://www.korea.kr/briefing/pressReleaseList.do?srchKeyword=" + urllib.parse.quote("수출입 현황")),
    ]:
        try:
            s, b, h, t = get(url)
            txt = dec(b)
            out[name] = {"status": s, "sec": t, "len": len(txt), "ctype": h.get("Content-Type"),
                         "titles": re.findall(r"[^>]{0,40}수출입 현황[^<]{0,80}", txt)[:10],
                         "ids": sorted(set(re.findall(r"newsId=(\d+)", txt)))[:20], "head": txt[:600]}
        except Exception as e:
            out[name] = {"err": str(e)[:200]}
    return out


for n in (287971, 287232, 287667):
    probe(f"kdi_{n}", kdi(n))
probe("customs", customs)
probe("korea_kr", korea_kr)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
