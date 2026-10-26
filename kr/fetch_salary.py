"""韓股員工薪資（比照台股 fetch_salary.py、美股 us/fetch_salary.py）→ kr/data/salary.json
來源：OpenDART 定期報告主要資訊（年報 reprt_code=11011，每年 3 月底公布前一年度）
  empSttus.json             직원 현황：事業部門 × 性別分列的員工數、平均年資、年度薪資總額、1 人平均薪資
  unrstExctvMendngSttus.json 미등기임원 보수현황：非登記高管人數、1 人平均報酬
  indvdlByPay.json          개인별 보수지급 금액（5 億韓元以上前 5 名）：最高個人報酬
口徑：母公司本身（個別）全體員工，正職＋約聘（含短時間），薪資＝課稅所得口徑（含獎金、股票行權所得）；
     韓國只揭露「平均」，沒有中位數 → 對應台股的「全體員工薪資平均」（財報附註），不是非主管中位數。
     金控、控股公司（KB金融、新韓金融、SK Square…）母公司只有少數員工，平均值不代表整個集團。
輸出 d[代號] = {avg 平均薪資(韓元), avgPrev 前一年, avgChg %, emp 員工數, empPrev, ten 平均年資(年), tot 薪資總額(億韓元),
             ctr 約聘比例 %, m 男平均, f 女平均, exAvg 非登記高管平均, exN 人數, top 最高個人報酬, topNm 姓名, topPos 職位,
             yr 年度, rcept 申報日, url 原文, miss 沒抓到的}
快取：kr/data/salary_raw.json 存每家每年三支 API 的整理結果，已抓到就不重抓（年報公布後內容不變）；
     查無資料（013）的會每次重試，3～5 月新年報陸續公布時才有新的。內容沒變不寫檔。
用法：python kr/fetch_salary.py               # 全部追蹤清單
     python kr/fetch_salary.py 005930 000660 # 指定代號
環境變數：DART_KEY（必填）、FORCE=1 忽略快取全部重抓
只用 Python 標準函式庫。
"""
import json, os, re, sys, time, datetime as dt
from pathlib import Path
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_kr import STOCKS, CFG, KEY, http, corp_map   # 追蹤清單、金鑰、HTTP、公司代碼快取都跟 fetch_kr.py 同一份

OUT = Path(__file__).resolve().parent / "data"
OUTF = OUT / "salary.json"
RAW = OUT / "salary_raw.json"
DIAG = OUT / "salary_diag.json"
FORCE = os.environ.get("FORCE") == "1"
KST = dt.timezone(dt.timedelta(hours=9))
TODAY = dt.datetime.now(KST).date()
API = "https://opendart.fss.or.kr/api"
CALLS = []
CACHE_V = 2   # 快取格式改版就 +1（舊快取重抓）
EMP_KEYS = ("fo_bbm", "sexdstn", "sm", "rgllbr_co", "cnttk_co", "jan_salary_am", "fyer_salary_totamt", "avrg_cnwk_sdytrn", "rcept_no")


def num(v):
    if v is None:
        return None
    s = str(v).replace(",", "").replace(" ", "").strip()
    if s in ("", "-", "--", "－"):
        return None
    neg = s.startswith("(") and s.endswith(")") or s.startswith("△")
    s = s.strip("()△")
    try:
        x = float(s)
    except ValueError:
        return None
    return -x if neg else x


def dart(ep, corp, year):
    """→ list（查無資料回 []）"""
    q = urllib.parse.urlencode(dict(crtfc_key=KEY, corp_code=corp, bsns_year=year, reprt_code="11011"))
    t0 = time.time()
    j = http(f"{API}/{ep}.json?{q}", tries=3, timeout=60)
    st = j.get("status")
    CALLS.append([corp, ep, year, round(time.time() - t0, 1), st])
    if st == "013":
        return []
    if st != "000":
        raise RuntimeError(f"OpenDART {ep} {st} {j.get('message')}")
    time.sleep(0.2)
    return j.get("list") or []


TOTAL = re.compile(r"합\s*계|총\s*계|소\s*계|^전\s*체$|^계$|^total", re.I)


def unit_fix(avg, tot, n):
    """1 人平均、總額的單位五花八門（원／천원／백만원）：平均薪資合理範圍 1,500 萬～10 億韓元；總額用 平均×人數 對齊"""
    a = None
    if avg:
        for m in (1, 1e3, 1e6, 1e4):
            if 1.5e7 <= avg * m <= 1e9:
                a = avg * m
                break
    t = None
    if tot:
        if a and n:
            t = min((tot * m for m in (1, 1e3, 1e6, 1e4)), key=lambda x: abs(x / (a * n) - 1))
        else:
            t = tot * (1e6 if tot < 1e7 else 1)
    return a, t


def tenure(v):
    """平均年資：'14.0'／'8년 7개월'／'3년10개월\n(18년2개월)'（括號＝含集團年資，取第一個）→ 年"""
    if v is None:
        return None
    t = str(v).strip()
    m = re.search(r"(\d+(?:\.\d+)?)\s*년(?:\s*(\d+)\s*개월)?", t)
    if m:
        return float(m.group(1)) + (int(m.group(2)) / 12 if m.group(2) else 0)
    m = re.search(r"^(\d+)\s*개월", t)
    if m:
        return int(m.group(1)) / 12
    return num(t.split("\n")[0].split("(")[0])


def emp_summary(rows):
    """직원 현황：部門 × 性別分列 → 公司合計。各公司寫法不同：
      全公司合計列（합계／합계）、全公司分性別（성별합계 남／여，或部門欄寫 -）、分部門合計、部門 × 性別明細。
    每個指標各自取「第一組欄位齊全」的：合計列 → 全公司分性別 → 分部門 → 明細。
    平均薪資＝Σ薪資總額 ÷ Σ(薪資總額 ÷ 1人平均)（＝公司自己用的年平均人數）；只有平均就用人數加權；只有總額就 ÷ 年底人數"""
    R = []
    for x in rows:
        n = num(x.get("sm"))
        if n is None:
            n = sum(num(x.get(k)) or 0 for k in ("rgllbr_co", "cnttk_co")) or None
        avg, tot = unit_fix(num(x.get("jan_salary_am")), num(x.get("fyer_salary_totamt")), n)
        seg, sex = (x.get("fo_bbm") or "").strip(), (x.get("sexdstn") or "").strip()
        R.append(dict(seg=seg, sex=sex, n=n, avg=avg, tot=tot, ten=tenure(x.get("avrg_cnwk_sdytrn")),
                      ctr=num(x.get("cnttk_co")), rcept=(x.get("rcept_no") or ""),
                      st=bool(TOTAL.search(seg)) or seg in ("", "-"), xt=bool(TOTAL.search(sex)) or sex in ("", "-")))
    R = [r for r in R if r["n"]]
    if not R:
        return None
    sets = [[r for r in R if r["st"] and r["xt"]][:1],          # 全公司合計
            [r for r in R if r["st"] and not r["xt"]],          # 全公司分性別
            [r for r in R if not r["st"] and r["xt"]],          # 分部門合計
            [r for r in R if not r["st"] and not r["xt"]]]      # 明細
    sets = [x for x in sets if x]

    def avg_of(rs):
        if all(r["tot"] and r["avg"] for r in rs):
            return sum(r["tot"] for r in rs) / sum(r["tot"] / r["avg"] for r in rs)
        if all(r["avg"] for r in rs):
            return sum(r["avg"] * r["n"] for r in rs) / sum(r["n"] for r in rs)
        if all(r["tot"] for r in rs):
            return sum(r["tot"] for r in rs) / sum(r["n"] for r in rs)
        return None

    base = sets[0]
    out = dict(n=sum(r["n"] for r in base), ctr=sum(r["ctr"] or 0 for r in base), avg=None, tot=None, ten=None)
    for rs in sets:
        if out["avg"] is None:
            out["avg"] = avg_of(rs)
        if out["tot"] is None and all(r["tot"] for r in rs):
            out["tot"] = sum(r["tot"] for r in rs)
        if out["ten"] is None and all(r["ten"] is not None for r in rs):
            out["ten"] = sum(r["ten"] * r["n"] for r in rs) / sum(r["n"] for r in rs)
    # 男女平均：全公司分性別有薪資就用它，否則明細依性別加總
    for key, pat in (("m", r"^(남|男)"), ("f", r"^(여|女)")):
        out[key] = None
        for rs in ([r for r in R if r["st"] and not r["xt"]], [r for r in R if not r["st"] and not r["xt"]]):
            g = [r for r in rs if re.match(pat, r["sex"])]
            if g and avg_of(g):
                out[key] = avg_of(g)
                break
    out["rcept"] = next((r["rcept"] for r in R if r["rcept"]), "")
    return out


def exec_summary(rows):
    n = sum(num(x.get("nmpr")) or 0 for x in rows)
    if not rows or not n:
        return None
    x = rows[0] if len(rows) == 1 else max(rows, key=lambda r: num(r.get("nmpr")) or 0)
    avg, _ = unit_fix(num(x.get("jan_salary_am")), num(x.get("fyer_salary_totamt")), num(x.get("nmpr")))
    if avg is None:   # 平均欄常空白：總額 ÷ 人數
        tot = num(x.get("fyer_salary_totamt"))
        if tot and num(x.get("nmpr")):
            avg, _ = unit_fix(tot / num(x.get("nmpr")), None, None)
    return dict(n=int(n), avg=avg)


def top_summary(rows):
    best = None
    for x in rows:
        v = num(x.get("mendng_totamt"))
        if v is None:   # 欄名不同版本：找含 totamt 的欄位
            v = next((num(x[k]) for k in x if "totamt" in k and num(x[k])), None)
        if v is None:
            continue
        if v < 1e6:      # 百萬韓元
            v *= 1e6
        elif v < 1e8:    # 千韓元
            v *= 1e3
        if not best or v > best["v"]:
            best = dict(v=v, nm=(x.get("nm") or "").strip(), pos=(x.get("ofcps") or "").strip())
    return best


def year_data(corp, year, full):
    e = dart("empSttus", corp, year)
    d = dict(rows=[{k: x.get(k) for k in EMP_KEYS} for x in e], at=TODAY.isoformat(), v=CACHE_V)
    if full:
        d["ex"] = exec_summary(dart("unrstExctvMendngSttus", corp, year))
        d["top"] = top_summary(dart("indvdlByPay", corp, year))
    return d


def main():
    if not KEY:
        sys.exit("缺 DART_KEY")
    ids = [a for a in sys.argv[1:] if re.fullmatch(r"\d{6}", a)] or STOCKS
    corp = corp_map(ids)
    raw = json.loads(RAW.read_text("utf-8")) if RAW.exists() else {}
    y1 = TODAY.year - 1 if TODAY.month >= 4 else TODAY.year - 2   # 4 月前年報可能還沒到齊：先用再前一年
    y_try = [TODAY.year - 1, TODAY.year - 2, TODAY.year - 3] if TODAY.month < 4 else [y1, y1 - 1]
    diag, bad = {}, []
    for code in ids:
        if code not in corp:
            diag[code] = "不在 OpenDART 公司清單"
            continue
        cc = corp[code][0]
        r = raw.setdefault(code, {})
        t0 = time.time()
        try:
            got = []
            for i, y in enumerate(y_try):
                k = str(y)
                have = r.get(k)
                need_full = not got   # 最新一年才抓高管與個人報酬
                if FORCE or not have or have.get("v") != CACHE_V or not have.get("rows") or (need_full and "ex" not in have):
                    r[k] = year_data(cc, y, need_full)
                if r[k].get("rows"):
                    got.append(y)
                if len(got) == 2:
                    break
            diag[code] = dict(sec=round(time.time() - t0, 1), years=got,
                              emp=emp_summary(r[str(got[0])]["rows"]) if got else None)
            print(f"{code} {CFG[code]['zh']}: 年度 {got} {time.time() - t0:.0f}s")
        except Exception as e:
            bad.append(code)
            diag[code] = f"ERR {e}"[:300]
            print(f"{code} FAILED {e}", file=sys.stderr)
    RAW.write_text(json.dumps(raw, ensure_ascii=False, separators=(",", ":"), sort_keys=True), "utf-8")

    d = {}
    for code in STOCKS:
        r = raw.get(code) or {}
        ys = sorted((y for y in r if (r[y] or {}).get("rows") and emp_summary(r[y]["rows"])), reverse=True)
        if not ys:
            continue
        cur, prev = r[ys[0]], (r[ys[1]] if len(ys) > 1 and int(ys[1]) == int(ys[0]) - 1 else None)
        e, p = emp_summary(cur["rows"]), (emp_summary(prev["rows"]) if prev else None) or {}
        rd = lambda v, n=0: None if v is None else (round(v, n) if n else int(round(v)))
        o = dict(avg=rd(e.get("avg")), avgPrev=rd(p.get("avg")), emp=rd(e.get("n")), empPrev=rd(p.get("n")),
                 ten=rd(e.get("ten"), 1), tot=rd(e["tot"] / 1e8, 1) if e.get("tot") else None,
                 ctr=rd(e["ctr"] / e["n"] * 100, 1) if e.get("ctr") is not None and e.get("n") else None,
                 m=rd(e.get("m")), f=rd(e.get("f")), yr=int(ys[0]), rcept=e.get("rcept") or "")
        o["avgChg"] = rd((o["avg"] / o["avgPrev"] - 1) * 100, 1) if o["avg"] and o["avgPrev"] else None
        ex, top = cur.get("ex"), cur.get("top")
        if ex and ex.get("avg"):
            o["exAvg"], o["exN"] = rd(ex["avg"]), ex["n"]
        if top:
            o["top"], o["topNm"], o["topPos"] = rd(top["v"]), top["nm"], top["pos"]
        if o["rcept"]:
            o["url"] = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={o['rcept']}"
            o["filed"] = f"{o['rcept'][:4]}-{o['rcept'][4:6]}-{o['rcept'][6:8]}"
        o["miss"] = [k for k in ("avg", "emp", "ten", "exAvg", "top") if o.get(k) is None]
        d[code] = {k: v for k, v in o.items() if v not in (None, "", [])}
    out = dict(src="OpenDART 사업보고서 직원 현황／미등기임원 보수현황／개인별 보수지급 금액", unit="韓元", d=d)
    old = json.loads(OUTF.read_text("utf-8")) if OUTF.exists() else {}
    if {k: v for k, v in old.items() if k != "updated"} != out:
        out = dict(updated=dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M"), **out)
        OUTF.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
        print(f"寫入 salary.json：{len(d)} 檔")
    else:
        print("salary.json 沒變")
    DIAG.write_text(json.dumps(dict(at=dt.datetime.now(KST).isoformat(timespec="seconds"), years=y_try, calls=CALLS[-400:],
                                   d=diag), ensure_ascii=False, indent=1), "utf-8")
    print(f"完成 {len(d)}／{len(STOCKS)} 檔有資料，失敗：{bad}")
    if ids and len(bad) == len(ids):
        sys.exit(1)


if __name__ == "__main__":
    main()
