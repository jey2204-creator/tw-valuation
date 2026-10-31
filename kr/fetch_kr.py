"""韓股估值看板：OpenDART 財報 + Naver 股價／外資持股比／法人共識 → kr/data/{代號}.json
用法：python kr/fetch_kr.py                 # 抓 STOCKS 全部
     python kr/fetch_kr.py 005930 000660   # 指定代號
環境變數：DART_KEY（OpenDART 認證金鑰，必填）
只用 Python 標準函式庫。

財報快取：kr/data/fin/{代號}.json 存每份定期報告抽出的科目，已抓過的報告不再重抓
（OpenDART 每次約 7 秒，6 年 × 4 份報告全抓一次要 3 分鐘）。
公司代碼快取：kr/data/corp.json（corpCode.xml 下載要 3.5 分鐘，只在清單缺代號時重抓）。
"""
import io, json, os, re, sys, time, zipfile, datetime as dt
from pathlib import Path
import urllib.request, urllib.parse

# ---------- 追蹤清單：主題 → [(代號, 中文名, 旗標)], [(台股代號, 名稱)] ----------
# 旗標：C = 循環股（以淨值比為主）
THEMES = [
    ("🎯 AI 晶片／記憶體", [("005930", "三星電子", "C"), ("000660", "SK海力士", "C")],
     [("2344", "華邦電"), ("2408", "南亞科"), ("8299", "群聯"), ("2337", "旺宏")]),
    ("🧱 先進封裝／設備", [("042700", "韓美半導體", ""), ("095340", "ISC", ""), ("058470", "利諾工業", ""),
                         ("089030", "泰克榮", ""), ("039030", "EO Technics", ""), ("240810", "圓益IPS", "C"),
                         ("036930", "周星工程", "C"), ("403870", "HPSP", "")],
     [("3711", "日月光投控"), ("2449", "京元電子"), ("3131", "弘塑"), ("6187", "萬潤"), ("6223", "旺矽"), ("6515", "穎崴")]),
    ("🟩 PCB／EMS", [("007660", "ISU Petasys", ""), ("011070", "LG Innotek", ""), ("353200", "大德電子", ""),
                    ("222800", "Simmtech", "C"), ("007810", "韓國電路", "")],
     [("2368", "金像電"), ("3037", "欣興"), ("8046", "南電"), ("4958", "臻鼎-KY"), ("2383", "台光電")]),
    ("⚡ 被動元件", [("009150", "三星電機", "")],
     [("2327", "國巨"), ("2492", "華新科"), ("3026", "禾伸堂")]),
    ("💿 矽晶圓／基板", [("011790", "SKC", ""), ("357780", "Soulbrain", ""), ("005290", "東進世美肯", "")],
     [("6488", "環球晶"), ("5483", "中美晶"), ("6182", "合晶")]),
    ("🔌 電力", [("267260", "HD現代電機", ""), ("010120", "LS電氣", ""), ("298040", "曉星重工業", ""),
               ("103590", "日進電氣", "")],
     [("1519", "華城"), ("1503", "士電"), ("1513", "中興電"), ("1514", "亞力")]),    # 市值前 20 大裡還沒追蹤的（2026-10 排行）。首頁不出內建卡片（前端 TID 沒有這個主題），只是讓它們有資料、能放進自建主題。
    # 三星電子特別股 005935 不加：OpenDART 只有普通股代號，財報與 005930 相同。金融股、控股公司以淨值比為主（標 C）。
    ("🏆 市值前20", [("402340", "SK Square", "C"), ("373220", "LG新能源", "C"), ("207940", "三星生物製劑", ""),
                   ("005380", "現代汽車", ""), ("105560", "KB金融", "C"), ("032830", "三星人壽", "C"),
                   ("028260", "三星物產", "C"), ("068270", "賽特瑞恩", ""), ("000270", "起亞", ""),
                   ("055550", "新韓金融", "C"), ("012450", "韓華航太", ""), ("006400", "三星SDI", "C"),
                   ("034020", "斗山能源", ""), ("034730", "SK", "C"), ("329180", "HD現代重工", ""),
                   ("086790", "韓亞金融", "C")],
     []),
]
CFG = {c: dict(theme=th, zh=zh, flags=f, tw=tw) for th, items, tw in THEMES for c, zh, f in items}
STOCKS = list(CFG)

YEARS = 6
OUT = Path(__file__).resolve().parent / "data"
KEY = os.environ.get("DART_KEY", "").strip()
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
KST = dt.timezone(dt.timedelta(hours=9))
TODAY = dt.datetime.now(KST).date()

# 報告代碼 → (季別, 季末月日, 法定申報期限天數)
STATS = []   # 每次 OpenDART 呼叫：[代號, 報告, 秒, 結果]
DEADLINE = time.time() + float(os.environ.get("KR_BUDGET_MIN", "45")) * 60   # 超過就先不抓新報告，下次排程接著補
CACHE_V = 3   # 抽取規則改版就 +1：舊版快取會重抓（v3：加營業現金流、股利、資產、負債、現金）
REPORTS = [("11013", 1, "03-31", 45), ("11012", 2, "06-30", 45), ("11014", 3, "09-30", 45), ("11011", 4, "12-31", 90)]


def http(url, data=None, headers=None, tries=3, timeout=60, raw=False):
    h = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "ko-KR,ko;q=0.9"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
                return b if raw else json.loads(b)
        except Exception as e:
            if i == tries - 1:
                raise RuntimeError(f"{url.split('?')[0]}: {e}")
            time.sleep(3 * (i + 1))


# ---------- 公司代碼 ----------
def corp_map(need):
    p = OUT / "corp.json"
    m = json.loads(p.read_text("utf-8")) if p.exists() else {}
    if all(c in m for c in need):
        return m
    print("下載 OpenDART 公司代碼清單（約 3～4 分鐘）…")
    b = http(f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={KEY}", raw=True, timeout=600)
    z = zipfile.ZipFile(io.BytesIO(b))
    xml = z.read(z.namelist()[0]).decode("utf-8")
    m = {}
    for blk in re.findall(r"<list>(.*?)</list>", xml, re.S):
        g = lambda t: (re.search(f"<{t}>([^<]*)</{t}>", blk) or [None, ""])[1].strip()
        if re.fullmatch(r"\d{6}", g("stock_code")):
            m[g("stock_code")] = [g("corp_code"), g("corp_name")]
    p.write_text(json.dumps(m, ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"公司代碼 {len(m)} 筆")
    return m


# ---------- OpenDART 財報 ----------
def num(s):
    if s is None:
        return None
    s = str(s).replace(",", "").strip()
    if s in ("", "-"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


ACC = {  # 科目：(報表, [標準科目 ID], [科目名稱（ID 找不到時用）])
    "rev": ("IS", ["ifrs-full_Revenue", "ifrs_Revenue"], ["매출액", "수익(매출액)", "영업수익", "매출", "수익"]),
    "cost": ("IS", ["ifrs-full_CostOfSales", "ifrs_CostOfSales"], ["매출원가", "영업비용"]),
    "gp": ("IS", ["ifrs-full_GrossProfit", "ifrs_GrossProfit"], ["매출총이익", "매출총이익(손실)"]),
    "op": ("IS", ["dart_OperatingIncomeLoss"], ["영업이익", "영업이익(손실)", "영업손익"]),
    "ni": ("IS", ["ifrs-full_ProfitLossAttributableToOwnersOfParent", "ifrs_ProfitLossAttributableToOwnersOfParent"],
           ["지배기업의 소유주에게 귀속되는 당기순이익", "지배기업 소유주지분", "지배기업소유주지분", "지배기업의 소유주지분"]),
    "nit": ("IS", ["ifrs-full_ProfitLoss", "ifrs_ProfitLoss"], ["당기순이익", "당기순이익(손실)", "분기순이익", "반기순이익"]),
    "eps": ("IS", ["ifrs-full_BasicEarningsLossPerShare", "ifrs_BasicEarningsLossPerShare"],
            ["기본주당이익", "기본주당이익(손실)", "보통주 기본주당이익", "기본주당순이익", "기본주당순이익(손실)"]),
    "eq": ("BS", ["ifrs-full_EquityAttributableToOwnersOfParent", "ifrs_EquityAttributableToOwnersOfParent"],
           ["지배기업의 소유주에게 귀속되는 자본", "지배기업 소유주지분", "지배기업소유주지분"]),
    "eqt": ("BS", ["ifrs-full_Equity", "ifrs_Equity"], ["자본총계"]),
    "capex": ("CF", ["ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
                     "ifrs_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"],
              ["유형자산의 취득", "유형자산취득", "유형자산의취득"]),
    # ---- v3 新增：財報明細頁（資產負債、現金流）；CF 為累計、BS 為期末餘額 ----
    "ocf": ("CF", ["ifrs-full_CashFlowsFromUsedInOperatingActivities", "ifrs_CashFlowsFromUsedInOperatingActivities"],
            ["영업활동현금흐름", "영업활동으로인한현금흐름", "영업활동으로 인한 현금흐름", "영업활동 현금흐름"]),
    "divp": ("CF", ["ifrs-full_DividendsPaidClassifiedAsFinancingActivities", "ifrs_DividendsPaidClassifiedAsFinancingActivities",
                    "dart_DividendsPaidClassifiedAsFinancingActivities"],
             ["배당금지급", "배당금의 지급", "배당금의지급", "배당금 지급", "현금배당금의 지급", "현금배당금지급"]),
    "assets": ("BS", ["ifrs-full_Assets", "ifrs_Assets"], ["자산총계"]),
    "liab": ("BS", ["ifrs-full_Liabilities", "ifrs_Liabilities"], ["부채총계"]),
    "cash": ("BS", ["ifrs-full_CashAndCashEquivalents", "ifrs_CashAndCashEquivalents"], ["현금및현금성자산", "현금 및 현금성자산"]),
}


def extract(lst):
    """從 fnlttSinglAcntAll 的 list 抽出需要的科目。
    損益表：thstrm_amount = 單季（年報為全年）、thstrm_add_amount = 累計；
    現金流量表：thstrm_amount = 累計；資產負債表：期末餘額"""
    by = {}
    for x in lst:
        sj = x.get("sj_div")
        by.setdefault("IS" if sj in ("IS", "CIS") else sj, []).append(x)
    # 損益表優先用 IS，沒有才用 CIS（綜合損益表），避免抓到「綜合損益歸屬母公司」
    if any(x.get("sj_div") == "IS" for x in by.get("IS", [])):
        by["IS"] = [x for x in by["IS"] if x.get("sj_div") == "IS"]
    out = {}
    for k, (sj, ids, names) in ACC.items():
        rows = by.get(sj, [])
        hit = [x for x in rows if x.get("account_id") in ids]
        if not hit:
            hit = [x for x in rows if re.sub(r"\s", "", x.get("account_nm", "")) in [re.sub(r"\s", "", n) for n in names]
                   and "Comprehensive" not in (x.get("account_id") or "")]
        if not hit and k == "eps":   # 名稱五花八門（보통주기본주당순이익…）：找含「기본」「주당」的列
            hit = [x for x in rows if "BasicEarnings" in (x.get("account_id") or "")
                   or ("기본" in x.get("account_nm", "") and "주당" in x.get("account_nm", ""))]
        if k == "eps" and len(hit) > 1:   # 普通股／特別股各一列 → 取普通股
            hit = sorted(hit, key=lambda x: (0 if "보통주" in x.get("account_nm", "") else 1,
                                             1 if "우선주" in x.get("account_nm", "") else 0))
        if not hit:
            continue
        x = hit[0]
        out[k] = num(x.get("thstrm_amount"))
        if sj == "IS":
            out[k + "_c"] = num(x.get("thstrm_add_amount"))
    out["rcept"] = (lst[0].get("rcept_no") or "")[:8] if lst else ""
    out["v"] = CACHE_V
    return out


def dart_report(corp, year, rc):
    for fs in ("CFS", "OFS"):
        q = urllib.parse.urlencode(dict(crtfc_key=KEY, corp_code=corp, bsns_year=year, reprt_code=rc, fs_div=fs))
        j = http(f"https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json?{q}", tries=2, timeout=40)
        st = j.get("status")
        if st == "000":
            if os.environ.get("KR_DEBUG") and year == TODAY.year - 1 and rc == "11012":
                (OUT / "debug").mkdir(exist_ok=True)
                (OUT / "debug" / f"{corp}_{year}_{rc}.json").write_text(json.dumps(
                    [{k: x.get(k) for k in ("sj_div", "account_id", "account_nm", "thstrm_nm", "thstrm_amount",
                      "thstrm_add_amount")} for x in j.get("list", []) if x.get("sj_div") in ("IS", "CIS")],
                    ensure_ascii=False, indent=0), "utf-8")
            d = extract(j.get("list", []))
            d["fs"] = fs
            return d
        if st != "013":   # 013 = 查無資料；其他（金鑰、超過上限）直接報錯
            raise RuntimeError(f"OpenDART {st} {j.get('message')}")
        time.sleep(0.3)
    return None


def fin_cache(code, corp):
    p = OUT / "fin" / f"{code}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    cache = json.loads(p.read_text("utf-8")) if p.exists() else {}
    todo = []
    for y in range(TODAY.year - YEARS, TODAY.year + 1):
        for rc, qn, md, due in REPORTS:
            k = f"{y}-{rc}"
            if k in cache and cache[k] is not None and (cache[k] == {} or cache[k].get("v") == CACHE_V):
                continue
            end = dt.date.fromisoformat(f"{y}-{md}")
            if TODAY < end + dt.timedelta(days=14):     # 還沒到可能公布的時間
                continue
            todo.append((k, y, rc, end, due))
    n_new = 0
    for k, y, rc, end, due in todo:
        if time.time() > DEADLINE:
            break
        n_new += 1
        t0 = time.time()
        try:
            d = dart_report(corp, y, rc)
            STATS.append([code, k, round(time.time() - t0, 1), "ok" if d else "none"])
        except Exception as e:
            STATS.append([code, k, round(time.time() - t0, 1), str(e)[:80]])
            if "OpenDART 0" in str(e) or "OpenDART 1" in str(e) or "OpenDART 9" in str(e):
                raise
            continue
        if d is None:
            # 超過法定期限 + 60 天仍查無資料（上市前、或不申報）→ 記成空的，以後不再查
            if TODAY > end + dt.timedelta(days=due + 60):
                cache[k] = {}
        else:
            cache[k] = d
        p.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":"), sort_keys=True), "utf-8")
    pending = len(todo) - n_new   # 因時間上限沒抓到的報告數
    p.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":"), sort_keys=True), "utf-8")
    return cache, (n_new, pending)


def quarters(cache):
    """財報快取 → 單季資料列（季末日排序）"""
    rows = []
    for y in range(TODAY.year - YEARS, TODAY.year + 1):
        R = {qn: cache.get(f"{y}-{rc}") or None for rc, qn, md, due in REPORTS}
        for rc, qn, md, due in REPORTS:
            r = R[qn]
            # 金融股（銀行、壽險、金控）損益表沒有「營收」科目：有淨利就照收，營收／利潤率留空，EPS、淨值照算
            fin = r is not None and r.get("rev") is None and (r.get("ni") is not None or r.get("nit") is not None)
            if not r or (r.get("rev") is None and not fin):
                continue
            v = {}
            if qn < 4:
                for k in ("rev", "cost", "gp", "op", "ni", "nit", "eps"):
                    v[k] = r.get(k)
                prev = R.get(qn - 1)
                for k in ("capex", "ocf", "divp"):
                    c, pc = r.get(k), (prev or {}).get(k)
                    v[k] = c if qn == 1 else (c - pc if c is not None and pc is not None else None)
            else:
                r3, parts = R.get(3), [R.get(1), R.get(2), R.get(3)]
                for k in ("rev", "cost", "gp", "op", "ni", "nit", "eps"):
                    fy = r.get(k)
                    cum = (r3 or {}).get(k + "_c")
                    if cum is None and all(p and p.get(k) is not None for p in parts):
                        cum = sum(p[k] for p in parts)
                    v[k] = fy - cum if fy is not None and cum is not None else None
                for k in ("capex", "ocf", "divp"):
                    c, pc = r.get(k), (r3 or {}).get(k)
                    v[k] = c - pc if c is not None and pc is not None else None
            if not fin and (not v["rev"] or v["rev"] <= 0):
                continue
            if fin:
                v["rev"] = v["gp"] = v["cost"] = None
            if not fin and v["gp"] is None and v["cost"] is not None and r.get("gp") is None:
                # 沒有毛利科目（金融、服務業常見）：以營收 − 營業成本推算，但營業成本 = 營業費用全部時不算
                if r.get("op") is None or abs((v["rev"] - v["cost"]) - (v["op"] or 0)) > 1:
                    v["gp"] = v["rev"] - v["cost"]
            ni = v["ni"] if v["ni"] is not None else v["nit"]
            eq = r.get("eq") if r.get("eq") is not None else r.get("eqt")
            sh = ni / v["eps"] if ni and v["eps"] and qn < 4 else None
            if qn == 4 and r.get("eps") and (r.get("ni") or r.get("nit")):
                sh = (r.get("ni") if r.get("ni") is not None else r.get("nit")) / r["eps"]   # 年報：全年淨利 ÷ 全年 EPS
            pct = lambda x: None if x is None or not v["rev"] else round(x / v["rev"] * 100, 1)
            f = r.get("rcept") or ""
            rows.append(dict(cal=f"{str(y)[2:]}Q{qn}", end=f"{y}-{md}",
                             filed=f"{f[:4]}-{f[4:6]}-{f[6:8]}" if len(f) == 8 else f"{y}-{md}",
                             rev=None if v["rev"] is None else round(v["rev"] / 1e8, 1), gm=pct(v["gp"]), om=pct(v["op"]), nm=pct(ni),
                             eps=None if v["eps"] is None else round(v["eps"], 1),
                             capex=None if v["capex"] is None else round(v["capex"] / 1e8, 1),
                             sh=None if not sh or sh <= 0 else round(sh / 1e6, 2),
                             eq=None if eq is None else round(eq / 1e8, 1), fs=r.get("fs"), ni=ni,
                             # 財報明細（億韓元）：營業利益、母公司淨利、營業現金流、股利發放（取絕對值）、總資產、總負債、現金
                             opa=None if v["op"] is None else round(v["op"] / 1e8, 1),
                             nia=None if ni is None else round(ni / 1e8, 1),
                             ocf=None if v.get("ocf") is None else round(v["ocf"] / 1e8, 1),
                             divp=None if v.get("divp") is None else round(abs(v["divp"]) / 1e8, 1),
                             assets=None if r.get("assets") is None else round(r["assets"] / 1e8, 1),
                             liab=None if r.get("liab") is None else round(r["liab"] / 1e8, 1),
                             cash=None if r.get("cash") is None else round(r["cash"] / 1e8, 1)))
    # 股票分割／合併：股數（淨利 ÷ EPS）相鄰兩季跳成整數倍 → 之前各季 EPS、股數依倍數調整（Naver 股價已還原）
    near = lambda u, v: u and v and abs(u / v - 1) < 0.05
    for i in range(1, len(rows)):
        a, b = rows[i - 1]["sh"], rows[i]["sh"]
        if not a or not b:
            continue
        # 要前後各一季佐證（股數維持在新／舊水準），避免小額淨利÷EPS 的雜訊誤判；最新一季則只看前面
        prev2 = next((x["sh"] for x in reversed(rows[:i - 1]) if x["sh"]), None)
        nxt = next((x["sh"] for x in rows[i + 1:] if x["sh"]), None)
        if not near(prev2, a) or (nxt is not None and not near(nxt, b)):
            continue
        for ratio, inv in ((b / a, False), (a / b, True)):
            n = round(ratio)
            if n >= 2 and abs(ratio - n) / n < 0.05:
                for x in rows[:i]:
                    f = (1 / n) if inv else n
                    if x["eps"] is not None:
                        x["eps"] = round(x["eps"] / f, 1)
                    if x["sh"]:
                        x["sh"] = round(x["sh"] * f, 2)
                rows[i]["split"] = (f"{n}合1" if inv else f"1拆{n}")
    # 財報沒有 EPS 的季：用最接近一季的股數推算（EPS = 歸屬母公司淨利 ÷ 股數）
    for i, x in enumerate(rows):
        if x["eps"] is None and x["ni"] is not None:
            near = sorted((abs(i - j), y["sh"]) for j, y in enumerate(rows) if y["sh"])
            if near:
                x["sh"] = near[0][1]
                x["eps"] = round(x["ni"] / (x["sh"] * 1e6), 1)
                x["eps_est"] = True
        elif not x["sh"]:
            near = sorted((abs(i - j), y["sh"]) for j, y in enumerate(rows) if y["sh"])
            x["sh"] = near[0][1] if near else None
    return rows


# ---------- Naver ----------
def naver_price(code):
    st = (TODAY - dt.timedelta(days=365 * YEARS + 40)).strftime("%Y%m%d") + "0000"
    en = TODAY.strftime("%Y%m%d") + "2359"
    j = http(f"https://api.stock.naver.com/chart/domestic/item/{code}/day?startDateTime={st}&endDateTime={en}")
    px = [dict(date=f"{x['localDate'][:4]}-{x['localDate'][4:6]}-{x['localDate'][6:]}", c=float(x["closePrice"]),
               fr=x.get("foreignRetentionRate")) for x in j if x.get("closePrice")]
    return sorted(px, key=lambda r: r["date"])


def yahoo_price(code):
    for sfx in (".KS", ".KQ"):
        try:
            j = http(f"https://query1.finance.yahoo.com/v8/finance/chart/{code}{sfx}?range={YEARS + 1}y&interval=1d")
            r = j["chart"]["result"][0]
            cl = r["indicators"]["quote"][0]["close"]
            px = [dict(date=dt.datetime.fromtimestamp(t, KST).date().isoformat(), c=c, fr=None)
                  for t, c in zip(r["timestamp"], cl) if c]
            if px:
                return px
        except Exception:
            pass
    return []


def kv(s):
    """'1,391조 4,143억' / '10.68배' / '22,292원' / '46.18%' → 數字（金額單位：億韓元）"""
    if s is None:
        return None
    s = str(s).replace(",", "")
    if "조" in s or "억" in s:
        jo = re.search(r"([\d.]+)조", s)
        eok = re.search(r"([\d.]+)억", s)
        return (float(jo[1]) * 1e4 if jo else 0) + (float(eok[1]) if eok else 0)
    m = re.search(r"-?[\d.]+", s)
    return float(m[0]) if m else None


def naver_info(code):
    j = http(f"https://m.stock.naver.com/api/stock/{code}/integration")
    t = {x.get("code"): x.get("value") for x in j.get("totalInfos", [])}
    return dict(per=kv(t.get("per")), eps=kv(t.get("eps")), pbr=kv(t.get("pbr")), bps=kv(t.get("bps")),
                cns_per=kv(t.get("cnsPer")), cns_eps=kv(t.get("cnsEps")), mcap=kv(t.get("marketValue")),
                fr=kv(t.get("foreignRate")), dy=kv(t.get("dividendYieldRatio")), name=j.get("stockName"))


def naver_cons(code):
    """Naver 年度財務（含法人共識預估年度）→ [[年度, 營收(億), 營益(億), EPS, 是否預估]]"""
    j = http(f"https://m.stock.naver.com/api/stock/{code}/finance/annual")
    if os.environ.get("KR_DEBUG"):
        (OUT / "debug").mkdir(exist_ok=True)
        (OUT / "debug" / f"{code}_annual.json").write_text(json.dumps(j, ensure_ascii=False)[:20000], "utf-8")
    fi = j.get("financeInfo") or {}
    titles = fi.get("trTitleList") or []
    rows = {r.get("title"): r.get("columns") or {} for r in fi.get("rowList") or []}
    out = []
    for t in titles:
        k = t.get("key")
        g = lambda name: kv((rows.get(name, {}).get(k) or {}).get("value"))
        out.append([str(t.get("title", ""))[:4], g("매출액"), g("영업이익"), g("EPS"), t.get("isConsensus") == "Y"])
    return out


# ---------- 組裝 ----------
FIN_COLS = ["cal", "rev", "gm", "om", "nm", "eps", "opa", "nia", "capex", "ocf", "divp", "eq", "assets", "liab", "cash"]
# fin 欄位：0季別 1營收(億) 2毛利率 3營益率 4淨利率 5EPS 6營業利益(億) 7母公司淨利(億) 8資本支出(億) 9營業現金流(億)
#           10股利發放(億) 11母公司權益(億) 12總資產(億) 13總負債(億) 14現金(億)　— 前端 #fin 財報明細頁用


def fin_rows(Q):
    return [[x.get(k) for k in FIN_COLS] for x in Q]


def build(code, corps):
    cfg = CFG.get(code, dict(theme="", zh="", flags="", tw=[]))
    corp, kname = corps.get(code, [None, ""])
    note, Q, n_new = [], [], (0, 0)
    if corp:
        cache, n_new = fin_cache(code, corp)
        Q = quarters(cache)
    else:
        note.append("OpenDART 查無此代號，沒有財報資料")
    try:
        px = naver_price(code)
        src = "Naver"
    except Exception as e:
        print(f"  Naver 股價失敗：{e}，改用 Yahoo")
        px, src = yahoo_price(code), "Yahoo"
    if not px:
        raise RuntimeError("抓不到股價")
    try:
        nv = naver_info(code)
    except Exception as e:
        print(f"  Naver 摘要失敗：{e}")
        nv = {}
    try:
        cons = naver_cons(code)
    except Exception as e:
        print(f"  Naver 共識失敗：{e}")
        cons = []

    def ttm_at(day):
        av = [q for q in Q if q["filed"] <= day and q["eps"] is not None]
        if len(av) < 4:
            return None
        last = av[-4:]
        if (dt.date.fromisoformat(last[-1]["end"]) - dt.date.fromisoformat(last[0]["end"])).days > 300:
            return None
        return sum(q["eps"] for q in last)

    def bvps_at(day):
        av = [q for q in Q if q["filed"] <= day and q["eq"] and q["sh"]]
        if not av:
            return None
        return av[-1]["eq"] * 1e8 / (av[-1]["sh"] * 1e6)

    mon = {}
    for r in px:
        mon[r["date"][:7]] = r
    riv = []
    for k in sorted(mon):
        r = mon[k]
        c, t, b = r["c"], ttm_at(r["date"]), bvps_at(r["date"])
        riv.append([k, c, None if t is None else round(t), None if b is None else round(b),
                    round(c / t, 1) if t and t > 0 else None, round(c / b, 2) if b and b > 0 else None,
                    r["fr"]])
    lr, pr = px[-1], px[-2] if len(px) > 1 else px[-1]
    t, b = ttm_at(lr["date"]), bvps_at(lr["date"])
    last = dict(date=lr["date"], close=lr["c"], prev=pr["c"], ttm=None if t is None else round(t),
                bvps=None if b is None else round(b), pe=round(lr["c"] / t, 1) if t and t > 0 else None,
                pb=round(lr["c"] / b, 2) if b and b > 0 else None, fr=lr["fr"] if lr["fr"] is not None else nv.get("fr"),
                cns_eps=nv.get("cns_eps"), cns_per=nv.get("cns_per"), nv_per=nv.get("per"), nv_pbr=nv.get("pbr"),
                mcap=nv.get("mcap"), dy=nv.get("dy"))
    cut = (TODAY - dt.timedelta(days=365 * 3)).isoformat()
    fr = [[r["date"], r["c"], r["fr"]] for r in px if r["date"] >= cut and r["fr"] is not None]
    q = [[x["cal"], x["cal"], x["rev"], x["gm"], x["om"], x["nm"], x["eps"], x["capex"], x["sh"], x["end"], x["filed"]]
         for x in Q]
    fin = fin_rows(Q)
    sp = [f"{x['cal']} {x['split']}" for x in Q if x.get("split")]
    if sp:
        note.append("股票分割：" + "、".join(sp) + "，之前各季 EPS 已依比例調整")
    if n_new[1]:
        note.append(f"財報回補中：還有 {n_new[1]} 份報告未抓，下次排程補齊")
    est = [x["cal"] for x in Q if x.get("eps_est")]
    if est:
        note.append(f"{est[0]}～{est[-1]} 共 {len(est)} 季財報未列 EPS，以淨利 ÷ 鄰近季股數推算")
    if Q and len(Q) < 4:
        note.append(f"財報只有 {len(Q)} 季，歷史資料不足")
    if Q and Q[-1].get("fs") == "OFS":
        note.append("此公司沒有連結財報，使用個別財報")
    if src != "Naver":
        note.append("股價來自 Yahoo（Naver 暫時抓不到），沒有外資持股比")
    return dict(id=code, name=cfg["zh"] or nv.get("name") or kname, kname=kname, theme=cfg["theme"],
                cyclical="C" in cfg["flags"], tw=cfg["tw"], freq="Q", fye=f"{TODAY.year - 1}-12-31", corp=corp,
                updated=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), last=last, q=q, riv=riv,
                fr=fr, cons=cons, fin=fin, note=note, _nv_name=nv.get("name")), n_new


def write_diag(diag):
    calls = [x[2] for x in STATS]
    (OUT / "diag.json").write_text(json.dumps(dict(
        at=dt.datetime.now(KST).strftime("%F %H:%M KST"), r=diag,
        dart=dict(n=len(calls), avg=round(sum(calls) / len(calls), 1) if calls else None, max=max(calls) if calls else None,
                  slow=[x for x in STATS if x[2] > 20 or x[3] not in ("ok", "none")][:40])),
        ensure_ascii=False, indent=1), "utf-8")


def main():
    if not KEY:
        sys.exit("缺少環境變數 DART_KEY")
    ids = sys.argv[1:] or STOCKS
    OUT.mkdir(parents=True, exist_ok=True)
    corps = corp_map(ids)
    ok, bad, diag = [], [], {}
    for code in ids:
        try:
            t0 = time.time()
            d, n_new = build(code, corps)
            nvn = d.pop("_nv_name", None)
            (OUT / f"{code}.json").write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), "utf-8")
            L, lq = d["last"], d["q"][-1] if d["q"] else None
            ok.append(dict(id=code, name=d["name"], kname=d["kname"], theme=d["theme"], n=len(d["q"]),
                           close=L["close"], chg=round((L["close"] / L["prev"] - 1) * 100, 2) if L["prev"] else None,
                           pe=L["pe"], pb=L["pb"], fr=L["fr"], cpe=L["cns_per"], lq=lq[0] if lq else None,
                           cyc=d["cyclical"], tw=d["tw"], date=L["date"]))
            Qs = d["q"]
            diag[code] = dict(zh=d["name"], kname=d["kname"], nv=nvn, n=len(Qs), sec=round(time.time() - t0),
                              first=Qs[0][0] if Qs else None, last=lq[0] if lq else None, new=n_new,
                              miss={k: sum(1 for x in Qs if x[i] is None) for k, i in (("gm", 3), ("om", 4), ("eps", 6), ("capex", 7))},
                              pe=L["pe"], nv_per=L["nv_per"], pb=L["pb"], nv_pbr=L["nv_pbr"], cns=L["cns_per"], fr=L["fr"],
                              note=d["note"], tail=Qs[-2:])
            write_diag(diag)
            print(f"{code} ok {d['name']} ({d['kname']}) close={L['close']} pe={L['pe']}(Naver {L['nv_per']}) "
                  f"pb={L['pb']}(Naver {L['nv_pbr']}) ttm={L['ttm']}(Naver {L.get('cns_eps')} 共識) fr={L['fr']} "
                  f"q={len(d['q'])} 新抓報告={n_new} {time.time() - t0:.0f}s")
            for x in d["q"][-6:]:
                print("   ", x)
            print("    cons", d["cons"])
        except Exception as e:
            bad.append(code)
            diag[code] = dict(err=str(e)[:300])
            write_diag(diag)
            print(f"{code} FAILED: {e}", file=sys.stderr)
    idx = OUT / "index.json"
    old = json.loads(idx.read_text("utf-8")) if idx.exists() else []
    m = {s["id"]: s for s in old if s["id"] in CFG}
    m.update({s["id"]: s for s in ok if s["id"] in CFG})
    idx.write_text(json.dumps([m[c] for c in STOCKS if c in m], ensure_ascii=False), "utf-8")
    write_diag(diag)
    print(f"完成 {len(ok)}／{len(ids)}，失敗：{bad}")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
