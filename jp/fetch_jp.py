"""日股估值看板：Yahoo 股價 ＋ J-Quants 免費版（歷史財報）＋ TDnet 決算短信 XBRL（最新財報、会社予想）
→ 加密寫到 jp/data/{代號}.bin、jp/data/index.bin；歷史存檔加密在 jp/raw/*.bin。

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
    ("🧱 半導體設備", [("8035", "東京威力科創", "")],
     [("3131", "弘塑"), ("3583", "辛耘"), ("6187", "萬潤"), ("6223", "旺矽"), ("6515", "穎崴")]),
    ("⚡ 被動元件", [("6981", "村田製作所", "")],
     [("2327", "國巨"), ("2492", "華新科"), ("3026", "禾伸堂")]),
    ("💿 矽晶圓／材料", [("4063", "信越化學", "C")],
     [("6488", "環球晶"), ("5483", "中美晶"), ("6182", "合晶")]),
]
CFG = {c: dict(theme=th, zh=zh, flags=f, tw=tw) for th, items, tw in THEMES for c, zh, f in items}
STOCKS = list(CFG)

ROOT = Path(__file__).resolve().parent
OUT, RAW = ROOT / "data", ROOT / "raw"
JQ = "https://api.jquants.com/v2"
JQ_KEY = os.environ.get("JQUANTS_API_KEY", "").strip()
PASS = unicodedata.normalize("NFC", os.environ.get("JP_DATA_KEY", "").strip())
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
def yahoo(code):
    j = http(f"https://query1.finance.yahoo.com/v8/finance/chart/{code}.T"
             f"?range={YEARS}y&interval=1d&events=div%2Csplit&includeAdjustedClose=true")
    r = (j.get("chart", {}).get("result") or [None])[0]
    if not r or not r.get("timestamp"):
        raise RuntimeError(f"Yahoo 沒有 {code}.T 股價")
    day = lambda t: (dt.datetime.utcfromtimestamp(t) + dt.timedelta(hours=9)).strftime("%Y-%m-%d")
    q = r["indicators"]["quote"][0]
    px = {}
    for t, c, v in zip(r["timestamp"], q.get("close") or [], q.get("volume") or []):
        if c:
            px[day(t)] = c          # Yahoo close：已做分割調整、未做除息調整
    splits = sorted((day(int(k)), (s.get("numerator") or 1) / (s.get("denominator") or 1))
                    for k, s in (r.get("events", {}).get("splits") or {}).items())
    return sorted(px.items()), [(d, f) for d, f in splits if f and abs(f - 1) > 1e-9]


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
    first = not arch.get("days")
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
def build(code, jq_recs, td_recs, master):
    cfg = CFG[code]
    px, splits = yahoo(code)
    recs = [r for r in jq_recs + td_recs if r]
    Q, best = build_quarters(recs, splits)
    fc = forecast_block(recs, best, splits)
    std = Q[-1]["std"] if Q else ""

    def ttm_at(day):
        av = [q for q in Q if q["first"] <= day and q["eps"] is not None]
        if len(av) < 4:
            return None
        l4 = av[-4:]
        if (D(l4[-1]["end"]) - D(l4[0]["end"])).days > 300:
            return None
        return sum(q["eps"] for q in l4)

    def bps_at(day):
        av = [q for q in Q if q["first"] <= day and q["bps"]]
        return av[-1]["bps"] if av else None

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
            pe_r, pb_r = [], []
            for ym in sorted(bym)[-8:]:
                v = bym[ym]
                c, t0, b0 = px_on(v["Date"]), ttm_at(v["Date"]), bps_at(v["Date"])
                if c and t0 and t0 > 0:
                    pe_r.append(round(c / t0 / num(v["PER"]), 3))
                if c and b0 and b0 > 0:
                    pb_r.append(round(c / b0 / num(v["PBR"]), 3))
            val_chk = dict(pe=pe_r, pb=pb_r)
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
    q = [[x["cal"], x["fis"], x["sales"], x["om"], x["odm"], x["nm"], x["eps"], x["np"], x["sh"], x["end"],
          x["first"], x["src"], x["fy_end"], x["k"]] for x in Q]
    note = []
    if splits:
        note.append("每股數字已依分割調整：" + "、".join(f"{d} 1拆{n:g}" for d, n in splits if d >= f"{TODAY.year - YEARS}"))
    if len(Q) < 8:
        note.append(f"財報目前只有 {len(Q)} 季（J-Quants 免費版只給 2 年），本益比河流圖較短，之後每日存檔會慢慢變長")
    m = master.get(code, {})
    # 檢查（只輸出到 diag）：EPS × 平均股數 ≈ 淨利
    chk = [abs(x["eps"] * x["sh"] / x["np"] - 1) < 0.03 for x in Q if x["eps"] and x["sh"] and x["np"]]
    DIAG["stocks"][code] = dict(px_n=len(px), px_last=ld, q_n=len(Q), q_first=Q[0]["cal"] if Q else None,
                                q_last=Q[-1]["cal"] if Q else None, q_src="".join(x["src"] for x in Q),
                                fc_n=len(fc["hist"]) if fc else 0, fc_fy=fc["fy"] if fc else None,
                                eps_np_ok=f"{sum(chk)}/{len(chk)}", splits=[[d, round(n, 4)] for d, n in splits], std=std,
                                riv_pe=sum(1 for r in riv if r[4]), riv_pb=sum(1 for r in riv if r[5]),
                                **({"val_vs_jq": val_chk} if val_chk else {}))
    return dict(id=code, name=cfg["zh"], jname=m.get("CoName", ""), sector=m.get("S33Nm", ""), mkt=m.get("MktNm", ""),
                theme=cfg["theme"], cyclical="C" in cfg["flags"], tw=cfg["tw"], std=std,
                updated=NOW_JST.strftime("%Y-%m-%d %H:%M"), last=last, q=q, riv=riv, fc=fc, note=note)


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
        idx = {s["id"]: s for s in dec(aes, idx_p.read_bytes())} if idx_p.exists() else {}
    except Exception:  # noqa
        idx = {}
    ok = []
    for c in codes:
        try:
            d = build(c, jqa.get(c, []), td.get("rec", {}).get(c, []), master)
            (OUT / f"{c}.bin").write_bytes(enc(aes, d))
            L, lq = d["last"], d["q"][-1] if d["q"] else None
            idx[c] = dict(id=c, name=d["name"], jname=d["jname"], theme=d["theme"], tw=d["tw"], cyc=d["cyclical"],
                          close=L["close"], chg=round((L["close"] / L["prev"] - 1) * 100, 2) if L["prev"] else None,
                          pe=L["pe"], pb=L["pb"], fpe=L["fpe"], lq=lq[0] if lq else None, date=L["date"])
            ok.append(c)
            print(f"{c} ok  q={len(d['q'])} last={lq[0] if lq else '-'} fc={'Y' if d['fc'] else '-'}")
        except Exception as e:  # noqa
            err(f"{c}: {e}")
        time.sleep(0.5)
    order = [c for c in STOCKS if c in idx]
    idx_p.write_bytes(enc(aes, [idx[c] for c in order]))
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
