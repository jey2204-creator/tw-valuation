"""美股員工薪資（比照台股 fetch_salary.py）→ us/data/salary.json
來源：SEC EDGAR
  DEF 14A（股東會說明書）Pay Ratio 段：員工年度總薪酬中位數（Median employee）、CEO 年度總薪酬、CEO÷中位數倍數
      ——Dodd-Frank 953(b)／Reg S-K Item 402(u)，2018 年起美國上市公司強制揭露；外國發行人（20-F，如 ARM、CAMT）不揭露
  10-K Item 1「Human Capital」段：員工人數（文字 regex，不在 XBRL）
  companyfacts：股票酬勞 ShareBasedCompensation（代替台股「薪資總額」，美股薪資費用幾乎沒人標）
口徑注意：美股中位數＝全球所有員工（含時薪、兼職、海外）的「總薪酬」（含股票），台股＝台灣非主管全時員工薪資。
輸出 d[代號] = {med 中位數USD, medPrev 前一年, medChg %, ceo CEO總薪酬USD, ratio 倍數, emp 員工人數, empDate, sbc 股票酬勞(億美元), sbcFY,
             fy 會計年度結束日, filed DEF14A申報日, acc, acc10k, fpi 外國發行人, url, miss 沒抓到的欄位}
快取：同一檔 DEF 14A／10-K 的 accession 沒變就不重抓（一年只真的抓一次）；抓失敗沿用上一版；內容沒變不寫檔。
手動修正：us/data/salary_override.json  {"NVDA": {"med": 123456}} 會覆蓋同名欄位（regex 抓錯時用）。
用法：python us/fetch_salary.py            # 全部 45 檔
     python us/fetch_salary.py NVDA AMZN  # 指定代號
環境變數：SEC_UA（SEC 要求的 User-Agent，需含聯絡 email）、FORCE=1 忽略快取全部重抓
只用 Python 標準函式庫。
"""
import json, os, re, sys, time, gzip, html, datetime as dt
from pathlib import Path
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_us import STOCKS, UA   # 追蹤清單與 User-Agent 跟 fetch_us.py 同一份

OUT = Path(__file__).resolve().parent / "data"
OUTF = OUT / "salary.json"
OVR = OUT / "salary_override.json"
FORCE = os.environ.get("FORCE") == "1"
FIELDS = ["med", "medPrev", "medChg", "ceo", "ratio", "emp", "empDate", "sbc", "sbcFY", "fy", "filed", "acc", "acc10k", "fpi", "url", "miss"]


def get(url, tries=3):
    time.sleep(0.15)  # SEC 上限每秒 10 次
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                b = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    b = gzip.decompress(b)
                return b
        except Exception as e:
            if i == tries - 1:
                raise RuntimeError(f"{url}: {e}")
            time.sleep(4 * (i + 1))


def getj(url):
    return json.loads(get(url))


def text_of(raw):
    """HTML → 純文字（去 script/style、標籤換空白、解 entity、壓空白）"""
    s = raw.decode("utf-8", "replace")
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s)


def num(s):
    try:
        return float(s.replace(",", ""))
    except Exception:
        return None


# ---------- DEF 14A：Pay Ratio ----------
MED_PATS = [
    r"(?:annual )?total compensation of (?:our |the )?median(?:[- ]compensated)? employee[^$]{0,160}?\$\s?(\d{1,3}(?:,\d{3})+|\d{4,7})(?![\d,])",
    r"median employee[^$]{0,160}?\$\s?(\d{1,3}(?:,\d{3})+|\d{4,7})(?![\d,])",
    r"median of the annual total compensation of (?:all )?(?:of )?(?:our |the )?employees[^$]{0,200}?\$\s?(\d{1,3}(?:,\d{3})+|\d{4,7})(?![\d,])",
    r"\$\s?(\d{1,3}(?:,\d{3})+|\d{4,7})(?![\d,])[^.]{0,80}?median employee",
]
CEO_PATS = [
    r"(?:annual )?total compensation of (?:our |the )?(?:Chief Executive Officer|CEO|President and Chief Executive Officer)[^$]{0,160}?\$\s?(\d{1,3}(?:,\d{3})+|\d{6,10})(?![\d,])",
    r"(?:Chief Executive Officer|CEO)[^$]{0,120}?annual total compensation[^$]{0,80}?\$\s?(\d{1,3}(?:,\d{3})+|\d{6,10})(?![\d,])",
]
RATIO_PATS = [
    r"ratio[^.]{0,200}?(\d[\d,]*(?:\.\d+)?)\s*(?:to|:|-to-|‑to‑)\s*(?:1|one)\b",
    r"(\d[\d,]*(?:\.\d+)?)\s*(?:to|:|-to-)\s*1\b[^.]{0,80}?ratio",
]


def pay_ratio_section(t):
    """從「pay ratio」標題附近開始找，避免抓到別處的 $ 數字；找不到就全篇"""
    best = None
    for m in re.finditer(r"(?i)pay ratio", t):
        win = t[m.start():m.start() + 8000]
        if re.search(r"(?i)median", win):
            best = m.start()
            break
    return t[best:best + 40000] if best is not None else t


def parse_def14a(t):
    sec = pay_ratio_section(t)
    out = {}
    for p in MED_PATS:
        for m in re.finditer("(?i)" + p, sec):
            v = num(m.group(1))
            if v and 8000 <= v <= 3_000_000:
                out["med"] = v
                break
        if "med" in out:
            break
    for p in CEO_PATS:
        for m in re.finditer("(?i)" + p, sec):
            v = num(m.group(1))
            if v and 100_000 <= v <= 1_000_000_000:
                out["ceo"] = v
                break
        if "ceo" in out:
            break
    for p in RATIO_PATS:
        for m in re.finditer("(?i)" + p, sec):
            v = num(m.group(1))
            if v and 1 <= v <= 20000:
                out["ratio"] = v
                break
        if "ratio" in out:
            break
    if out.get("ceo") and out.get("med") and out["ceo"] <= out["med"] * 1.5:
        out.pop("ceo")          # 抓到同一個數（句子順序顛倒），放棄 CEO
    if out.get("med") and out.get("ceo"):
        calc = out["ceo"] / out["med"]
        if "ratio" not in out or abs(out["ratio"] / calc - 1) > 0.35:
            out["ratio"] = round(calc)   # 文字倍數對不上 CEO÷中位數就用算的
    elif out.get("ratio") and out["ratio"] < 5 and not out.get("ceo"):
        out.pop("ratio")        # 沒 CEO 又倍數 <5，多半抓錯
    return out


# ---------- 10-K：員工人數 ----------
EMP_PATS = [
    r"(?:we |the company |[A-Z][\w.&]* )?(?:had|employed|employs?|employing)\s(?:a total of\s|approximately\s|about\s|over\s|more than\s|roughly\s)?(\d{1,3}(?:,\d{3})+|\d{2,7})\s(?:full[- ]time\s(?:and part[- ]time\s)?)?(?:regular\s)?(?:employees|people|team members|persons|individuals|associates|teammates)",
    r"(?:workforce|headcount|employee base|team)\s(?:of|was|were|totaled|consisted of)\s(?:approximately\s|about\s)?(\d{1,3}(?:,\d{3})+|\d{2,7})",
    r"(\d{1,3}(?:,\d{3})+|\d{2,7})\s(?:full[- ]time\s)?(?:employees|team members|people)\s(?:worldwide|globally|in \d+ countries|as of)",
    r"(?:employees|headcount|workforce)[^.]{0,60}?(?:was|were|totaled|of)\s(?:approximately\s|about\s)?(\d{1,3}(?:,\d{3})+|\d{2,7})",
    r"(?:approximately|about|over|more than)\s(\d{1,3}(?:,\d{3})+)\s(?:regular\s|global\s|full[- ]time\s)?(?:employees|people|team members|associates)",
    r"(?:employees|headcount)\s?[:|]?\s(\d{1,3}(?:,\d{3})+)\b",
]


def parse_10k(t):
    """先找 Human Capital 段，再全篇；取第一個合理數字（10 ≤ n ≤ 500 萬）"""
    zones = []
    for m in re.finditer(r"(?i)human capital", t):
        zones.append(t[m.start():m.start() + 6000])
    zones.append(t)
    for z in zones:
        for p in EMP_PATS:
            for m in re.finditer("(?i)" + p, z):
                v = num(m.group(1))
                if v and 10 <= v <= 5_000_000:
                    return v
    return None


# ---------- companyfacts：股票酬勞 ----------
def sbc_of(cik):
    try:
        cf = getj(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")
    except Exception:
        return None, None
    for tag in ("ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"):
        rows = cf.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {}).get("USD", [])
        fy = [r for r in rows if r.get("fp") == "FY" and r.get("form") in ("10-K", "10-K/A", "20-F") and r.get("start") and r.get("end")]
        fy = [r for r in fy if 300 <= (dt.date.fromisoformat(r["end"]) - dt.date.fromisoformat(r["start"])).days <= 380]
        if fy:
            r = max(fy, key=lambda r: (r["end"], r["filed"]))
            return round(r["val"] / 1e8, 2), r["end"]
    return None, None


# ---------- 單檔 ----------
def filings(cik):
    sub = getj(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
    rec = sub["filings"]["recent"]
    rows = [dict(form=f, acc=a, doc=d, filed=fd, rep=rd) for f, a, d, fd, rd in
            zip(rec["form"], rec["accessionNumber"], rec["primaryDocument"], rec["filingDate"], rec["reportDate"])]
    return sub.get("name", ""), rows


def doc_url(cik, acc, doc):
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{doc}"


def build(tk, cik, old):
    name, rows = filings(cik)
    px = [r for r in rows if r["form"] == "DEF 14A"]
    tenk = [r for r in rows if r["form"] in ("10-K", "20-F")] or [r for r in rows if r["form"] == "10-K/A"]
    fpi = not px and any(r["form"] in ("20-F", "40-F") for r in rows)
    d = dict(old or {})
    d["fpi"] = fpi
    miss = []
    if px:
        cur, prev = px[0], (px[1] if len(px) > 1 else None)
        if FORCE or d.get("acc") != cur["acc"] or "med" not in d:
            t = text_of(get(doc_url(cik, cur["acc"], cur["doc"])))
            p = parse_def14a(t)
            d.update(med=p.get("med"), ceo=p.get("ceo"), ratio=p.get("ratio"), filed=cur["filed"], acc=cur["acc"],
                     url=doc_url(cik, cur["acc"], cur["doc"]), fy=cur["rep"] or None, medPrev=None, medChg=None)
            if prev and p.get("med"):
                try:
                    pp = parse_def14a(text_of(get(doc_url(cik, prev["acc"], prev["doc"]))))
                    if pp.get("med"):
                        d["medPrev"] = pp["med"]
                        d["medChg"] = round((p["med"] / pp["med"] - 1) * 100, 1)
                except Exception as e:
                    print(f"  {tk} 前一年 DEF 14A 失敗：{e}")
    else:
        d.setdefault("med", None)
        miss.append("def14a" if not fpi else "fpi")
    if tenk:
        k = tenk[0]
        if FORCE or d.get("acc10k") != k["acc"] or "emp" not in d:
            emp = None
            for kk in tenk[:2]:   # 最新一份抓不到人數就試前一年的
                emp = parse_10k(text_of(get(doc_url(cik, kk["acc"], kk["doc"]))))
                if emp:
                    d["empDate"] = kk["rep"] or kk["filed"]
                    break
            d.update(emp=emp, acc10k=k["acc"])
            if not emp:
                d["empDate"] = None
    sbc, sbcfy = sbc_of(cik)
    d["sbc"], d["sbcFY"] = sbc, sbcfy
    for k in ("med", "ceo", "ratio", "emp", "sbc"):
        if d.get(k) is None and k not in miss:
            miss.append(k)
    d["miss"] = miss
    return {k: d.get(k) for k in FIELDS}


def main():
    want = [t.upper() for t in sys.argv[1:]] or STOCKS
    tick = getj("https://www.sec.gov/files/company_tickers.json")
    cik_map = {v["ticker"].upper(): int(v["cik_str"]) for v in tick.values()}
    old = {}
    if OUTF.exists():
        old = json.loads(OUTF.read_text(encoding="utf-8")).get("d", {})
    out = dict(old)
    for tk in want:
        cik = cik_map.get(tk)
        if not cik:
            print(f"{tk}: 找不到 CIK，略過")
            continue
        try:
            out[tk] = build(tk, cik, old.get(tk))
            r = out[tk]
            print(f"{tk}: 中位數 {r['med']}  CEO {r['ceo']}  倍數 {r['ratio']}  員工 {r['emp']}  SBC {r['sbc']}億  缺 {r['miss']}")
        except Exception as e:
            print(f"{tk}: 失敗，沿用上一版：{e}")
    if OVR.exists():
        for tk, patch in json.loads(OVR.read_text(encoding="utf-8")).items():
            if tk in out:
                out[tk].update(patch)
                out[tk]["miss"] = [m for m in out[tk]["miss"] if m not in patch]
    res = dict(updated=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), fields=FIELDS,
               note="med/ceo 美元；sbc 億美元；美股中位數＝全球所有員工總薪酬（含股票），與台股非主管全時口徑不同",
               d={k: out[k] for k in sorted(out)})
    if OUTF.exists():
        prev = json.loads(OUTF.read_text(encoding="utf-8"))
        if prev.get("d") == res["d"]:
            print("內容沒變，不寫檔")
            return
    OUT.mkdir(parents=True, exist_ok=True)
    OUTF.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    hit = sum(1 for v in res["d"].values() if v.get("med"))
    print(f"寫入 {OUTF}：{len(res['d'])} 檔，中位數命中 {hit} 檔")


if __name__ == "__main__":
    main()
