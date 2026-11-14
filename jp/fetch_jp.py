"""日股估值看板：Yahoo 股價 ＋ J-Quants 免費版（歷史財報）＋ TDnet 決算短信 XBRL（最新財報、会社予想）
→ 加密寫到 jp/data/{代號}.bin、jp/data/index.bin、jp/data/k/{代號}.bin（日 K 歷史）；歷史存檔加密在 jp/raw/*.bin。

公開（不加密）的只有：jp/data/meta.json（金鑰衍生用的 salt、驗證碼）、jp/data/diag.json（筆數、日期、檢查結果，不含數值）。
⚠️ J-Quants 條款：資料只能本人看 → 沒有 JP_DATA_KEY 就整個停止，絕不寫出明文。

環境變數：JQUANTS_API_KEY（J-Quants 金鑰）、JP_DATA_KEY（加密密語）、JP_VALIDATE=1（加跑股價交叉比對，較慢）
用法：python jp/fetch_jp.py [代號 ...]
"""
import base64, hashlib, io, json, os, re, sys, time, unicodedata, zipfile, datetime as dt
from pathlib import Path
import urllib.request, urllib.parse, urllib.error

# ---------- 追蹤清單：(主題, [(代號, 中文名, 旗標)], 對應台股) ；旗標 C = 循環股 ----------
THEMES = [
    ("🧱 半導體設備", [("8035", "東京威力科創", ""), ("6857", "愛德萬測試", ""), ("6146", "迪思科", ""),
                   ("6920", "雷泰光電", ""), ("7735", "斯庫林", ""), ("6525", "國際電氣", ""), ("7729", "東京精密", "")],
     [("3131", "弘塑"), ("3583", "辛耘"), ("6187", "萬潤"), ("6223", "旺矽"), ("6515", "穎崴"), ("2360", "致茂")]),
    ("💿 矽晶圓／半導體材料", [("4063", "信越化學", "C"), ("3436", "勝高 SUMCO", "C"), ("4004", "力森諾科", ""),
                        ("4186", "東京應化", ""), ("2802", "味之素（ABF）", "")],
     [("6488", "環球晶"), ("5483", "中美晶"), ("6182", "合晶")]),
    ("🟩 載板／PCB 材料", [("4062", "揖斐電", ""), ("3110", "日東紡", "")],
     [("3037", "欣興"), ("4958", "臻鼎-KY"), ("2383", "台光電"), ("2368", "金像電")]),
    ("⚡ 被動元件", [("6981", "村田製作所", ""), ("6762", "TDK", ""), ("6976", "太陽誘電", ""), ("6971", "京瓷", "")],
     [("2327", "國巨"), ("2492", "華新科"), ("3026", "禾伸堂")]),
    ("💡 光通訊／電線", [("5803", "藤倉", ""), ("5801", "古河電工", ""), ("5802", "住友電工", "")],
     [("3081", "聯亞"), ("3363", "上詮"), ("3163", "波若威"), ("3450", "聯鈞"), ("4979", "華星光")]),
    ("🎯 記憶體／IC 設計", [("285A", "鎧俠", "C"), ("6526", "索思未來", ""), ("6723", "瑞薩電子", "")],
     [("2344", "華邦電"), ("2408", "南亞科"), ("8299", "群聯"), ("3661", "世芯-KY"), ("3443", "創意")]),
    ("🔌 電力／重電", [("6501", "日立", ""), ("6503", "三菱電機", ""), ("6504", "富士電機", "")],
     [("1519", "華城"), ("1503", "士電"), ("1513", "中興電"), ("1514", "亞力")]),
    # 一檔股票可以出現在多個主題（第 4 欄＝在這個主題的角色；旗標 O＝選配／題材股）
    ("🖥️ AI 伺服器供應鏈", [
        ("5803", "藤倉", "", "資料中心高密度光纖、MPO"), ("5801", "古河電工", "", "資料中心光纖、散熱模組"),
        ("4062", "揖斐電", "", "AI 晶片 ABF 載板"), ("3110", "日東紡", "", "低介電玻纖布（載板、高階 CCL）"),
        ("5706", "三井金屬", "", "HVLP 高頻銅箔"), ("6981", "村田製作所", "", "MLCC、電源模組"),
        ("6516", "山洋電氣", "", "伺服器風扇、UPS"), ("285A", "鎧俠", "C", "企業級 SSD（NAND）"),
        ("6594", "尼得科", "O", "液冷 CDU、風扇（馬達、車用為主）"), ("6762", "TDK", "O", "伺服器電源、電感（電池為主）"),
        ("6963", "羅姆", "O", "SiC／GaN 功率元件（車用、工業為主）"),
        ("6997", "日本貴彌功", "O", "伺服器電源電容（車用占比高）"),
        ("5802", "住友電工", "O", "資料中心光纖（車用線束為主）")],
     [("2382", "廣達"), ("3231", "緯創"), ("6669", "緯穎"), ("3017", "奇鋐"), ("3324", "雙鴻"), ("2308", "台達電"),
      ("2383", "台光電"), ("8358", "金居")]),
]
CFG = {}
for th, items, tw in THEMES:
    for it in items:
        c, zh, f = it[:3]
        CFG.setdefault(c, dict(theme=th, zh=zh, flags=f.replace("O", ""), tw=tw))   # 第一次出現的主題＝主要主題
STOCKS = list(CFG)
# 口徑變更（事業分拆、改列停業單位等）：新財報的累計營收／營業利益改成新口徑，但上一期累計還是舊口徑，
# 「本期累計 − 上期累計」算出來的單季會失真，之後四季的營收年增也是新舊口徑互比。
# 填法：代號 → (會計年度底 YYYY-MM, 第幾季起改口徑, 說明)。只做標記（q 第 15 欄）與提示，不改動原本的數字：
#   1＝變更當季（單季營收、利益率不可用）　2＝之後四季（單季數字可用，但營收年增不可比）
# 第 1 季就改口徑時單季沒問題（累計＝單季），那一季起四季都標 2。新的分拆案要手動加一行。
BASIS_BREAK = {
    "4004": ("2026-12", 3, "2026/7～9 月起石化事業（Crasus Chemical，2026/10/1 部分分拆）改列停業單位"),
}
# 給網頁用的主題清單：[{t: 主題, tw: 對應台股, m: [[代號, 角色, 選配]]}]
THEME_META = [dict(t=th, tw=tw, m=[[it[0], it[3] if len(it) > 3 else "", "O" in it[2]] for it in items])
              for th, items, tw in THEMES]

ROOT = Path(__file__).resolve().parent
OUT, RAW = ROOT / "data", ROOT / "raw"
JQ = "https://api.jquants.com/v2"
JQ_KEY = os.environ.get("JQUANTS_API_KEY", "").strip()
# NFKC：全形英數（中文輸入法打出來的）與半形視為相同，手機輸入比較不會對不上
PASS = unicodedata.normalize("NFKC", os.environ.get("JP_DATA_KEY", "")).strip()
VALIDATE = os.environ.get("JP_VALIDATE", "") == "1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
NOW_JST = dt.datetime.utcnow() + dt.timedelta(hours=9)
TODAY = NOW_JST.date()
ITER = 310000
YEARS = 10
DIAG = {"asof": NOW_JST.strftime("%Y-%m-%d %H:%M JST"), "errors": [], "stocks": {}}


def err(msg):
    print("⚠️", msg, file=sys.stderr)
    DIAG["errors"].append(str(msg)[:300])


D = lambda s: dt.date.fromisoformat(s[:10])


def num(v):
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ======================= 加密 =======================
def load_meta():
    p = OUT / "meta.json"
    m = json.loads(p.read_text("utf-8")) if p.exists() else {}
    if not m.get("salt"):
        m = {"v": 1, "kdf": "PBKDF2-SHA256", "iter": ITER, "salt": base64.b64encode(os.urandom(16)).decode()}
    return m


def make_key(meta):
    raw = hashlib.pbkdf2_hmac("sha256", PASS.encode("utf-8"), base64.b64decode(meta["salt"]), meta["iter"], 32)
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return AESGCM(raw)


def enc(aes, obj):
    iv = os.urandom(12)
    return iv + aes.encrypt(iv, json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), None)


def dec(aes, b):
    return json.loads(aes.decrypt(b[:12], b[12:], None).decode("utf-8"))


# ======================= HTTP =======================
def http(url, headers=None, timeout=60, tries=3, raw=False):
    h = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.8"}
    h.update(headers or {})
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
                b = r.read()
                return b if raw else json.loads(b)
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (400, 401, 403, 404):
                break
        except Exception as e:  # noqa
            last = f"{type(e).__name__}: {e}"
        time.sleep(3 * (i + 1))
    raise RuntimeError(f"{url[:90]} → {last}")


_plan_t = [0.0]


def jq(path, params, plan=True):
    """J-Quants 免費版：一般端點 5 次／分 → 間隔 13 秒；fins/* 另有 60 次／分 → 間隔 1.1 秒。
    遇 429 等 75 秒重試一次（官方：不給 Retry-After、至少等 1 分鐘）。自動走 pagination_key。"""
    if not JQ_KEY:
        raise RuntimeError("沒有 JQUANTS_API_KEY")
    out, pkey = [], None
    while True:
        gap = 13 if plan else 1.1
        wait = gap - (time.time() - _plan_t[0]) if plan else gap
        if wait > 0:
            time.sleep(wait)
        q = dict(params, **({"pagination_key": pkey} if pkey else {}))
        url = f"{JQ}{path}?{urllib.parse.urlencode(q)}"
        for attempt in range(2):
            try:
                j = http(url, {"x-api-key": JQ_KEY, "Accept": "application/json"}, tries=1)
                break
            except RuntimeError as e:
                if "HTTP 429" in str(e) and attempt == 0:
                    time.sleep(75)
                    continue
                raise
            finally:
                if plan:
                    _plan_t[0] = time.time()
        out += j.get("data", [])
        pkey = j.get("pagination_key")
        if not pkey:
            return out


# ======================= Yahoo 股價 =======================
YNAME = {}
YK = {}            # 代號 → 日 K [[日期, 開, 高, 低, 收, 量], ...]（個股頁「K線」用）
K_MONTHS = 37      # 日 K 保留本月＋往前 37 個月（約 3 年；2 年區間的 MA200 要往前多 200 根才算得出）


def yahoo(code):
    j = http(f"https://query1.finance.yahoo.com/v8/finance/chart/{code}.T"
             f"?range={YEARS}y&interval=1d&events=div%2Csplit&includeAdjustedClose=true")
    r = (j.get("chart", {}).get("result") or [None])[0]
    YNAME[code] = ((r or {}).get("meta") or {}).get("longName") or ((r or {}).get("meta") or {}).get("shortName")
    if not r or not r.get("timestamp"):
        raise RuntimeError(f"Yahoo 沒有 {code}.T 股價")
    day = lambda t: (dt.datetime.utcfromtimestamp(t) + dt.timedelta(hours=9)).strftime("%Y-%m-%d")
    q = r["indicators"]["quote"][0]
    px = {}
    for t, c, v in zip(r["timestamp"], q.get("close") or [], q.get("volume") or []):
        if c:
            px[day(t)] = c          # Yahoo close：已做分割調整、未做除息調整
    YK[code] = ohlc_rows(r["timestamp"], q, day)
    splits = sorted((day(int(k)), (s.get("numerator") or 1) / (s.get("denominator") or 1))
                    for k, s in (r.get("events", {}).get("splits") or {}).items())
    return sorted(px.items()), [(d, f) for d, f in splits if f and abs(f - 1) > 1e-9]


def ohlc_rows(ts, q, day):
    """Yahoo chart 的開高低收量（都已做分割調整、未做除息調整，和 close 同一基準）→ [[日期, 開, 高, 低, 收, 量], ...]
    開高低任一缺就只留收盤（o=h=l=c），避免畫出假影線；同一天重複（盤中＋收盤各一筆）取後面那筆。"""
    n = len(ts)
    col = lambda k: (q.get(k) or []) + [None] * n
    rd = lambda x: round(x, 1) if x >= 100 else round(x, 2)
    by = {}
    for t, o, h, l, c, v in zip(ts, col("open"), col("high"), col("low"), col("close"), col("volume")):
        if not c:
            continue
        if o and h and l:
            h, l = max(h, o, c), min(l, o, c)   # 防資料源偶發高低顛倒
        else:
            o = h = l = c
        by[day(t)] = [day(t), rd(o), rd(h), rd(l), rd(c), int(v) if v else None]
    return [by[d] for d in sorted(by)]


def k_split(rows):
    """日 K 拆成（歷史, 本月）。加密檔每次重寫整份都會變（git 無法做差異壓縮），所以：
    歷史＝上個月底以前，放 data/k/{代號}.bin，內容有變（換月、分割調整）才重寫；本月的幾根放進每天都會重寫的 {代號}.bin 的 k。
    起點固定在月初（不是「最近 N 根」），歷史檔才不會每天掉一根而天天重寫。"""
    m = TODAY.year * 12 + TODAY.month - 1 - K_MONTHS
    lo, cut = f"{m // 12}-{m % 12 + 1:02d}-01", TODAY.strftime("%Y-%m") + "-01"
    return [r for r in rows if lo <= r[0] < cut], [r for r in rows if r[0] >= cut]


def split_factor(disc, splits):
    """公布日之後才生效的分割 → 當時的每股數字要除以這個倍數，才能和分割調整後的股價比"""
    f = 1.0
    for d, n in splits:
        if disc < d:
            f *= n
    return f


# ======================= J-Quants 財報 =======================
JQ_A = dict(sales="Sales", op="OP", odp="OdP", np="NP", eps="EPS", deps="DEPS", ta="TA", eq="Eq", sheq="ShEq",
            bps="BPS", sh_out="ShOutFY", tr_sh="TrShFY", avg_sh="AvgSh")
JQ_F = dict(sales="FSales", op="FOP", odp="FOdP", np="FNP", eps="FEPS")
JQ_FH = dict(sales="FSales2Q", op="FOP2Q", odp="FOdP2Q", np="FNP2Q", eps="FEPS2Q")
JQ_NF = dict(sales="NxFSales", op="NxFOP", odp="NxFOdP", np="NxFNp", eps="NxFEPS")
JQ_NFH = dict(sales="NxFSales2Q", op="NxFOP2Q", odp="NxFOdP2Q", np="NxFNp2Q", eps="NxFEPS2Q")
MONEY = {"sales", "op", "odp", "np", "ta", "eq", "sheq"}


def pick(rec, m):
    out = {}
    for k, f in m.items():
        v = num(rec.get(f))
        if v is not None:
            out[k] = v / 1e6 if k in MONEY else v      # 金額一律換成百萬日圓
    return out


def norm_jq(r):
    doc = r.get("DocType", "")
    per = r.get("CurPerType", "")
    if "FinancialStatements" in doc:
        typ = {"1Q": "1Q", "2Q": "2Q", "3Q": "3Q", "FY": "FY"}.get(per, "X")
    elif "EarnForecastRevision" in doc:
        typ = "REV"
    else:
        typ = "O"
    std = "IFRS" if "IFRS" in doc else "US" if "_US" in doc else "JP"
    return dict(src="J", id=r.get("DiscNo"), disc=r.get("DiscDate", ""), time=(r.get("DiscTime") or "")[:5], type=typ,
                doc=doc, std=std, cons="NonConsolidated" not in doc,
                fy_st=r.get("CurFYSt", ""), fy_end=r.get("CurFYEn", ""), per_st=r.get("CurPerSt", ""),
                per_end=r.get("CurPerEn", ""), a=pick(r, JQ_A), f=pick(r, JQ_F), fh=pick(r, JQ_FH),
                nf=pick(r, JQ_NF), nfh=pick(r, JQ_NFH))


# ======================= TDnet 決算短信 XBRL =======================
TD = "https://www.release.tdnet.info/inbs/"
NAMES = dict(  # 依序找第一個有值的科目（日本基準、IFRS、美國基準）
    sales=["NetSales", "OperatingRevenues", "OrdinaryRevenues", "GrossOperatingRevenues", "SalesIFRS",
           "RevenueIFRS", "OperatingRevenuesIFRS", "NetSalesIFRS", "NetSalesUS", "OperatingRevenuesUS",
           "RevenuesUS", "TotalRevenuesUS"],
    op=["OperatingIncome", "OperatingIncomeIFRS", "OperatingProfitIFRS", "OperatingIncomeUS"],
    odp=["OrdinaryIncome"],
    np=["ProfitAttributableToOwnersOfParent", "NetIncome", "ProfitAttributableToOwnersOfParentIFRS",
        "NetIncomeAttributableToOwnersOfParentUS", "NetIncomeAttributableToShareholdersUS"],
    eps=["NetIncomePerShare", "BasicEarningsPerShareIFRS", "NetIncomePerShareUS", "BasicNetIncomePerShareUS"],
    deps=["DilutedNetIncomePerShare", "DilutedEarningsPerShareIFRS", "DilutedNetIncomePerShareUS"],
    ta=["TotalAssets", "TotalAssetsIFRS", "TotalAssetsUS"],
    eq=["NetAssets", "TotalEquityIFRS", "EquityUS", "TotalEquityUS"],
    sheq=["OwnersEquity", "EquityAttributableToOwnersOfParentIFRS", "ShareholdersEquityUS"],
    bps=["NetAssetsPerShare", "EquityAttributableToOwnersOfParentPerShareIFRS"],
    sh_out=["NumberOfIssuedAndOutstandingSharesAtTheEndOfFiscalYearIncludingTreasuryStock"],
    tr_sh=["NumberOfTreasuryStockAtTheEndOfFiscalYear"],
    avg_sh=["AverageNumberOfShares"],
)
FC_KEYS = ("sales", "op", "odp", "np", "eps")
NF_RE = re.compile(r"<ix:nonFraction\b([^>]*?)(/>|>(.*?)</ix:nonFraction>)", re.S | re.I)
ATTR_RE = re.compile(r'([\w:.-]+)="([^"]*)"')
CTX_RE = re.compile(r'<xbrli:context\b[^>]*\bid="([^"]+)"[^>]*>(.*?)</xbrli:context>', re.S)


def ix_values(html):
    """回傳 {context: {科目: 數值}}，數值已乘上 scale、處理負號；金額換成百萬日圓"""
    out = {}
    for attrs, _, inner in NF_RE.findall(html):
        a = dict(ATTR_RE.findall(attrs))
        name, ctx = a.get("name", "").split(":")[-1], a.get("contextRef", "")
        if not name or a.get("xsi:nil") == "true":
            continue
        txt = re.sub(r"<[^>]+>", "", inner or "").replace(",", "").replace(" ", "").strip()
        neg = txt.startswith(("△", "▲", "-", "−"))
        txt = txt.lstrip("△▲-−")
        try:
            v = float(txt)
        except ValueError:
            continue
        v *= 10 ** int(a.get("scale", "0") or 0)
        if a.get("sign") == "-" or neg:
            v = -v
        if a.get("unitRef", "").upper() == "JPY":
            v /= 1e6
        out.setdefault(ctx, {})[name] = v
    return out


def ix_periods(html):
    per = {}
    for cid, body in CTX_RE.findall(html):
        s = re.search(r"<xbrli:startDate>([\d-]+)<", body)
        e = re.search(r"<xbrli:endDate>([\d-]+)<", body)
        i = re.search(r"<xbrli:instant>([\d-]+)<", body)
        per[cid] = (s.group(1) if s else "", (e or i).group(1) if (e or i) else "")
    return per


def take(vals, ctxs, fields=None):
    out = {}
    for k in (fields or NAMES):
        for ctx in ctxs:
            row = vals.get(ctx)
            if not row:
                continue
            v = next((row[n] for n in NAMES[k] if n in row), None)
            if v is not None:
                out[k] = v
                break
    return out


def fc_of(vals, base):
    """預估值：優先 ForecastMember；區間預估（Lower／Upper）取中間值"""
    f = take(vals, [f"{base}_ForecastMember"], FC_KEYS)
    lo, hi = take(vals, [f"{base}_LowerMember"], FC_KEYS), take(vals, [f"{base}_UpperMember"], FC_KEYS)
    for k in FC_KEYS:
        if k not in f and k in lo and k in hi:
            f[k] = (lo[k] + hi[k]) / 2
    return f


def parse_td(html, fname, disc, tm, zipname):
    vals, per = ix_values(html), ix_periods(html)
    pre = re.search(r"tse-([a-z]+)-", fname)
    pre = pre.group(1) if pre else ""            # 例：qcedjpsm = 季報(q)・合併(c)・ed・日本基準(jp)・summary
    std = "IFRS" if pre[4:6] == "if" or any(k.endswith("IFRS") for v in vals.values() for k in v) else \
        "US" if pre[4:6] == "us" else "JP"
    cons = any("_ConsolidatedMember_" in c for c in vals)   # 合併公司也會有非合併的股利 context，所以只看有沒有合併
    mem = "ConsolidatedMember" if cons else "NonConsolidatedMember"
    # 本期：季報 CurrentAccumulatedQn、年報 CurrentYear
    typ, cur = None, None
    for n in (3, 2, 1):
        c = f"CurrentAccumulatedQ{n}Duration_{mem}_ResultMember"
        if c in vals and take(vals, [c], ("sales", "np", "op")):
            typ, cur = f"{n}Q", f"CurrentAccumulatedQ{n}"
            break
    if not typ:
        c = f"CurrentYearDuration_{mem}_ResultMember"
        if c in vals and take(vals, [c], ("sales", "np", "op")):
            typ, cur = "FY", "CurrentYear"
    rec = dict(src="T", id=zipname, disc=disc, time=tm, std=std, cons=cons, pre=pre, a={}, f={}, fh={}, nf={},
               nfh={}, p={})
    fy = per.get(f"CurrentYearDuration_{mem}_ForecastMember") or per.get(f"CurrentYearDuration_{mem}_ResultMember") \
        or per.get(f"CurrentYearDuration_AnnualMember_{mem}_ForecastMember") or ("", "")
    if typ:
        dctx = f"{cur}Duration_{mem}_ResultMember"
        ictx = [f"{cur}Instant_{mem}_ResultMember", f"{cur}Instant"]
        a = take(vals, [dctx], ("sales", "op", "odp", "np", "eps", "deps"))
        a.update(take(vals, ictx + [dctx, f"{cur}Duration"], ("ta", "eq", "sheq", "bps", "sh_out", "tr_sh", "avg_sh")))
        rec.update(type=typ, a=a, per_st=per.get(dctx, ("", ""))[0], per_end=per.get(dctx, ("", ""))[1])
        pctx = dctx.replace("Current", "Prior")
        rec["p"] = take(vals, [pctx], ("sales", "op", "odp", "np", "eps"))
        rec["p_end"] = per.get(pctx, ("", ""))[1]
        if typ == "FY":
            rec["fy_st"], rec["fy_end"] = per.get(dctx, ("", ""))
            rec["nf"] = fc_of(vals, f"NextYearDuration_{mem}")
            rec["nfh"] = fc_of(vals, f"NextAccumulatedQ2Duration_{mem}")
        else:
            rec["fy_st"], rec["fy_end"] = fy
            rec["f"] = fc_of(vals, f"CurrentYearDuration_{mem}")
            rec["fh"] = fc_of(vals, f"CurrentAccumulatedQ2Duration_{mem}")
    else:
        f = fc_of(vals, f"CurrentYearDuration_{mem}")
        if not f:
            # 認不得的格式（例如業績予想修正的新版 context）：只把 context 名稱記到 diag，之後再補
            DIAG.setdefault("td_unknown", []).append([pre, sorted(vals)[:30]])
            return None
        rec.update(type="REV", f=f, fh=fc_of(vals, f"CurrentAccumulatedQ2Duration_{mem}"),
                   fy_st=fy[0], fy_end=fy[1], per_end="")
    if not rec.get("fy_end"):
        return None
    if rec["type"] == "2Q" and pre.startswith("s"):
        rec["doc"] = "中間期"
    return rec


def td_list(day):
    rows, page = [], 1
    while page <= 40:
        try:
            html = http(f"{TD}I_list_{page:03d}_{day:%Y%m%d}.html", raw=True, tries=2).decode("utf-8", "replace")
        except RuntimeError as e:
            if "404" not in str(e):
                err(f"TDnet {day} p{page}: {e}")
            break
        for r in re.findall(r"<tr>(.*?)</tr>", html, re.S):
            z = re.search(r'href="([^"]+\.zip)"', r)
            code = re.search(r'kjCode"[^>]*>\s*([0-9A-Z]{4,5})', r)
            if not z or not code:
                continue
            title = re.search(r'kjTitle"[^>]*>(.*?)</td>', r, re.S)
            tm = re.search(r'kjTime"[^>]*>\s*([0-9:]+)', r)
            rows.append(dict(code=code.group(1), title=re.sub(r"<[^>]+>|\s+", "", title.group(1)) if title else "",
                             zip=z.group(1), time=tm.group(1) if tm else "", disc=f"{day:%Y-%m-%d}"))
        if f"I_list_{page + 1:03d}_" not in html:
            break
        page += 1
        time.sleep(0.5)
    return rows, page


def td_parse_zip(row):
    b = http(TD + row["zip"], raw=True, tries=2)
    zf = zipfile.ZipFile(io.BytesIO(b))
    out = []
    for n in zf.namelist():
        if "/Summary/" in n and n.endswith("ixbrl.htm"):
            rec = parse_td(zf.read(n).decode("utf-8", "replace"), n.split("/")[-1], row["disc"], row["time"],
                           row["zip"])
            if rec:
                rec["title"] = row["title"][:60]
                out.append(rec)
    return out


def td_scan(arch, codes):
    """掃 TDnet 公開清單（只保留約 1 個月）。第一次回補 31 天，之後掃最近 5 天；只下載追蹤股票的 XBRL。"""
    added = set(codes) - set(arch.get("codes", []))
    first = not arch.get("days") or bool(added)   # 第一次或新增追蹤股票 → 回補 31 天
    back = 31 if first else 5
    want = {c + "0": c for c in codes}
    seen = set(arch.setdefault("seen", []))
    days_done = arch.setdefault("days", {})
    n_days = n_rows = n_new = 0
    all_rows = []
    for i in range(back + 1):
        d = TODAY - dt.timedelta(days=i)
        if d.weekday() >= 5:
            continue
        key = f"{d:%Y-%m-%d}"
        if key in days_done and i >= 2 and not first:
            continue
        rows, pages = td_list(d)
        n_days += 1
        n_rows += len(rows)
        all_rows += rows
        days_done[key] = pages
        for r in rows:
            c = want.get(r["code"])
            if not c or r["zip"] in seen:
                continue
            try:
                recs = td_parse_zip(r)
                arch.setdefault("rec", {}).setdefault(c, []).extend(recs)
                n_new += len(recs)
                seen.add(r["zip"])
            except Exception as e:  # noqa
                err(f"TDnet {c} {r['zip']}: {e}")
            time.sleep(0.5)
        time.sleep(0.5)
    arch["codes"] = sorted(set(arch.get("codes", [])) | set(codes))
    arch["seen"] = sorted(seen)[-5000:]
    arch["days"] = dict(sorted(days_done.items())[-60:])
    DIAG["tdnet"] = dict(days_scanned=n_days, rows=n_rows, new_records=n_new, backfill=first)
    return all_rows


# ======================= 交叉驗證：TDnet 去年同期 vs J-Quants =======================
def validate_td(rows, n=6):
    cand, kinds = [], {}
    for r in rows:
        if "決算短信" in r["title"] and r["code"].endswith("0"):
            cand.append(r)
    out = dict(checked=0, fields={}, mismatch=[])
    for tries, r in enumerate(cand):
        if out["checked"] >= n or tries >= n * 4:
            break
        try:
            recs = td_parse_zip(r)
            rec = next((x for x in recs if x.get("p") and x.get("p_end")), None)
            if not rec:
                continue
            k = rec["pre"]
            if kinds.get(k, 0) >= 2:
                continue
            js = [norm_jq(x) for x in jq("/fins/summary", {"code": r["code"]}, plan=False)]
            j = next((x for x in js if x["per_end"] == rec["p_end"] and x["type"] == rec["type"]), None)
            if not j:
                continue
            kinds[k] = kinds.get(k, 0) + 1
            out["checked"] += 1
            for f, tv in rec["p"].items():
                jv = j["a"].get(f)
                if jv is None:
                    continue
                st = out["fields"].setdefault(f, [0, 0])
                ok = abs(tv - jv) <= max(abs(jv) * 0.001, 0.011 if f == "eps" else 0.5)
                st[0 if ok else 1] += 1
                if not ok:
                    out["mismatch"].append([r["code"], rec["pre"], f, round(tv / jv, 4) if jv else None])
        except Exception as e:  # noqa
            err(f"驗證 {r['code']}: {e}")
        time.sleep(0.5)
    DIAG["validate_tdnet"] = out


# ======================= 組合季資料 =======================
QORDER = {"1Q": 1, "2Q": 2, "3Q": 3, "FY": 4}


def cal_label(start, end):
    mid = D(start) + (D(end) - D(start)) / 2
    return f"{str(mid.year)[2:]}Q{(mid.month - 1) // 3 + 1}"


def fy_label(fy_end):
    return f"{fy_end[2:4]}/{int(fy_end[5:7])}期"


def fy_ok(r):
    try:
        n = (D(r["fy_end"]) - D(r["fy_st"])).days
        return 350 <= n <= 380
    except Exception:  # noqa
        return False


def ym_add(ym, n):
    return f"{int(ym[:4]) + n}{ym[4:7]}"


def build_quarters(recs, splits):
    """年初累計 → 單季。同一（會計年度, 季別）有多筆時：數值取最新一筆（更正），公布日取最早（河流圖不偷看未來）。
    會計年度以年底的「年-月」當鍵（2 月底公司的 2/28、2/29 才不會對不起來）"""
    best = {}
    for r in recs:
        if r.get("type") not in QORDER or not r.get("fy_end") or not r["a"]:
            continue
        if not fy_ok(r) or (r["type"] != "FY" and not r.get("per_end")):
            continue
        k = (r["fy_end"][:7], QORDER[r["type"]])
        o = best.get(k)
        stamp = (r["disc"], r.get("time", ""), r["src"] == "J")
        if not o:
            best[k] = dict(r, first=r["disc"], stamp=stamp)
        else:
            first = min(o["first"], r["disc"])
            if stamp >= o["stamp"]:
                merged = dict(r["a"])
                for kk, vv in o["a"].items():          # 新的一筆缺的科目沿用舊的
                    merged.setdefault(kk, vv)
                best[k] = dict(r, a=merged, first=first, stamp=stamp)
            else:
                for kk, vv in r["a"].items():
                    o["a"].setdefault(kk, vv)
                o["first"] = first
    rows = []
    for (fy, k), r in sorted(best.items()):
        fy_end = r["fy_end"]
        prev = best.get((fy, k - 1)) if k > 1 else None
        if k > 1 and (not prev or not prev.get("per_end")):
            continue                                   # 缺前一季累計 → 無法推算單季
        a, pa = r["a"], prev["a"] if prev else {}
        f, pf = split_factor(r["first"], splits), split_factor(prev["first"], splits) if prev else 1

        def q(field, ps=False):
            v = a.get(field)
            if v is None:
                return None
            if ps:
                v = v / f
            if k == 1:
                return v
            pv = pa.get(field)
            if pv is None:
                return None
            return v - (pv / pf if ps else pv)

        st = r["fy_st"] if k == 1 else (D(prev["per_end"]) + dt.timedelta(days=1)).isoformat()
        end = r["per_end"] if r.get("per_end") else fy_end
        sales = q("sales")
        if not sales or sales <= 0:
            continue
        eps = q("eps", True)
        npv = q("np")
        sh = a.get("avg_sh")
        if eps is None and npv is not None and sh:
            eps = npv / (sh * f / 1e6)
        shares = (a.get("sh_out") or 0) - (a.get("tr_sh") or 0)
        bps = a["sheq"] * 1e6 / shares / f if a.get("sheq") and shares > 0 else None
        pct = lambda v: None if v is None else round(v / sales * 100, 1)
        rows.append(dict(end=end, st=st, first=r["first"], fy_end=fy_end, k=k, src=r["src"], std=r.get("std", ""),
                         cal=cal_label(st, end), fis=f"{fy_label(fy_end)} {k}Q", sales=round(sales, 1),
                         om=pct(q("op")), odm=pct(q("odp")), nm=pct(npv), np=None if npv is None else round(npv, 1),
                         eps=None if eps is None else round(eps, 3),
                         sh=round(sh * f / 1e6, 3) if sh else None, bps=None if bps is None else round(bps, 2)))
    return rows, best


def forecast_block(recs, best, splits):
    """会社予想：目前會計年度的全年預估（含歷次修正）、上半年預估、年初累計實績與去年同期進度"""
    res = [r for r in recs if r.get("type") in QORDER and r.get("fy_end")]
    if not res:
        return None
    last = max(res, key=lambda r: (r["disc"], r.get("time", "")))
    cur = last["fy_end"][:7]
    if last["type"] == "FY":                            # 年報剛公布 → 目前年度是下一年
        cur = ym_add(cur, 1)
    prev_fy = ym_add(cur, -1)
    hist, h1 = [], None
    for r in sorted(recs, key=lambda r: (r["disc"], r.get("time", ""))):
        snap = h = None
        fy = (r.get("fy_end") or "")[:7]
        if fy == cur and r.get("type") in ("1Q", "2Q", "3Q", "REV"):
            snap, h = r.get("f"), r.get("fh")
        elif fy == prev_fy and r.get("type") == "FY":
            snap, h = r.get("nf"), r.get("nfh")
        if snap:
            f = split_factor(r["disc"], splits)
            row = [r["disc"]] + [None if snap.get(k) is None else round(snap[k] / f if k == "eps" else snap[k], 2)
                                 for k in FC_KEYS] + [r["src"]]
            if not hist or hist[-1][1:6] != row[1:6]:
                hist.append(row)
        if h:
            f = split_factor(r["disc"], splits)
            h1 = [r["disc"]] + [None if h.get(k) is None else round(h[k] / f if k == "eps" else h[k], 2)
                                for k in FC_KEYS]
    ytd = None
    ks = [k for (fy, k) in best if fy == cur]
    if ks:
        r = best[(cur, max(ks))]
        f = split_factor(r["first"], splits)
        ytd = dict(k=max(ks), per_end=r.get("per_end") or cur,
                   **{k: (None if r["a"].get(k) is None else round(r["a"][k] / f if k == "eps" else r["a"][k], 2))
                      for k in FC_KEYS})
    prior = None
    if ytd and (prev_fy, ytd["k"]) in best and (prev_fy, 4) in best:
        a, fa = best[(prev_fy, ytd["k"])]["a"], best[(prev_fy, 4)]["a"]
        prior = {k: round(a[k] / fa[k] * 100, 1) for k in FC_KEYS
                 if a.get(k) is not None and fa.get(k) and fa[k] > 0 and k != "eps"}
    return dict(fy=cur, label=f"{cur[2:4]}/{int(cur[5:7])}期", hist=hist[-8:], h1=h1, ytd=ytd, prior=prior)


# ======================= 組合個股 =======================
def read_block(recs, best, Q):
    """財報判讀（對公司預估，日股沒有市場預估 EPS）：每一季公布當下的
    ・進度率 pg＝年初累計 ÷ 當時的全年預估，pgp＝去年同期累計 ÷ 去年全年實績（比季節性，不是比 25%×季數）
    ・rev＝全年預估自上一季公布以來的修正幅度 %（含季中另外發的業績予想修正）
    ・年報那一季改看：ach＝全年實績 vs 3Q 時的預估 %，gd＝新年度預估 vs 剛出爐的全年實績 %
    指標 m 依序取有預估的第一個：營業利益 op → 經常利益 odp → 淨利 np。金額單位百萬日圓。
    tr＝過去各年度「全年實績 vs 期初預估」%（看這家公司預估習慣保守還是樂觀）。"""
    snaps = {}                                           # 會計年度 → [(公布日, 全年預估)]，依時間排序
    for r in sorted(recs, key=lambda r: (r["disc"], r.get("time", ""))):
        fy = (r.get("fy_end") or "")[:7]
        if not fy:
            continue
        if r.get("type") in ("1Q", "2Q", "3Q", "REV") and r.get("f"):
            snaps.setdefault(fy, []).append((r["disc"], r["f"]))
        elif r.get("type") == "FY" and r.get("nf"):
            snaps.setdefault(ym_add(fy, 1), []).append((r["disc"], r["nf"]))

    def asof(fy, day, m):
        v = None
        for d, f in snaps.get(fy, []):
            if day is not None and d <= day and f.get(m) is not None:
                v = f[m]
        return v

    lab = {(x["fy_end"][:7], x["k"]): x for x in Q}
    r1 = lambda v: None if v is None else round(v, 1)
    rows = []
    for (fy, k) in sorted(best):
        x = lab.get((fy, k))
        if not x:
            continue
        r, disc, a = best[(fy, k)], best[(fy, k)]["first"], best[(fy, k)]["a"]
        pk = (fy, k - 1) if k > 1 else (ym_add(fy, -1), 4)
        pdisc = best[pk]["first"] if pk in best else None
        nfy = ym_add(fy, 1)
        m = next((m for m in ("op", "odp", "np") if a.get(m) is not None and
                  (asof(fy, disc, m) is not None or (k == 4 and asof(nfy, disc, m) is not None))), None)
        row = dict(cal=x["cal"], fis=x["fis"], d=disc, k=k, m=m)
        if m:
            f0 = asof(fy, pdisc, m)
            if k < 4:
                f1 = asof(fy, disc, m)
                pa, pf = best.get((ym_add(fy, -1), k)), best.get((ym_add(fy, -1), 4))
                row.update(a=r1(a[m]), f=r1(f1), f0=r1(f0),
                           pg=r1(a[m] / f1 * 100) if f1 and f1 > 0 else None,
                           pgp=r1(pa["a"][m] / pf["a"][m] * 100) if pa and pf and pa["a"].get(m) is not None
                           and pf["a"].get(m) and pf["a"][m] > 0 else None,
                           rev=r1((f1 / f0 - 1) * 100) if f0 and f0 > 0 and f1 is not None else None)
            else:
                nf = asof(nfy, disc, m)
                row.update(a=r1(a[m]), f=r1(nf), f0=r1(f0),
                           ach=r1((a[m] / f0 - 1) * 100) if f0 and f0 > 0 else None,
                           gd=r1((nf / a[m] - 1) * 100) if nf is not None and a[m] > 0 else None)
        rows.append(row)
    tr = []
    for (fy, k) in sorted(best):
        if k != 4:
            continue
        a = best[(fy, k)]["a"]
        for m in ("op", "odp", "np"):
            init = next((f[m] for d, f in snaps.get(fy, []) if f.get(m) is not None), None)
            if init and init > 0 and a.get(m) is not None:
                tr.append([fy_label(best[(fy, k)]["fy_end"]), m, r1((a[m] / init - 1) * 100)])
                break
    return dict(rows=rows[-8:], tr=tr[-5:]) if rows else None


JQCAL = {}          # 代號 → J-Quants 決算發表預定日（免費版只給下一個營業日、且以 3／9 月決算公司為主，所以多數時候是空的）


def k_react(code, disc):
    """決算公布後下一個交易日的漲跌 %（收盤 vs 前一收盤）；還沒有隔日股價回 None"""
    rows = YK.get(code) or []
    i = next((i for i, r in enumerate(rows) if r[0] > disc), None)
    return round((rows[i][4] / rows[i - 1][4] - 1) * 100, 1) if i and rows[i - 1][4] else None


def next_block(code, best):
    """下一次決算公布日。日本沒有免費的完整決算行事曆，所以依序：
    jq＝J-Quants 發表預定日（有就是公司已公告的日期）
    py＝去年同一季的公布日 ＋ 364 天（同一個星期幾；日本公司每年公布日很固定，通常差不到一週）
    lag＝沒有去年同季（新上市等）→ 下一季季末 ＋ 上一次「季末到公布」的天數
    回傳 dict(d 日期, fis 會計季, k, src, pd 去年同季公布日)"""
    if not best:
        return None
    fy, k = max(best)
    last = best[(fy, k)]
    nfy, nk = (fy, k + 1) if k < 4 else (ym_add(fy, 1), 1)
    fis = f"{nfy[2:4]}/{int(nfy[5:7])}期 {nk}Q"
    c = JQCAL.get(code)
    if c and c > last["first"]:
        return dict(d=c, fis=fis, k=nk, src="jq")
    py = best.get((ym_add(nfy, -1), nk))
    if py:
        return dict(d=(D(py["first"]) + dt.timedelta(days=364)).isoformat(), fis=fis, k=nk, src="py", pd=py["first"])
    end = last.get("per_end") if k < 4 else last.get("fy_end")
    if end:
        lag = (D(last["first"]) - D(end)).days
        e = D(end)
        m = e.year * 12 + e.month - 1 + 3
        nxt_end = dt.date(m // 12 + (m % 12 == 11), (m % 12 + 1) % 12 + 1, 1) - dt.timedelta(days=1)   # 三個月後的月底
        if 0 < lag < 120:
            return dict(d=(nxt_end + dt.timedelta(days=lag)).isoformat(), fis=fis, k=nk, src="lag")
    return None


def build(code, jq_recs, td_recs, master):
    cfg = CFG[code]
    px, splits = yahoo(code)
    recs = [r for r in jq_recs + td_recs if r]
    Q, best = build_quarters(recs, splits)
    fc = forecast_block(recs, best, splits)
    try:
        rd = read_block(recs, best, Q)
    except Exception as e:  # noqa   判讀只是附加資訊，算不出來不能拖垮整檔
        rd = None
        err(f"判讀 {code}: {e}")
    try:
        nx = next_block(code, best)
    except Exception as e:  # noqa
        nx = None
        err(f"下次決算 {code}: {e}")
    std = Q[-1]["std"] if Q else ""

    # 財報多在 15:00 收盤前後公布 → 從公布日的「下一個交易日」起才採用（同 J-Quants 估值，不偷看未來）
    def ttm_at(day):
        av = [q for q in Q if q["first"] < day and q["eps"] is not None]
        if len(av) < 4:
            return None
        l4 = av[-4:]
        if (D(l4[-1]["end"]) - D(l4[0]["end"])).days > 300:
            return None
        return sum(q["eps"] for q in l4)

    def bps_at(day):
        av = [q for q in Q if q["first"] < day and q["bps"]]
        return av[-1]["bps"] if av else None

    # 流通股數（期末發行 − 庫藏股），依分割調整到目前股價基準；取 day 之前最新一份財報
    shr_recs = sorted((r for r in recs if r.get("a", {}).get("sh_out")), key=lambda r: (r["disc"], r.get("time", "")))

    def shares_at(day):
        av = [r for r in shr_recs if r["disc"] < day]
        if not av:
            return None
        a0 = av[-1]["a"]
        return (a0["sh_out"] - (a0.get("tr_sh") or 0)) * split_factor(av[-1]["disc"], splits)

    mon = {}
    for d, c in px:
        mon[d[:7]] = (d, c)
    riv = []
    for ym in sorted(mon):
        d, c = mon[ym]
        t, b = ttm_at(d), bps_at(d)
        riv.append([ym, round(c, 1), None if t is None else round(t, 2), None if b is None else round(b, 1),
                    round(c / t, 1) if t and t > 0 else None, round(c / b, 2) if b and b > 0 else None])
    val_chk = None
    if VALIDATE and JQ_KEY:
        # 交叉比對：自己算的本益比／淨值比 vs J-Quants 官方估值（最近 8 個月底）。
        # 比例不受分割影響，所以同時驗證近四季 EPS、每股淨值、分割調整與 Yahoo 股價；只輸出比例
        try:
            import bisect
            pxd = dict(px)
            dates = sorted(pxd)
            px_on = lambda d: pxd[dates[bisect.bisect_right(dates, d) - 1]] if bisect.bisect_right(dates, d) else None
            bym = {}
            for v in jq("/equities/valuation", {"code": code}):
                if num(v.get("PER")) and num(v.get("PBR")):
                    bym[v["Date"][:7]] = v
            pe_r, pb_r, mc_r = [], [], []
            for ym in sorted(bym)[-8:]:
                v = bym[ym]
                c, t0, b0 = px_on(v["Date"]), ttm_at(v["Date"]), bps_at(v["Date"])
                s0 = shares_at(v["Date"])
                if c and s0 and num(v.get("MktCap")):
                    mc_r.append(round(c * s0 / 1e6 / num(v["MktCap"]), 3))
                if c and t0 and t0 > 0:
                    pe_r.append(round(c / t0 / num(v["PER"]), 3))
                if c and b0 and b0 > 0:
                    pb_r.append(round(c / b0 / num(v["PBR"]), 3))
            val_chk = dict(pe=pe_r, pb=pb_r, cap=mc_r)
        except Exception as e:  # noqa
            err(f"估值比對 {code}: {e}")
    (ld, lc), (pd, pc) = px[-1], px[-2] if len(px) > 1 else px[-1]
    t, b = ttm_at(ld), bps_at(ld)
    feps = None
    if fc and fc["hist"] and fc["hist"][-1][5]:
        feps = fc["hist"][-1][5]
    last = dict(date=ld, close=round(lc, 1), prev=round(pc, 1), ttm=None if t is None else round(t, 2),
                bps=None if b is None else round(b, 1), pe=round(lc / t, 1) if t and t > 0 else None,
                pb=round(lc / b, 2) if b and b > 0 else None, fpe=round(lc / feps, 1) if feps and feps > 0 else None)
    sh_now = shares_at("9999")
    last["cap"] = round(lc * sh_now / 1e8, 1) if sh_now else None          # 市值（億日圓）
    l4 = Q[-4:]
    last["rev4"] = round(sum(x["sales"] for x in l4) / 100, 1) if len(l4) == 4 else None   # 近四季營收（億日圓）
    q = [[x["cal"], x["fis"], x["sales"], x["om"], x["odm"], x["nm"], x["eps"], x["np"], x["sh"], x["end"],
          x["first"], x["src"], x["fy_end"], x["k"]] for x in Q]
    note = []
    bb = BASIS_BREAK.get(code)
    if bb:
        fy0, k0, why = bb
        seq = lambda x: (int(x["fy_end"][:4]) - int(fy0[:4])) * 4 + x["k"] - k0     # 距離變更季幾季（同一個決算月）
        for row, x in zip(q, Q):
            n = seq(x) if x["fy_end"][5:7] == fy0[5:7] else None
            row.append(None if n is None else 1 if n == 0 and k0 > 1 else 2 if (0 <= n <= 3 if k0 == 1 else 1 <= n <= 4) else None)
        if any(row[14] for row in q):
            hit = next((x["cal"] for row, x in zip(q, Q) if row[14]), "")
            note.append(f"口徑變更：{why}。" + (f"{hit} 單季營收與利益率是新舊口徑相減，不可用；" if k0 > 1 else "") +
                        "之後四季的營收年增也不可比。淨利、EPS、本益比不受影響")
    if splits:
        note.append("每股數字已依分割調整：" + "、".join(f"{d} 1拆{n:g}" for d, n in splits if d >= f"{TODAY.year - YEARS}"))
    if len(Q) < 8:
        note.append(f"財報目前只有 {len(Q)} 季（J-Quants 免費版只給 2 年），本益比河流圖較短，之後每日存檔會慢慢變長")
    m = master.get(code, {})
    # 檢查（只輸出到 diag）：EPS × 平均股數 ≈ 淨利
    chk = [abs(x["eps"] * x["sh"] / x["np"] - 1) < 0.03 for x in Q if x["eps"] and x["sh"] and x["np"]]
    DIAG["stocks"][code] = dict(yname=YNAME.get(code), jname=m.get("CoName"), px_n=len(px), px_last=ld, q_n=len(Q), q_first=Q[0]["cal"] if Q else None,
                                q_last=Q[-1]["cal"] if Q else None, k_n=sum(map(len, k_split(YK.get(code) or []))), q_src="".join(x["src"] for x in Q),
                                fc_n=len(fc["hist"]) if fc else 0, fc_fy=fc["fy"] if fc else None, rd_n=len(rd["rows"]) if rd else 0, nx=[nx["d"], nx["src"]] if nx else None,
                                eps_np_ok=f"{sum(chk)}/{len(chk)}", splits=[[d, round(n, 4)] for d, n in splits], std=std,
                                riv_pe=sum(1 for r in riv if r[4]), riv_pb=sum(1 for r in riv if r[5]),
                                **({"val_vs_jq": val_chk} if val_chk else {}))
    return dict(id=code, name=cfg["zh"], jname=m.get("CoName", ""), sector=m.get("S33Nm", ""), mkt=m.get("MktNm", ""),
                theme=cfg["theme"], cyclical="C" in cfg["flags"], tw=cfg["tw"], std=std,
                updated=NOW_JST.strftime("%Y-%m-%d %H:%M"), last=last, q=q, riv=riv, fc=fc, note=note,
                k=k_split(YK.get(code) or [])[1], rd=rd, nx=nx)


# ======================= 首頁／主題頁用的統計（預先算好放進 index.bin，前端只解密一次） =======================
def stat_of(d):
    """回傳 {ry 營收年增%, ey 近四季EPS年增%, ek 虧損／轉盈, peg, mtd 本月至今%, ny 單季淨利年增%,
    pg 營業利益進度%, pgp 去年同期進度%, pk 第幾季累計, bb 口徑變更}；算不出來的鍵不放。規則同台股／美股站的 statOf。
    q 欄位：2 營收 6 EPS 7 淨利 12 會計年度底 13 第幾季"""
    o, q, L = {}, d.get("q") or [], d.get("last") or {}
    if q:
        lq = q[-1]
        fy, k = lq[12][:7], lq[13]
        p = next((x for x in q if x[12][:7] == ym_add(fy, -1) and x[13] == k), None)
        if len(lq) > 14 and lq[14]:
            o["bb"] = lq[14]                                      # 口徑變更期間：營收年增不可比，不給 ry
        elif p and p[2] and p[2] > 0 and lq[2] is not None:
            o["ry"] = round((lq[2] / p[2] - 1) * 100, 1)
        if p and p[7] and p[7] > 0 and lq[7] is not None:
            o["ny"] = round((lq[7] / p[7] - 1) * 100, 1)
    if len(q) >= 8:
        w = q[-8:]
        nxt = lambda x: (x[12][:7], x[13] + 1) if x[13] < 4 else (ym_add(x[12][:7], 1), 1)
        if all(nxt(w[i - 1]) == (w[i][12][:7], w[i][13]) for i in range(1, 8)) and all(x[6] is not None for x in w):
            a, b = sum(x[6] for x in w[4:]), sum(x[6] for x in w[:4])
            if a <= 0:
                o["ek"] = "虧損"
            elif b <= 0:
                o["ek"] = "轉盈"
            else:
                o["ey"] = round((a / b - 1) * 100, 1)
    if L.get("pe") and o.get("ey") and 0 < o["ey"] <= 300:        # 年增 >300% 是低基期，不算 PEG
        o["peg"] = round(L["pe"] / o["ey"], 2)
    r = d.get("riv") or []
    if len(r) >= 2 and r[-2][1] and r[-1][0] == (L.get("date") or "")[:7]:
        o["mtd"] = round((r[-1][1] / r[-2][1] - 1) * 100, 1)
    fc = d.get("fc") or {}
    if fc.get("hist") and fc.get("ytd"):
        f_op, a_op = fc["hist"][-1][2], fc["ytd"].get("op")
        if f_op and f_op > 0 and a_op is not None:
            o["pg"], o["pk"] = round(a_op / f_op * 100, 1), fc["ytd"]["k"]
            pp = (fc.get("prior") or {}).get("op")
            if pp is not None:
                o["pgp"] = pp
    return o


def cal_of(code, d):
    """首頁決算日曆用（放進 index.bin）：nx 下次決算 [日期, 會計季, 來源]；lr 最近一次決算的判讀列（同 rd.rows 的最後一列）；rx 那次的隔日漲跌 %"""
    o = {}
    if d.get("nx"):
        o["nx"] = [d["nx"]["d"], d["nx"]["fis"], d["nx"]["src"]]
    rows = (d.get("rd") or {}).get("rows") or []
    if rows:
        o["lr"] = rows[-1]
        rx = k_react(code, rows[-1]["d"])
        if rx is not None:
            o["rx"] = rx
    return o


def main():
    if not PASS or len(PASS) < 8:
        print("❌ 沒有設定 JP_DATA_KEY（至少 8 字）→ 為遵守 J-Quants 條款，不寫出任何資料", file=sys.stderr)
        sys.exit(1)
    codes = [c.upper() for c in sys.argv[1:]] or STOCKS
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    meta = load_meta()
    aes = make_key(meta)
    meta["kcv"] = base64.b64encode(enc(aes, {"ok": "jp"})).decode()
    # 存檔（加密）：TDnet 解析結果、J-Quants 財報（免費版視窗只有 2 年，存起來才會越來越長）
    arch = {}
    for name in ("tdnet", "jq"):
        p = RAW / f"{name}.bin"
        if p.exists():
            try:
                arch[name] = dec(aes, p.read_bytes())
            except Exception:  # noqa
                err(f"{name}.bin 解密失敗（密語換過？）→ 重新建立")
    td, jqa = arch.get("tdnet", {}), arch.get("jq", {})
    # J-Quants：清單＋各檔財報
    master = {}
    if JQ_KEY:
        try:
            for r in jq("/equities/master", {}):
                if r.get("Code", "")[:4] in CFG and r.get("Code", "").endswith("0"):
                    master[r["Code"][:4]] = r
        except Exception as e:  # noqa
            err(f"J-Quants master: {e}")
        for c in codes:
            try:
                rows = jq("/fins/summary", {"code": c}, plan=False)
                old = {r["id"]: r for r in jqa.get(c, [])}
                for r in rows:
                    n = norm_jq(r)
                    old[n["id"]] = n
                jqa[c] = sorted(old.values(), key=lambda r: (r["disc"], r["time"]))
            except Exception as e:  # noqa
                err(f"J-Quants fins {c}: {e}")
    else:
        err("沒有 JQUANTS_API_KEY：只用存檔的 J-Quants 資料")
    if JQ_KEY:
        try:   # 決算發表預定日：只留追蹤清單、今天以後
            for r in jq("/equities/earnings-calendar", {}):
                c, day = str(r.get("Code", ""))[:4], str(r.get("Date", ""))[:10]
                if c in CFG and day >= TODAY.isoformat():
                    JQCAL[c] = day
        except Exception as e:  # noqa
            err(f"J-Quants 決算預定日: {e}")
    DIAG["jq_cal"] = len(JQCAL)
    DIAG["jq"] = dict(master=len(master), fins={c: len(jqa.get(c, [])) for c in codes},
                      last_disc={c: max((r["disc"] for r in jqa.get(c, [])), default=None) for c in codes})
    # TDnet
    rows = []
    try:
        rows = td_scan(td, codes)
    except Exception as e:  # noqa
        err(f"TDnet: {e}")
    if JQ_KEY and rows:
        validate_td(rows, 12 if VALIDATE else 4)
    # 組合、加密輸出
    idx_p = OUT / "index.bin"
    try:
        old = dec(aes, idx_p.read_bytes()) if idx_p.exists() else []
        idx = {s["id"]: s for s in (old["stocks"] if isinstance(old, dict) else old)}
    except Exception:  # noqa
        idx = {}
    fx = None
    def yclose(sym):
        j = http(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=5d&interval=1d")
        cl = [x for x in j["chart"]["result"][0]["indicators"]["quote"][0]["close"] if x]
        return cl[-1] if cl else None
    try:   # 日圓 → 台幣：用美元交叉匯率（USD/TWD ÷ USD/JPY）；JPYTWD=X 報價只有 1 位小數（0.2），誤差約 5%
        twd, jpy = yclose("TWD=X"), yclose("JPY=X")
        fx = round(twd / jpy, 5) if twd and jpy else None
        DIAG["fx_src"] = {"usdtwd": twd, "usdjpy": jpy}
    except Exception as e:  # noqa
        err(f"匯率: {e}")
    DIAG["fx_jpytwd"] = fx
    ok = []
    for c in codes:
        try:
            d = build(c, jqa.get(c, []), td.get("rec", {}).get(c, []), master)
            (OUT / f"{c}.bin").write_bytes(enc(aes, d))
            L, lq = d["last"], d["q"][-1] if d["q"] else None
            idx[c] = dict(id=c, name=d["name"], jname=d["jname"], theme=d["theme"], tw=d["tw"], cyc=d["cyclical"],
                          close=L["close"], chg=round((L["close"] / L["prev"] - 1) * 100, 2) if L["prev"] else None,
                          pe=L["pe"], pb=L["pb"], fpe=L["fpe"], lq=lq[0] if lq else None, date=L["date"],
                          cap=L["cap"], rev4=L["rev4"], fx=fx or (idx.get(c) or {}).get("fx"), **stat_of(d), **cal_of(c, d))
            d["last"]["fx"] = idx[c]["fx"]
            (OUT / f"{c}.bin").write_bytes(enc(aes, d))
            kh, kp = k_split(YK.get(c) or [])[0], OUT / "k" / f"{c}.bin"     # 日 K 歷史：內容沒變就不重寫
            try:
                same = kp.exists() and dec(aes, kp.read_bytes()) == kh
            except Exception:  # noqa
                same = False
            if kh and not same:
                kp.parent.mkdir(parents=True, exist_ok=True)
                kp.write_bytes(enc(aes, kh))
            ok.append(c)
            print(f"{c} ok  q={len(d['q'])} last={lq[0] if lq else '-'} fc={'Y' if d['fc'] else '-'}")
        except Exception as e:  # noqa
            err(f"{c}: {e}")
        time.sleep(0.5)
    order = [c for c in STOCKS if c in idx]
    idx_p.write_bytes(enc(aes, {"stocks": [idx[c] for c in order], "themes": THEME_META}))
    (RAW / "tdnet.bin").write_bytes(enc(aes, td))
    (RAW / "jq.bin").write_bytes(enc(aes, jqa))
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), "utf-8")
    DIAG["ok"] = ok
    (OUT / "diag.json").write_text(json.dumps(DIAG, ensure_ascii=False, indent=1), "utf-8")
    print(f"完成 {len(ok)}／{len(codes)}；錯誤 {len(DIAG['errors'])}")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
