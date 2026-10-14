"""韓國關稅廳出口數據 → kr/data/exports.json
來源：關稅廳官網新聞稿看板（customs.go.kr，搜尋「수출입」）
  ① 每月 1～10 日、1～20 日「수출입 현황」（잠정치，11 日／21 日上午 9 點公布）
     → 半導體出口金額與年增、總出口、工作天數（兩年）、前 10 大出口品項與國家
  ② 每月「월간 수출입 현황 [확정치]」（次月 15 日左右）→ 整月半導體出口（수리일 기준）
附件格式：2025 年底起有 PDF；更早是 HWP（部分有 HWPX）→ kr/hwp.py 轉文字
已解析過的新聞稿記在 exports.json 的 seen，不重複下載。
用法：python kr/fetch_exports.py [--pages N]   （第一次回補約 20 頁，之後每天看第 1 頁就夠）
需要：pip install pypdf olefile
"""
import datetime as dt, json, os, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hwp import any_text  # noqa: E402

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
BASE = "https://www.customs.go.kr"
LIST = BASE + "/kcs/na/ntt/selectNttList.do?mi=2891&bbsId=1362"
OUT = Path(__file__).resolve().parent / "data" / "exports.json"
START_TEN = "2021-01"      # 10 天數據從這個月開始回補
START_MON = "2019-01"      # 整月確定值從這個月開始
PARSE_V = 1                # 解析規則改版就 +1：舊的解析結果會重新下載解析
KST = dt.timezone(dt.timedelta(hours=9))


# ---------- 文字解析（純函式，可離線測試） ----------
NUM = r"△?-?\d[\d,]*(?:\.\d+)?"


def num(s):
    s = s.replace(",", "").replace("(", "").replace(")", "").strip()
    neg = s.startswith("△") or s.startswith("-")
    s = s.lstrip("△-")
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def period_of(title, posted):
    """標題 → (年, 月, 結束日)；結束日 10／20 為旬報，None 為整月"""
    t = re.sub(r"\s+", " ", title)
    y = re.search(r"(\d{4})\s*년", t)
    if y:
        year = int(y[1])
    else:
        y2 = re.search(r"[’'‘`](\d{2})\s*년", t)
        year = 2000 + int(y2[1]) if y2 else None
    m = re.search(r"(\d{1,2})\s*월", t)
    if not m:
        return None
    month = int(m[1])
    if year is None:   # 「6월 수출입 현황(확정치)」沒有年份：以公布日推算
        p = dt.date.fromisoformat(posted)
        year = p.year if month < p.month else p.year - 1
    e = re.search(r"1\s*일\s*[~∼\-－]\s*(?:\d{1,2}\s*월\s*)?(\d{1,2})\s*일", t)
    return year, month, int(e[1]) if e else None


def tokens(seg):
    """表格區段 → 依序的 (品名, 金額, 增減率) 三元組；品名可含空白（PDF 會把字拆開）"""
    toks = re.findall(rf"[가-힣][가-힣·ㆍ\s]*[가-힣]|[가-힣]|{NUM}", seg)
    out, i = [], 0
    while i + 2 < len(toks):
        a, b, c = toks[i], toks[i + 1], toks[i + 2]
        if re.match(r"[가-힣]", a) and re.fullmatch(NUM, b) and re.fullmatch(NUM, c):
            out.append([re.sub(r"\s+|주요품목|주요국가|금액|증감률", "", a), num(b), num(c)])
            i += 3
        else:
            i += 1
    return out


def two_tables(seg):
    """左右並排的「수출｜수입」表 → (出口列, 進口列)"""
    trip = tokens(seg)
    return trip[0::2], trip[1::2]


def parse_ten(text):
    """1～10 日／1～20 日新聞稿全文 → dict"""
    r = {}
    # 總出口：「통관기준」表格中「수 출」列的第 4 個金額（2 年前同期、去年累計、上月、當期、今年累計）
    i = text.find("통관기준")
    if i < 0:
        i = text.find("단위")
    seg = text[i:i + 1500]
    m = re.search(r"수\s+출(.*?)수\s+입", seg, re.S)
    if m:
        ints = [num(x) for x in re.findall(r"(?<![(\d.,△-])\d[\d,]*(?![\d.,]*\))", m[1])]
        pcts = [num(x) for x in re.findall(rf"\(\s*({NUM})\s*\)", m[1])]
        if len(ints) >= 4:
            r["tot"] = ints[3]
        if len(pcts) >= 4:
            r["tot_y"] = pcts[3]
    # 工作天數：조업일수 [(’25) 3.5 일, (’26) 5.5 일]
    m = re.search(r"조\s*업\s*일\s*수\s*\[?\s*\(\s*[’'‘`]?\s*(\d{2})\s*\)\s*([\d.]+)\s*일\s*,\s*\(\s*[’'‘`]?\s*(\d{2})\s*\)\s*([\d.]+)\s*일", text)
    if m:
        r["wd0"], r["wd"] = float(m[2]), float(m[4])
    # 附表：主要品項、主要國家（左＝出口、右＝進口）。表頭「주요품목 금액 증감률 주요품목 금액 증감률」之後才是資料
    hi = re.search(r"주요품목\s*금액\s*증감률\s*주요품목\s*금액\s*증감률", text)
    hc = re.search(r"주요국가\s*금액\s*증감률\s*주요국가\s*금액\s*증감률", text)
    if hi:
        stop = text.find("주요국가", hi.end())
        exp, imp = two_tables(text[hi.end(): stop if stop > 0 else len(text)])
        r["items"], r["imp"] = exp, imp
        semi = next((x for x in exp if x[0] == "반도체"), None)
        if semi:
            r["semi"], r["semi_y"] = semi[1], semi[2]
    if hc:
        stop = text.find("※", hc.end())
        exp, imp = two_tables(text[hc.end(): stop if stop > 0 else len(text)])
        r["cty"] = exp
    return r


def six_after(text, label_re, start, stop):
    """在 [start, stop) 找第一個 label，回傳其後 6 個數字"""
    m = re.search(label_re, text[start:stop])
    if not m:
        return None
    nums = re.findall(NUM, text[start + m.end(): start + m.end() + 400])
    return [num(x) for x in nums[:6]] if len(nums) >= 6 else None


def parse_month(text):
    """整月確定值新聞稿 → 半導體與總出口（수리일 기준，兩年同月＋年增，兩年累計＋年增）"""
    r = {}
    s = text.find("수리일 기준")
    s = text.find("수출 실적", s if s >= 0 else 0)
    if s < 0:
        s = 0
    e = text.find("수입 실적", s)
    e = e if e > s else len(text)
    v = six_after(text, r"\(\s*반\s*도\s*체\s*\)", s, e)
    if v and v[0] and abs((v[1] / v[0] - 1) * 100 - v[2]) < 0.3:
        r.update(semi0=v[0], semi=v[1], semi_y=v[2], semi_ytd0=v[3], semi_ytd=v[4])
    v = six_after(text, r"총\s*계", s, e)
    if v and v[0] and abs((v[1] / v[0] - 1) * 100 - v[2]) < 0.3:
        r.update(tot0=v[0], tot=v[1], tot_y=v[2])
    return r


# ---------- 網路 ----------
def get(url, tries=3):
    h = {"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9", "Accept": "*/*", "Referer": LIST}
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=60) as r:
                return r.read()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


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
        if a and d:
            out.append(dict(id=a[1], url=a[2], title=re.sub(r"\s+", " ", a[3]).strip(), posted=d[1].replace(".", "-")))
    return out


def kind(title):
    t = title.replace(" ", "")
    if "수출입" not in t or any(k in t for k in ("기업규모", "운송", "운임", "컨테이너", "특송", "전자상거래")):
        return None
    if re.search(r"1일[~∼\-－](?:\d{1,2}월)?(10|20)일", t):
        return "ten"
    if "확정" in t:
        return "mon"
    return None


def fetch_text(row):
    html = dec(get(f"{BASE}/kcs/na/ntt/selectNttInfo.do?mi=2891&bbsId=1362&nttSn={row['id']}&nttSnUrl={row['url']}"))
    files = re.findall(r'href="(/common/nttFileDownload\.do\?fileKey=\w+)"\s+title="([^"]+)"', html)
    files = [f for f in files if re.search(r"\.(pdf|hwpx|hwp)\s", f[1].lower() + " ")]
    files.sort(key=lambda f: (".pdf" in f[1].lower(), ".hwpx" in f[1].lower()), reverse=True)
    last = None
    for href, name in files:     # PDF → HWPX → HWP，解析失敗就換下一個
        try:
            return any_text(get(BASE + href), name), name
        except Exception as e:
            last = e
    raise RuntimeError(f"附件無法解析：{[f[1] for f in files]} {last}")


def main():
    pages = 1
    if "--pages" in sys.argv:
        pages = int(sys.argv[sys.argv.index("--pages") + 1])
    db = json.loads(OUT.read_text("utf-8")) if OUT.exists() else {}
    seen = db.get("seen", {})
    ten = {f"{x['ym']}-{x['d']}": x for x in db.get("p", [])}
    mon = {x["ym"]: x for x in db.get("m", [])}
    if not ten and pages < 20:
        pages = 25     # 第一次：回補歷史
    kw = urllib.parse.quote("수출입")
    cand = []
    for pg in range(1, pages + 1):
        rs = rows(dec(get(f"{LIST}&searchType=sj&searchValue={kw}&listCo=50&currPage={pg}")))
        if not rs:
            break
        cand += rs
        if rs[-1]["posted"] < START_MON + "-01":
            break
        time.sleep(0.3)
    n_new, errs = 0, []
    for row in reversed(cand):          # 舊 → 新，同一期間較新的新聞稿（更正）會覆蓋
        k = kind(row["title"])
        prev = seen.get(row["id"])
        if not k or (prev and prev.get("v") == PARSE_V):
            continue
        per = period_of(row["title"], row["posted"])
        if not per:
            continue
        y, mo, d = per
        ym = f"{y}-{mo:02d}"
        if (k == "ten" and ym < START_TEN) or (k == "mon" and ym < START_MON):
            continue
        try:
            text, fname = fetch_text(row)
            r = parse_ten(text) if k == "ten" else parse_month(text)
            ok = r.get("semi") is not None
            seen[row["id"]] = dict(v=PARSE_V, ok=ok, f=fname[-60:], title=row["title"][:60])
            if ok:
                r.update(ym=ym, rel=row["posted"], id=row["id"])
                if k == "ten":
                    r["d"] = d
                    ten[f"{ym}-{d}"] = r
                else:
                    mon[ym] = r
                n_new += 1
            else:
                errs.append([row["id"], row["title"][:40], "找不到半導體數字"])
        except Exception as e:
            errs.append([row["id"], row["title"][:40], str(e)[:120]])
            seen[row["id"]] = dict(v=0, ok=False, err=str(e)[:120], title=row["title"][:60])
        time.sleep(0.4)
    p = sorted(ten.values(), key=lambda x: (x["ym"], x["d"]))
    m = sorted(mon.values(), key=lambda x: x["ym"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(updated=dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"), p=p, m=m, seen=seen,
                                   errs=errs[-30:]), ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"旬報 {len(p)} 筆、整月 {len(m)} 筆，本次新增 {n_new}，錯誤 {len(errs)}")
    for x in errs[:10]:
        print("  ", x)
    if p:
        L = p[-1]
        print(f"最新：{L['ym']} 1～{L['d']} 日 半導體 {L['semi']:,.0f} 百萬美元（年增 {L['semi_y']}%），"
              f"總出口 {L.get('tot')}，工作天 {L.get('wd0')}→{L.get('wd')}")


if __name__ == "__main__":
    main()
