"""台股總經對照資料 → data/macro.json（macro.html 用）

兩塊資料（彼此獨立，任一塊失敗不影響另一塊）：
1. 發行量加權股價指數月底收盤：證交所 MI_5MINS_HIST（某月每日開高低收，每月 1 次請求，間隔 3.5 秒）
   → idx[] 每月一筆 [年月, 日期, 收盤, 本月未結束=1]；從最新月份往回補到 2000/1，每次最多 IDXMAX 個月（環境變數，預設 60）
   本月每次都重抓（取最新一天）；上個月若上次抓時還沒結束也重抓一次
   備援：FinMind TaiwanStockPrice data_id=TAIEX（一次拿全部歷史；證交所完全抓不到時才用）
2. GDP：主計總處開放資料「國民所得統計-常用資料」XML（季 NA8101A1Q、年 NA8101A1A，政府資料開放平臺 6799／44218）
   → gdp[] 每季一筆 [年季, 名目GDP(億), 經濟成長率%(實質), 名目年增%, 近四季名目GDP(億), 註記 p/f]
   → gdpY[] 每年一筆 [年, 名目GDP(億), 經濟成長率%]
   XML 欄位名稱由程式比對關鍵字（國內生產毛額／當期價格／經濟成長率），比對不到時把原始樣本寫進 diag 供修正解析

用法：python fetch_macro.py         （IDXMAX=400 python fetch_macro.py 一次補完指數歷史，約 20 分鐘）
"""
import json, os, re, sys, time, ssl, subprocess, tempfile, datetime as dt
from pathlib import Path
import urllib.request, urllib.parse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data"
UA = "Mozilla/5.0 (tw-valuation; GitHub Actions)"
IDXMAX = int(os.environ.get("IDXMAX") or 60)
IDX_START = (2000, 1)
TOKEN = os.environ.get("FINMIND_TOKEN", "")
TODAY = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date()
DIAG = {"idx": {"tries": [], "notes": []}, "gdp": {"tries": [], "notes": []}}
TW = {"last": 0.0, "n": 0}


# ---------------------------------------------------------------- 共用
def num(s):
    s = re.sub(r"[,\s%]", "", str(s if s is not None else ""))
    s = re.sub(r"[()pfrPFR*＊]+$", "", s)          # 主計總處的 p（初步）、f（預測）、r（修正）註記
    if s in ("", "-", "--", "---", "…", "N/A", "NA"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load(path, default):
    try:
        return json.loads(Path(path).read_text("utf-8"))
    except Exception:
        return default


CTX = {}


def chain_ctx(host):
    """伺服器沒送中繼憑證（主計總處 TWCA 憑證在 GitHub runner 上 unable to get local issuer certificate）：
    用 openssl 讀出伺服器憑證的 AIA「CA Issuers」網址，下載中繼憑證加進信任清單。
    仍然完整驗證：中繼憑證本身必須鏈到系統內建的根憑證，主機名稱也照常比對（不是關掉驗證）"""
    if host in CTX:
        return CTX[host]
    ctx = None
    try:
        leaf = subprocess.run(["openssl", "s_client", "-connect", f"{host}:443", "-servername", host, "-showcerts"],
                              input=b"", capture_output=True, timeout=30).stdout.decode("latin-1")
        pems = re.findall(r"-----BEGIN CERTIFICATE-----.+?-----END CERTIFICATE-----", leaf, re.S)
        extra = []
        todo = pems[:1]
        for _ in range(3):                      # 最多往上找 3 層
            if not todo:
                break
            pem = todo.pop()
            aia = subprocess.run(["openssl", "x509", "-noout", "-ext", "authorityInfoAccess"], input=pem.encode(),
                                 capture_output=True, timeout=10).stdout.decode()
            m = re.search(r"CA Issuers - URI:(\S+)", aia)
            if not m:
                break
            st, der = http(m.group(1), timeout=30, ctx=False)
            if st != 200 or not der:
                break
            if b"BEGIN CERTIFICATE" not in der:
                der = subprocess.run(["openssl", "x509", "-inform", "DER", "-outform", "PEM"], input=der,
                                     capture_output=True, timeout=10).stdout
            extra.append(der.decode())
            todo.append(der.decode())
        DIAG["gdp"]["notes"].append(f"{host}：伺服器送 {len(pems)} 張憑證，補下載中繼憑證 {len(extra)} 張")
        if extra:
            ctx = ssl.create_default_context()
            ctx.load_verify_locations(cadata="\n".join(extra))
    except Exception as e:
        DIAG["gdp"]["notes"].append(f"{host} 補中繼憑證失敗：{e!r}")
    CTX[host] = ctx
    return ctx


def http(url, timeout=60, headers=None, ctx=None):
    """GET → (status, bytes)；失敗回 (ERR 字串, b'')。遇到缺中繼憑證自動補（見 chain_ctx）後重試一次"""
    r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*", **(headers or {})})
    try:
        with urllib.request.urlopen(r, timeout=timeout, context=ctx or None) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        if ctx is None and "CERTIFICATE_VERIFY_FAILED" in str(e):
            c2 = chain_ctx(urllib.parse.urlsplit(url).hostname)
            if c2:
                return http(url, timeout, headers, c2)
        return f"ERR {e}", b""


# ---------------------------------------------------------------- 1. 加權指數
def twse_json(url):
    """證交所 rwd JSON（每次間隔 3.5 秒；失敗回 None）"""
    w = TW["last"] + 3.5 - time.time()
    if w > 0:
        time.sleep(w)
    TW["n"] += 1
    t0 = time.time()
    st, raw = http(url, headers={"Accept": "application/json,text/plain,*/*"})
    TW["last"] = time.time()
    try:
        js = json.loads(raw.decode("utf-8-sig"))
    except Exception:
        js = None
    DIAG["idx"]["tries"].append({"q": url.split("?")[-1][:30], "status": st, "len": len(raw), "sec": round(time.time() - t0, 1),
                                 "stat": js.get("stat") if isinstance(js, dict) else None})
    return js if isinstance(js, dict) else None


def roc_date(s):
    """'115/10/20' → date；也接受 '2026/10/20'、'20261020'"""
    m = re.match(r"\s*(\d{2,4})[/-](\d{1,2})[/-](\d{1,2})", str(s)) or re.match(r"\s*(\d{4})(\d{2})(\d{2})", str(s))
    if not m:
        return None
    y, mo, d = (int(x) for x in m.groups())
    if y < 1911:
        y += 1911
    try:
        return dt.date(y, mo, d)
    except ValueError:
        return None


def fetch_index_month(y, m):
    """某月每日收盤 → [(date, close)]；None = 請求失敗，[] = 該月無資料"""
    js = twse_json(f"https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST?date={y}{m:02d}01&response=json")
    if js is None:
        return None
    if js.get("stat") != "OK" and not js.get("data"):
        return []
    fields, rows = js.get("fields") or [], js.get("data") or []
    ic = next((i for i, f in enumerate(fields) if "收盤" in str(f)), len(fields) - 1 if fields else 4)
    out = []
    for r in rows:
        d = roc_date(r[0]) if r else None
        v = num(r[ic]) if r and len(r) > ic else None
        if d and v and d.year == y and d.month == m:
            out.append((d, v))
    return sorted(out)


def month_iter(start, end):
    y, m = end
    while (y, m) >= start:
        yield y, m
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)


def update_index(old):
    """old: {ym: [ym, date, close, partial]}；回傳更新後 dict"""
    cur = {r[0]: r for r in old}
    done = 0
    todo = []
    this = (TODAY.year, TODAY.month)
    for y, m in month_iter(IDX_START, this):
        ym = f"{y}-{m:02d}"
        r = cur.get(ym)
        if (y, m) == this or r is None or (len(r) > 3 and r[3]):
            todo.append((y, m))
    for y, m in todo:
        if done >= IDXMAX:
            DIAG["idx"]["notes"].append(f"達到 IDXMAX={IDXMAX}，剩 {len(todo) - done} 個月下次再補")
            break
        rows = fetch_index_month(y, m)
        done += 1
        if rows is None:
            DIAG["idx"]["notes"].append(f"{y}-{m:02d} 請求失敗，下次再補")
            if sum(1 for t in DIAG["idx"]["tries"][-3:] if t["status"] != 200) >= 3:
                DIAG["idx"]["notes"].append("證交所連續失敗 3 次，本次停止")
                break
            continue
        if not rows:
            if (y, m) != this:
                cur[f"{y}-{m:02d}"] = [f"{y}-{m:02d}", None, None]      # 該月無資料（例如尚未開始），記下來避免每次重抓
            continue
        d, v = rows[-1]
        partial = 1 if (y, m) == this else 0
        cur[f"{y}-{m:02d}"] = [f"{y}-{m:02d}", f"{d:%Y%m%d}", v] + ([1] if partial else [])
    return cur


def finmind_index():
    """備援：FinMind TAIEX 全部歷史 → {ym: [ym, date, close]}"""
    q = {"dataset": "TaiwanStockPrice", "data_id": "TAIEX", "start_date": "2000-01-01"}
    r = urllib.request.Request("https://api.finmindtrade.com/api/v4/data?" + urllib.parse.urlencode(q), headers={"User-Agent": UA})
    if TOKEN:
        r.add_header("Authorization", "Bearer " + TOKEN)
    st, raw = http(r.full_url, timeout=90, headers={"Authorization": "Bearer " + TOKEN} if TOKEN else None)
    DIAG["idx"]["tries"].append({"q": "finmind TAIEX", "status": st, "len": len(raw)})
    try:
        rows = json.loads(raw.decode("utf-8")).get("data") or []
    except Exception:
        return {}
    out = {}
    for x in sorted(rows, key=lambda x: x.get("date", "")):
        d, v = roc_date(x.get("date")), num(x.get("close"))
        if d and v:
            out[f"{d:%Y-%m}"] = [f"{d:%Y-%m}", f"{d:%Y%m%d}", v] + ([1] if (d.year, d.month) == (TODAY.year, TODAY.month) else [])
    return out


# ---------------------------------------------------------------- 2. GDP（主計總處開放資料 XML）
GDP_URLS = {
    # 2026/10/20 實測：www.dgbas.gov.tw 被 Cloudflare 擋（403 Just a moment），ws.dgbas.gov.tw 可以
    "q": ["https://ws.dgbas.gov.tw/public/data/open/Stat/NA/NA8101A1Q.xml",
          "https://www.dgbas.gov.tw/public/data/open/Stat/NA/NA8101A1Q.xml"],
    "y": ["https://ws.dgbas.gov.tw/public/data/open/Stat/NA/NA8101A1A.xml",
          "https://www.dgbas.gov.tw/public/data/open/Stat/NA/NA8101A1A.xml"],
}
EXCL_NOMINAL = ("連鎖", "實質", "成長", "平均每人", "每人", "美元", "指數", "變動", "平減", "率", "chain", "real", "growth", "capita", "USD", "deflator")
QPAT = [re.compile(r"(\d{4})\s*[-/.年]?\s*(?:第|Q|q)\s*([1-4])\s*季?"),
        re.compile(r"(?:民國)?\s*(\d{2,3})\s*年\s*第?\s*([1-4])\s*季"),
        re.compile(r"^\s*(\d{4})\s*[-/.]?\s*([1-4])\s*$"),
        re.compile(r"^\s*(\d{2,3})\s*Q\s*([1-4])\s*$", re.I)]
YPAT = [re.compile(r"(\d{4})\s*年?"), re.compile(r"(?:民國)?\s*(\d{2,3})\s*年")]


def period_of(s, freq):
    s = str(s or "").strip()
    if not s:
        return None
    if freq == "q":
        for p in QPAT:
            m = p.search(s)
            if m:
                y, q = int(m.group(1)), int(m.group(2))
                if y < 1000:
                    y += 1911
                if 1950 <= y <= 2100:
                    return f"{y}Q{q}"
        return None
    for p in YPAT:
        m = p.fullmatch(s) or p.match(s)
        if m and m.end() >= len(s) - 2:
            y = int(m.group(1))
            if y < 1000:
                y += 1911
            if 1950 <= y <= 2100:
                return str(y)
    return None


def xml_records(raw):
    """任何結構的 XML → 每個「子元素都是葉節點」的元素變成一筆 dict（含屬性）"""
    root = ET.fromstring(raw)
    recs, tags = [], set()
    for el in root.iter():
        kids = list(el)
        if len(kids) >= 2 and all(len(list(k)) == 0 for k in kids):
            d = {f"@{a}": v for a, v in el.attrib.items()}
            for k in kids:
                tag = k.tag.split("}")[-1]
                tags.add(tag)
                d[tag] = (k.text or "").strip()
                for a, v in k.attrib.items():
                    d[f"{tag}@{a}"] = v
            recs.append(d)
    return recs, sorted(tags)


def is_nominal(name):
    n = str(name)
    return (("國內生產毛額" in n or "GDP" in n.upper()) and not any(x in n for x in EXCL_NOMINAL)) or \
           (("國內生產毛額" in n or "GDP" in n.upper()) and ("當期" in n or "名目" in n or "current" in n.lower()))


def is_growth(name):
    n = str(name)
    return "經濟成長率" in n or ("成長" in n and "GDP" in n.upper() and "名目" not in n) or ("growth" in n.lower() and "real" in n.lower())


def interpret(recs, freq):
    """wide（每期一筆、欄位＝指標）或 long（每期×指標一筆）→ {period: {"gdp": 百萬元, "g": %, "flag": 'p'/'f'}}"""
    out = {}
    for d in recs:
        # 期間：先找欄位名像「期間／時間／年季」的，再掃所有值
        per, flag = None, ""
        for k, v in d.items():
            if any(x in k for x in ("期", "時間", "年", "季", "Period", "period", "TIME", "Time", "date", "Date")):
                per = period_of(v, freq)
                if per:
                    flag = "f" if re.search(r"\(f\)|預測|f$", str(v)) else "p" if re.search(r"\(p\)|初步|p$", str(v)) else ""
                    break
        if not per:
            for k, v in d.items():
                per = period_of(v, freq)
                if per:
                    break
        if not per:
            continue
        rec = out.setdefault(per, {})
        if flag:
            rec["flag"] = flag
        # wide：欄位名含指標關鍵字
        hit = False
        for k, v in d.items():
            if is_growth(k) and num(v) is not None:
                rec["g"] = num(v); hit = True
            elif is_nominal(k) and num(v) is not None:
                rec["gdp"] = num(v); hit = True
        if hit:
            continue
        # long：某個值是指標名稱、另一個值是數字
        name = next((v for v in d.values() if is_growth(v) or is_nominal(v)), None)
        if name is None:
            continue
        vals = [num(v) for k, v in d.items() if not period_of(v, freq) and num(v) is not None and v != name]
        if not vals:
            continue
        if is_growth(name):
            rec["g"] = vals[0]
        elif is_nominal(name):
            rec["gdp"] = vals[0]
    return out


SDMX = "https://nstatdb.dgbas.gov.tw/dgbasAll/webMain.aspx?sdmx/A018101010/{flt}.{f}&startTime={a}&endTime={b}"
BUA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"


def sdmx_series(js):
    """主計總處 API-JSON（SDMX-JSON 風格）→ [(名稱, {期間id: 值})]"""
    st = js.get("structure") or (js.get("data") or {}).get("structure") or {}
    dims = st.get("dimensions") or {}
    sdims, odims = dims.get("series") or [], dims.get("observation") or []
    periods = [v.get("id") or v.get("name") for v in (odims[0].get("values") if odims else [])]
    found = []

    def walk(o):
        if isinstance(o, dict):
            if o and all(re.fullmatch(r"\d+(:\d+)*", str(k)) for k in o) and any(isinstance(v, dict) and "observations" in v for v in o.values()):
                found.append(o)
                return
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(js.get("data") or js)
    out = []
    for ser in found[:1]:
        for key, v in ser.items():
            idx = [int(x) for x in str(key).split(":")]
            names = []
            for d, i in zip(sdims, idx):
                vals = d.get("values") or []
                if i < len(vals):
                    names.append(str(vals[i].get("name") or vals[i].get("id")))
            obs = {}
            for k, val in (v.get("observations") or {}).items():
                k = int(k)
                x = val[0] if isinstance(val, list) and val else val
                if k < len(periods) and num(x) is not None:
                    obs[periods[k]] = num(x)
            out.append(("／".join(names), obs))
    return out


def fetch_sdmx(freq):
    f = "Q" if freq == "q" else "A"
    a, b = ("1998-Q1", f"{TODAY.year + 1}-Q4") if freq == "q" else ("1998", str(TODAY.year + 1))
    meta = None
    for mu in ("https://nstatdb.dgbas.gov.tw/dgbasAll/webMain.aspx?sdmx/A018101010/",
               "https://nstatdb.dgbas.gov.tw/dgbasall/webMain.aspx?sdmx/A018101010/"):
        st, raw = http(mu, timeout=90, headers={"User-Agent": BUA, "Accept": "application/json,*/*"})
        tr = {"url": mu, "status": st, "len": len(raw), "head": raw[:200].decode("utf-8", "replace")}
        DIAG["gdp"]["tries"].append(tr)
        try:
            meta = json.loads(raw.decode("utf-8-sig"))
            sd = ((meta.get("structure") or {}).get("dimensions") or {}).get("series") or []
            tr["dims"] = [[v.get("id") for v in d.get("values") or []][:60] for d in sd]
            tr["names"] = [[v.get("name") for v in d.get("values") or []][:60] for d in sd]
            if sd:
                break
        except Exception:
            meta = None
    flts = []
    if meta:
        sd = ((meta.get("structure") or {}).get("dimensions") or {}).get("series") or []
        flts.append(".".join("+".join(str(v.get("id")) for v in d.get("values") or []) for d in sd))
    flts += ["1+2+3+4+5+6+7+8+9+10.1", "1+2+3+4+5+6+7+8+9+10"]
    for flt in flts:
        url = SDMX.format(flt=flt, f=f, a=a, b=b)
        t0 = time.time()
        st, raw = http(url, timeout=90, headers={"User-Agent": BUA, "Accept": "application/json,*/*"})
        tr = {"url": url, "status": st, "len": len(raw), "sec": round(time.time() - t0, 1)}
        DIAG["gdp"]["tries"].append(tr)
        if st != 200 or not raw:
            tr["head"] = raw[:300].decode("utf-8", "replace")
            continue
        try:
            js = json.loads(raw.decode("utf-8-sig"))
        except Exception:
            tr["head"] = raw[:500].decode("utf-8", "replace")
            continue
        ss = sdmx_series(js)
        tr["series"] = [n for n, _ in ss][:40]
        if not ss:
            tr["head"] = raw[:1500].decode("utf-8", "replace")
            continue
        data = {}
        for name, obs in ss:
            kind = "g" if is_growth(name) else "gdp" if is_nominal(name) else None
            if not kind:
                continue
            for pid, val in obs.items():
                per = period_of(pid, freq)
                if per and kind not in data.setdefault(per, {}):
                    data[per][kind] = val
        tr["parsed"] = len(data)
        if any("gdp" in v for v in data.values()):
            return data
    return {}


def fetch_gdp(freq):
    """回傳 {period: {...}}；全部失敗回 {}。開放資料 XML（Obs: Item／TIME_PERIOD／TYPE 原始值|年增率／Item_VALUE）"""
    for url in GDP_URLS[freq]:
        t0 = time.time()
        st, raw = http(url, timeout=90, headers={"User-Agent": BUA})
        tr = {"url": url, "status": st, "len": len(raw), "sec": round(time.time() - t0, 1)}
        DIAG["gdp"]["tries"].append(tr)
        if st != 200 or not raw:
            tr["head"] = raw[:300].decode("utf-8", "replace")
            continue
        try:
            recs, tags = xml_records(raw)
        except Exception as e:
            tr["parse"] = f"XML 解析失敗 {e!r}"
            tr["head"] = raw[:600].decode("utf-8", "replace")
            continue
        tr["records"] = len(recs)
        tr["tags"] = tags[:40]
        if "Item" in tags and "TIME_PERIOD" in tags:
            data = {}
            items = set()
            for d in recs:
                it, per = d.get("Item", ""), period_of(d.get("TIME_PERIOD"), freq)
                items.add(it)
                if not per or d.get("TYPE", "原始值") != "原始值" or num(d.get("Item_VALUE")) is None:
                    continue
                v = num(d["Item_VALUE"])
                if it == "國內生產毛額GDP(名目值，百萬元)":
                    data.setdefault(per, {})["gdp"] = v
                elif it.startswith("經濟成長"):
                    data.setdefault(per, {})["g"] = v
                fl = re.search(r"[pf]", str(d.get("TIME_PERIOD", ""))[4:] + str(d.get("@OBS_STATUS", "")))
                if fl and per in data:
                    data[per]["flag"] = fl.group(0)
            tr["items"] = sorted(items)[:30]
            tr["parsed"] = len(data)
            if any("gdp" in v for v in data.values()):
                return data
        tr["sample"] = recs[:3] + recs[-2:]
        data = interpret(recs, freq)
        tr["parsed"] = len(data)
        tr["withGDP"] = sum(1 for v in data.values() if "gdp" in v)
        if data and tr["withGDP"]:
            return data
        tr["head"] = raw[:900].decode("utf-8", "replace")
    return {}


def qnext(p):
    y, q = int(p[:4]), int(p[-1])
    return f"{y + 1}Q1" if q == 4 else f"{y}Q{q + 1}"


def norm_unit(data):
    big = [v["gdp"] for p, v in data.items() if v.get("gdp") and p >= "2015"]
    if big and max(big) < 1e6:
        for v in data.values():
            if v.get("gdp"):
                v["gdp"] *= 100
    return data


def gdp_rows(data):
    """季：[年季, 名目GDP億, 經濟成長率%, 名目年增%, 近四季名目GDP億, 註記]（升冪）"""
    ps = sorted(data)
    out = []
    for i, p in enumerate(ps):
        v = data[p]
        gdp = v.get("gdp")
        gdp_e = gdp / 100 if gdp is not None else None            # 百萬元 → 億
        prev = data.get(f"{int(p[:4]) - 1}{p[4:]}", {}).get("gdp")
        nom = (gdp / prev - 1) * 100 if gdp and prev else None
        last4 = [data[x].get("gdp") for x in ps[max(0, i - 3):i + 1]]
        s4 = sum(last4) / 100 if len(last4) == 4 and all(last4) and all(qnext(ps[j]) == ps[j + 1] for j in range(max(0, i - 3), i)) else None
        out.append([p, round(gdp_e, 1) if gdp_e is not None else None, v.get("g"), round(nom, 2) if nom is not None else None,
                    round(s4, 1) if s4 is not None else None, v.get("flag", "")])
    return out


def gdpy_rows(data):
    out = []
    for p in sorted(data):
        v = data[p]
        out.append([p, round(v["gdp"] / 100, 1) if v.get("gdp") is not None else None, v.get("g"), v.get("flag", "")])
    return out


# ---------------------------------------------------------------- main
def main():
    old = load(OUT / "macro.json", {})
    res = {"updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}

    # 1. 指數
    try:
        cur = update_index(old.get("idx", []))
        if not any(r[2] for r in cur.values()):
            DIAG["idx"]["notes"].append("證交所一筆都沒拿到，改用 FinMind")
            cur = finmind_index() or cur
        res["idx"] = [r for _, r in sorted(cur.items())]
    except Exception as e:
        DIAG["idx"]["notes"].append(f"指數失敗：{e!r}")
        res["idx"] = old.get("idx", [])
    res["idxFields"] = ["ym", "date", "close", "partial"]

    # 2. GDP
    try:
        q = fetch_gdp("q")
        res["gdp"] = gdp_rows(norm_unit(q)) if q else old.get("gdp", [])
        if not q:
            DIAG["gdp"]["notes"].append("季 GDP 抓不到或解析失敗，沿用上一版")
    except Exception as e:
        DIAG["gdp"]["notes"].append(f"季 GDP 失敗：{e!r}")
        res["gdp"] = old.get("gdp", [])
    res["gdpFields"] = ["yq", "名目GDP億", "經濟成長率%", "名目年增%", "近四季名目GDP億", "註記"]
    try:
        y = fetch_gdp("y")
        res["gdpY"] = gdpy_rows(norm_unit(y)) if y else old.get("gdpY", [])
    except Exception as e:
        DIAG["gdp"]["notes"].append(f"年 GDP 失敗：{e!r}")
        res["gdpY"] = old.get("gdpY", [])
    res["gdpYFields"] = ["year", "名目GDP億", "經濟成長率%", "註記"]
    DIAG["gdp"]["tries"] = DIAG["gdp"]["tries"][-12:]
    res["src"] = {"idx": "證交所 發行量加權股價指數歷史資料 MI_5MINS_HIST",
                  "gdp": "主計總處 國民所得統計-常用資料（季 data.gov.tw/dataset/6799、年 44218）"}
    DIAG["idx"]["requests"] = TW["n"]
    DIAG["idx"]["tries"] = DIAG["idx"]["tries"][-40:]
    res["diag"] = DIAG
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "macro.json").write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), "utf-8")
    g = res.get("gdp", [])
    print(f"指數 {sum(1 for r in res['idx'] if r[2])} 個月（最新 {res['idx'][-1][1] if res['idx'] else '—'}，證交所 {TW['n']} 次）；"
          f"GDP 季 {len(g)} 期（最新 {g[-1][0] if g else '—'}）、年 {len(res.get('gdpY', []))} 期；"
          f"備註 {DIAG['idx']['notes'] + DIAG['gdp']['notes']}")


if __name__ == "__main__":
    main()
