"""韓國出口數據來源探路 2：關稅廳官網新聞稿看板的分頁、搜尋、內文與附件 → kr/data/probe_exp.json"""
import json, os, re, time, urllib.request, urllib.parse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
OUT = os.path.join(os.path.dirname(__file__), "data", "probe_exp.json")
BASE = "https://www.customs.go.kr"
LIST = BASE + "/kcs/na/ntt/selectNttList.do?mi=2891&bbsId=1362"
res = {}


def get(url, headers=None, data=None):
    h = {"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9", "Accept": "*/*", "Referer": LIST}
    h.update(headers or {})
    if isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode()
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


def rows(html):
    """看板列表 → [(data-id, data-url, 標題, 日期)]"""
    out = []
    for tr in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        a = re.search(r'data-id="(\d+)"\s+data-url="([^"]*)"[^>]*title="([^"]*)"', tr)
        d = re.search(r'data-table="date">([\d.]+)<', tr)
        if a:
            out.append([a[1], a[2], a[3].strip(), d[1] if d else None])
    return out


def step(name, fn):
    try:
        res[name] = fn()
    except Exception as e:
        res[name] = {"err": f"{type(e).__name__}: {str(e)[:300]}"}
    print(name, json.dumps(res[name], ensure_ascii=False)[:400])


def p_list():
    s, b, h, t = get(LIST)
    html = dec(b)
    forms = re.findall(r"<form[^>]*>.*?</form>", html, re.S)
    inputs = sorted(set(re.findall(r'<(?:input|select)[^>]*name="([^"]+)"', html)))
    scripts = [x for x in re.findall(r"<script[^>]*>(.*?)</script>", html, re.S) if "nttInfoBtn" in x or "fn_" in x]
    jsfiles = re.findall(r'<script[^>]*src="([^"]+)"', html)
    return {"status": s, "sec": t, "rows": rows(html), "inputs": inputs, "form_heads": [f[:300] for f in forms][:4],
            "scripts": [x[:2500] for x in scripts][:3], "jsfiles": jsfiles[:30],
            "paging": re.findall(r"[^\n]{0,120}(?:currPage|pageIndex|goPage|fn_link_page|linkPage)[^\n]{0,120}", html)[:6]}


def p_pages():
    out = {}
    for prm in ("currPage=2", "pageIndex=2", "page=2", "pg=2"):
        try:
            s, b, h, t = get(LIST + "&" + prm)
            r = rows(dec(b))
            out[prm] = [r[0][:3] if r else None, len(r)]
        except Exception as e:
            out[prm] = str(e)[:100]
    return out


def p_search():
    out = {}
    kw = urllib.parse.quote("수출입 현황")
    for prm in (f"searchCnd=1&searchWrd={kw}", f"searchCnd=sj&searchWrd={kw}", f"srchWrd={kw}",
                f"searchKrwd={kw}&searchCnd=1", f"searchCondition=1&searchKeyword={kw}"):
        try:
            s, b, h, t = get(LIST + "&" + prm)
            r = rows(dec(b))
            out[prm] = [len(r), sum(1 for x in r if "수출입" in x[2]), [x[2][:30] for x in r[:3]]]
        except Exception as e:
            out[prm] = str(e)[:100]
    return out


def p_view():
    s, b, h, t = get(LIST)
    r = rows(dec(b))
    tgt = next((x for x in r if "1일 ~" in x[2] or "10일" in x[2]), r[0])
    out = {"target": tgt}
    for name, url in [
        ("info_nttSn", f"{BASE}/kcs/na/ntt/selectNttInfo.do?mi=2891&bbsId=1362&nttSn={tgt[0]}"),
        ("info_post", f"{BASE}/kcs/na/ntt/selectNttInfo.do"),
    ]:
        try:
            if name == "info_post":
                s, b, h, t = get(url, data={"mi": "2891", "bbsId": "1362", "nttSn": tgt[0]})
            else:
                s, b, h, t = get(url)
            html = dec(b)
            links = sorted(set(re.findall(r'(?:href|onclick|data-url|data-file\w*)="([^"]*(?:[Ff]ile|[Dd]own|atch|\.pdf|\.hwp)[^"]*)"', html)))
            out[name] = {"status": s, "sec": t, "len": len(html), "title": (re.search(r"<title>(.*?)</title>", html, re.S) or [0, ""])[1].strip()[:120],
                         "has_semi": "반도체" in html, "links": links[:20],
                         "file_snips": [html[max(0, m.start() - 200): m.start() + 400] for m in re.finditer(r"\.pdf|\.hwp", html)][:3]}
        except Exception as e:
            out[name] = str(e)[:200]
    return out


def p_titles():
    """前 8 頁的標題，看有哪些種類（10 天、20 天、月、確定值…）"""
    allr = []
    for pg in range(1, 9):
        try:
            s, b, h, t = get(LIST + f"&currPage={pg}")
            allr += rows(dec(b))
        except Exception as e:
            allr.append(["ERR", "", str(e)[:80], None])
        time.sleep(0.5)
    return [[x[0], x[2], x[3]] for x in allr]


step("list", p_list)
step("pages", p_pages)
step("search", p_search)
step("view", p_view)
step("titles", p_titles)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
