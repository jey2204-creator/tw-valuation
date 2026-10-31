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
    neg = (s.startswith("(") and s.endswith(")")) or s.startswith("△") or s.startswith("▲")
    s = s.strip("()△▲")
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


# ---------- 📅 財報公布：暫定業績（잠정실적）＋公布日預估 ----------
# 韓國大型股在季末後 1～4 週先發「營業（暫定）實績」公正公示（只有營收、營業利益、淨利），正式季報（OpenDART）要到季末後 45 天
# （年報 90 天）才出。這裡：1) Naver 季度表抓暫定數字（FnGuide 在暫定公布當天更新）；2) OpenDART 公示搜尋抓暫定公告日，
# 去年同季的公告日 + 1 年 = 今年預計公布日；3) 法定期限 = 底線。快取 kr/data/earn/{代號}.json
QMAP = {1: 4, 2: 4, 3: 4, 4: 1, 5: 1, 6: 1, 7: 2, 8: 2, 9: 2, 10: 3, 11: 3, 12: 3}   # 公告月份 → 屬於哪一季的業績


def q_of_date(d):
    """暫定業績公告日 → 季別 'YYQn'（1～3 月公告的是去年 Q4）"""
    qn = QMAP[d.month]
    y = d.year - 1 if qn == 4 else d.year
    return f"{str(y)[2:]}Q{qn}"


def q_end(cal):
    y, qn = 2000 + int(cal[:2]), int(cal[3])
    return dt.date.fromisoformat(f"{y}-{dict((q, md) for _, q, md, _ in REPORTS)[qn]}")


def next_cal(cal):
    y, qn = int(cal[:2]), int(cal[3]) + 1
    if qn > 4:
        y, qn = y + 1, 1
    return f"{y:02d}Q{qn}"


def weekday(d):
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d


def naver_quarter(code):
    """Naver 季度財務表 → {'26Q3': dict(rev=億, op=億, ni=億, nip=億(母公司), eps=韓元)}，只收非共識（已公布）的季度"""
    j = http(f"https://m.stock.naver.com/api/stock/{code}/finance/quarter")
    fi = j.get("financeInfo") or {}
    rows = {re.sub(r"\s", "", str(r.get("title") or "")): r.get("columns") or {} for r in fi.get("rowList") or []}

    def pick(k, *names):
        for n in names:   # 先找完全相同的列名，再找開頭相同的（「당기순이익」別抓到「당기순이익(지배)」）
            for t, cols in sorted(rows.items(), key=lambda kv_: 0 if kv_[0] == n else 1):
                if t.startswith(n) and "(E)" not in t:
                    v = kv((cols.get(k) or {}).get("value"))
                    if v is not None:
                        return v
        return None
    out = {}
    for t in fi.get("trTitleList") or []:
        title, k = str(t.get("title", "")), t.get("key")
        m = re.search(r"(\d{4})\D?(\d{1,2})", title)
        if not m or t.get("isConsensus") == "Y" or "(E)" in title or "E" == title.strip()[-1:]:
            continue
        y, mo = int(m[1]), int(m[2])
        if mo not in (3, 6, 9, 12):
            continue
        cal = f"{str(y)[2:]}Q{mo // 3}"
        rev, op = pick(k, "매출액"), pick(k, "영업이익")
        if rev is None and op is None:
            continue
        out[cal] = dict(rev=rev, op=op, ni=pick(k, "당기순이익"), nip=pick(k, "당기순이익(지배", "지배주주순이익", "지배기업"),
                        eps=pick(k, "EPS", "주당순이익"))
    return out


def dart_prelim(corp, cache):
    """OpenDART 公示搜尋：營業（暫定）實績公正公示 → cache['ann'] = [[公告日, rcept_no, 公告名]]，只補 upto 之後的新公告"""
    ann = {a[1]: a for a in cache.get("ann", [])}
    upto = cache.get("upto")
    bgn = (dt.date.fromisoformat(upto) - dt.timedelta(days=3)) if upto else TODAY - dt.timedelta(days=430)
    for page in range(1, 4):
        q = urllib.parse.urlencode(dict(crtfc_key=KEY, corp_code=corp, bgn_de=bgn.strftime("%Y%m%d"), end_de=TODAY.strftime("%Y%m%d"),
                                        pblntf_ty="I", page_no=page, page_count=100))
        j = http(f"https://opendart.fss.or.kr/api/list.json?{q}", tries=2, timeout=30)
        st = j.get("status")
        if st == "013":
            break
        if st != "000":
            raise RuntimeError(f"OpenDART list {st} {j.get('message')}")
        for x in j.get("list", []):
            nm = re.sub(r"\s", "", x.get("report_nm") or "")
            if "잠정" in nm and "실적" in nm and "정정" not in nm[:4]:
                d = x.get("rcept_dt") or ""
                ann[x.get("rcept_no")] = [f"{d[:4]}-{d[4:6]}-{d[6:8]}", x.get("rcept_no"), x.get("report_nm")]
        if page >= int(j.get("total_page") or 1):
            break
        time.sleep(0.3)
    cache["ann"] = sorted(ann.values())
    cache["upto"] = TODAY.isoformat()
    return cache


DOC_V = 2   # 解析規則改版就 +1：舊版快取會重新抓公告原文
DOC_ROWS = {"rev": ["매출액", "매출", "영업수익", "수익(매출액)"], "op": ["영업이익", "영업이익(손실)"],
            "ni": ["당기순이익", "당기순이익(손실)", "분기순이익", "반기순이익"],
            "nip": ["지배기업소유주지분순이익", "지배기업의소유주에게귀속되는당기순이익", "지배주주지분순이익", "지배기업소유주지분당기순이익", "지배기업지분순이익"]}


def dart_doc_prelim(rno):
    """OpenDART 公告原文（document.xml → zip 內 XML）→ 暫定業績表的「당해실적（本季）」欄：{rev, op, ni, nip}（億韓元）
    表格每個科目兩列：당해실적（單季）／누계실적（累計），取 당해실적 列第一個數字；單位看表頭「(단위 : 백만원)」"""
    b = http(f"https://opendart.fss.or.kr/api/document.xml?crtfc_key={KEY}&rcept_no={rno}", raw=True, tries=2, timeout=60)
    if not b.startswith(b"PK"):
        raise RuntimeError("document.xml 不是 zip：" + b[:80].decode("utf-8", "replace"))
    z = zipfile.ZipFile(io.BytesIO(b))
    raw = b"".join(z.read(n) for n in z.namelist() if n.lower().endswith((".xml", ".html", ".htm")))
    txt = None
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            txt = raw.decode(enc)
            break
        except UnicodeDecodeError:
            pass
    txt = txt or raw.decode("utf-8", "replace")
    txt = re.sub(r"<!--.*?-->", "", txt, flags=re.S)
    m = re.search(r"단위\s*[:：]?\s*(조원|십억원|백만원|억원|천원|원)", re.sub(r"<[^>]+>", " ", txt))
    k = {"조원": 1e4, "십억원": 10.0, "백만원": 1e-2, "억원": 1.0, "천원": 1e-5, "원": 1e-8}[m[1]] if m else 1e-2   # 沒寫單位當百萬韓元（KIND 表單預設）；三星用兆韓元
    out, rows = {}, []
    for tr in re.findall(r"<TR\b.*?</TR>", txt, flags=re.S | re.I):
        cells = [re.sub(r"\s", "", re.sub(r"<[^>]+>", "", c)) for c in re.findall(r"<T[DH]\b.*?</T[DH]>", tr, flags=re.S | re.I)]
        cells = [c for c in cells if c]
        if cells and len(rows) < 40:
            rows.append([c[:24] for c in cells[:8]])   # 留表格內容供核對（kr/data/earn/*.json doc.rows）
        if not cells or any("누계" in c for c in cells[:3]):
            continue
        for key, names in DOC_ROWS.items():
            if key in out:
                continue
            idx = next((i for i, c in enumerate(cells[:3]) if c.replace("(손실)", "") in [n.replace("(손실)", "") for n in names]), None)
            if idx is None:
                continue
            start = next((i + 1 for i, c in enumerate(cells) if "당해" in c), idx + 1)
            v = next((num(c) for c in cells[start:] if num(c) is not None), None)
            if v is not None:
                out[key] = round(v * k, 1)
    out["unit"], out["rows"], out["v"] = (m[1] if m else None), rows, DOC_V
    return out


def earn_info(code, corp, Q, fin):
    """→ (earn 摘要, 暫定季列 or None)。earn = {q 待公布季, st pre|wait|late, pre 暫定公布日, est 預計日, due 法定底線, b 預估依據, ...}"""
    p = OUT / "earn" / f"{code}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    cache = json.loads(p.read_text("utf-8")) if p.exists() else {}
    err = []
    if corp:
        try:
            cache = dart_prelim(corp, cache)
        except Exception as e:
            err.append(f"DART 公示：{str(e)[:60]}")
    try:
        cache["nv"] = naver_quarter(code)
        cache["nv_at"] = TODAY.isoformat()
    except Exception as e:
        err.append(f"Naver 季表：{str(e)[:60]}")
    p.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), "utf-8")
    # 暫定公告日：每季取最早的一次（三星 10/8 暫定、10/30 正式都掛「잠정」）
    pre_dt, last_rno = {}, {}
    for d, rno, nm in cache.get("ann", []):
        cal = q_of_date(dt.date.fromisoformat(d))
        if cal not in pre_dt or d < pre_dt[cal][0]:
            pre_dt[cal] = [d, rno]
        if cal not in last_rno or rno > last_rno[cal]:
            last_rno[cal] = rno   # 三星 10/8 暫定只有營收／營益，10/29 正式（含 기재정정）才有淨利 → 數字取最新一份
    if not Q:
        return dict(err=err) if err else {}, None
    last = Q[-1]["cal"]
    pend = next_cal(last)
    end = q_end(pend)   # 待公布季還沒結束（剛申報完）時，一樣顯示它的預計日
    y, qn = 2000 + int(pend[:2]), int(pend[3])
    rc, due_days = next((r, du) for r, q, md, du in REPORTS if q == qn)
    due = weekday(end + dt.timedelta(days=due_days))   # 期限遇假日順延到下個工作日
    e = dict(q=pend, end=end.isoformat(), due=due.isoformat())
    # 預計公布日：去年同季暫定公告日 → 去年同季季報申報日 → 法定底線
    ly = f"{int(pend[:2]) - 1:02d}Q{qn}"
    if ly in pre_dt:
        d0 = dt.date.fromisoformat(pre_dt[ly][0])
        e["est"], e["b"] = weekday(d0.replace(year=d0.year + 1)).isoformat(), f"去年暫定 {d0.month}/{d0.day}"
    else:
        r = fin.get(f"{y - 1}-{rc}") or {}
        f = r.get("rcept") or ""
        if len(f) == 8:
            d0 = dt.date(int(f[:4]), int(f[4:6]), int(f[6:]))
            e["est"], e["b"] = weekday(d0.replace(year=d0.year + 1)).isoformat(), f"去年季報 {d0.month}/{d0.day}"
        else:
            e["est"], e["b"] = due.isoformat(), "法定期限"
    if e["est"] > e["due"]:
        e["est"] = e["due"]
    # 這一季的暫定：DART 有公告（數字從公告原文解析，快取在 doc）or Naver 季表已有數字
    nv = (cache.get("nv") or {}).get(pend)
    row = None
    if pend in pre_dt:
        rno = last_rno[pend]
        doc = (cache.get("doc") or {}).get(rno)
        if doc is None or doc.get("v") != DOC_V or not doc.get("rev") and not doc.get("op"):   # 沒抓過、規則改版、或上次沒解析到 → 再試
            try:
                doc = dart_doc_prelim(rno)
            except Exception as ex:
                err.append(f"公告原文：{str(ex)[:60]}")
                doc = {}
            cache.setdefault("doc", {})[rno] = doc
            p.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), "utf-8")
        if doc and (doc.get("rev") is not None or doc.get("op") is not None):
            nv = dict(rev=doc.get("rev"), op=doc.get("op"), ni=doc.get("ni"), nip=doc.get("nip"), eps=None)
            e["src"] = "dart"
    if pend in pre_dt or nv:
        e["st"] = "pre"
        if pend in pre_dt:
            e["pre"], e["rno"] = pre_dt[pend]
            e["rno2"] = last_rno[pend]
        else:
            e["pre"], e["src"] = cache.get("nv_at") or TODAY.isoformat(), "naver"
        if nv:
            ni = nv.get("nip") if nv.get("nip") is not None else nv.get("ni")
            sh = next((q["sh"] for q in reversed(Q) if q.get("sh")), None)
            eps = nv.get("eps")
            if eps is None and ni is not None and sh:
                eps = round(ni * 1e8 / (sh * 1e6), 1)
            pct = lambda v: None if v is None or not nv.get("rev") else round(v / nv["rev"] * 100, 1)
            row = dict(cal=pend, end=end.isoformat(), filed=e["pre"], rev=nv.get("rev"), gm=None, om=pct(nv.get("op")), nm=pct(ni),
                       eps=eps, capex=None, sh=sh, eq=None, fs=None, ni=None if ni is None else ni * 1e8,
                       opa=nv.get("op"), nia=ni, ocf=None, divp=None, assets=None, liab=None, cash=None, pre=True,
                       eps_est=nv.get("eps") is None)
            e.update(rev=nv.get("rev"), op=nv.get("op"), ni=ni, eps=eps)
            # 年增（對去年同季正式財報）
            py = next((q for q in Q if q["cal"] == ly), None)
            if py and py.get("rev") and nv.get("rev"):
                e["ry"] = round((nv["rev"] / py["rev"] - 1) * 100, 1)
            if py and py.get("opa") and nv.get("op") is not None and py["opa"] > 0:
                e["oy"] = round((nv["op"] / py["opa"] - 1) * 100, 1)
        else:
            e["nonum"] = True   # DART 有暫定公告但原文解析不到數字、Naver 也沒有
    else:
        e["st"] = "late" if TODAY > due else "wait"
    if err:
        e["err"] = err
    return e, row


# ---------- 組裝 ----------
FIN_COLS = ["cal", "rev", "gm", "om", "nm", "eps", "opa", "nia", "capex", "ocf", "divp", "eq", "assets", "liab", "cash"]
# fin 欄位：0季別 1營收(億) 2毛利率 3營益率 4淨利率 5EPS 6營業利益(億) 7母公司淨利(億) 8資本支出(億) 9營業現金流(億)
#           10股利發放(億) 11母公司權益(億) 12總資產(億) 13總負債(億) 14現金(億)　— 前端 #fin 財報明細頁用


def fin_rows(Q):
    return [[x.get(k) for k in FIN_COLS] + ([1] if x.get("pre") else []) for x in Q]   # 第 16 欄 1 = 暫定業績（Naver 季表，待正式季報取代）


def build(code, corps):
    cfg = CFG.get(code, dict(theme="", zh="", flags="", tw=[]))
    corp, kname = corps.get(code, [None, ""])
    note, Q, n_new, cache = [], [], (0, 0), {}
    if corp:
        cache, n_new = fin_cache(code, corp)
        Q = quarters(cache)
    else:
        note.append("OpenDART 查無此代號，沒有財報資料")
    # 📅 暫定業績：正式季報還沒出、Naver 季表已有數字 → 接在最後一季後面（本益比、年增、財報明細都會用到；正式季報抓到後自動取代）
    try:
        earn, prow = earn_info(code, corp, Q, cache)
    except Exception as e:
        print(f"  暫定業績失敗：{e}")
        earn, prow = {}, None
    if prow and prow.get("rev"):
        Q.append(prow)
        note.append(f"{prow['cal']} 為暫定業績（{'OpenDART 公告原文' if earn.get('src') == 'dart' else 'Naver 季表'}，{earn.get('pre', '')[5:].replace('-', '/')} 公布）：只有營收、營業利益、淨利"
                    f"{'，EPS 以淨利 ÷ 前季股數推算' if prow.get('eps_est') else ''}；正式季報申報後自動取代")
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
    q = [[x["cal"], x["cal"], x["rev"], x["gm"], x["om"], x["nm"], x["eps"], x["capex"], x["sh"], x["end"], x["filed"]] + ([1] if x.get("pre") else [])
         for x in Q]   # 第 12 欄 1 = 暫定業績
    fin = fin_rows(Q)
    sp = [f"{x['cal']} {x['split']}" for x in Q if x.get("split")]
    if sp:
        note.append("股票分割：" + "、".join(sp) + "，之前各季 EPS 已依比例調整")
    if n_new[1]:
        note.append(f"財報回補中：還有 {n_new[1]} 份報告未抓，下次排程補齊")
    est = [x["cal"] for x in Q if x.get("eps_est") and not x.get("pre")]
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
                fr=fr, cons=cons, fin=fin, earn=earn, note=note, _nv_name=nv.get("name")), n_new


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
                           cyc=d["cyclical"], tw=d["tw"], date=L["date"], pre=bool(lq and len(lq) > 11 and lq[11]),
                           earn={k: v for k, v in (d.get("earn") or {}).items() if k in ("q", "st", "pre", "est", "due", "b", "ry", "oy", "nonum")}))
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
