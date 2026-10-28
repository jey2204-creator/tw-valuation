"""注意／處置股 → data/notice.json（notice.html 用）

來源（免費開放資料，GitHub Actions 連得到；雲端對話環境連不到）：
  上市（證交所 OpenAPI https://openapi.twse.com.tw/v1/）
    announcement/notice      當日公布注意有價證券      Code,Name,NumberOfAnnouncement,TradingInfoForAttention,Date,ClosingPrice,PE
    announcement/punish      公布處置有價證券          Code,Name,DispositionMeasures,ReasonsOfDisposition,…
    announcement/notetrans   注意累計次數可能達處置標準  Code,Name,RecentlyMetAttentionSecuritiesCriteria
  上櫃（櫃買中心 OpenAPI https://www.tpex.org.tw/openapi/v1/）
    tpex_trading_warning_information   上櫃公布注意股票   SecuritiesCompanyCode,CompanyName,TradingInformation,ClosePrice,PE
    tpex_disposal_information          上櫃公布處置股票   SecuritiesCompanyCode,CompanyName,DispositionPeriod,DispositionReasons,…
    上櫃「注意累計次數異常」端點名稱未確認 → 先試幾個候選名稱，抓不到就用自己的歷史紀錄算（近 10 日 ≥5 次或近 30 日 ≥11 次）

欄位名稱用「關鍵字比對」取，官方改名時不會整支掛掉；每個端點原始回應存 data/notice/raw_*.json 方便查。
歷史：data/notice/hist.json {YYYYMMDD: {att:[代號…], dis:[代號…]}}，保留 150 天，用來算「連續天數」「近 10／30 日次數」。
"""
import json, re, datetime as dt, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
NDIR = DATA / "notice"
NDIR.mkdir(parents=True, exist_ok=True)
OUT = DATA / "notice.json"
HIST = NDIR / "hist.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
TZ = dt.timezone(dt.timedelta(hours=8))
NOW = dt.datetime.now(TZ)
TODAY = NOW.strftime("%Y%m%d")
DIAG = {"ok": [], "fail": [], "rows": {}}

TWSE = "https://openapi.twse.com.tw/v1/"
TPEX = "https://www.tpex.org.tw/openapi/v1/"
SRC = {
    "twse_att": TWSE + "announcement/notice",
    "twse_dis": TWSE + "announcement/punish",
    "twse_pre": TWSE + "announcement/notetrans",
    "tpex_att": TPEX + "tpex_trading_warning_information",
    "tpex_dis": TPEX + "tpex_disposal_information",
}
TPEX_PRE_CANDIDATES = [
    "tpex_trading_warning_accumulated_information",
    "tpex_accumulated_trading_warning_information",
    "tpex_trading_warning_count_abnormal",
    "tpex_warning_accumulation_abnormal",
]


def get(url):
    for i in range(3):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json", "If-Modified-Since": "Mon, 26 Jul 1997 05:00:00 GMT"})
            with urllib.request.urlopen(r, timeout=60) as resp:
                raw = resp.read()
            try:
                j = json.loads(raw.decode("utf-8-sig"))
            except Exception:
                j = json.loads(raw.decode("big5", "replace"))
            if isinstance(j, dict):
                j = j.get("data") or j.get("result") or j.get("tables") or []
            return j if isinstance(j, list) else []
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
            import time; time.sleep(3 * (i + 1))
    DIAG["fail"].append(f"{url} → {err}")
    return None


def load(p, default):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default


# ---------------------------------------------------------------- 欄位關鍵字比對
def pick(row, *pats):
    """依序用 regex 找第一個符合的欄位（忽略大小寫、底線、空白）"""
    norm = {re.sub(r"[\s_\-]", "", k).lower(): v for k, v in row.items()}
    for p in pats:
        rx = re.compile(p, re.I)
        for k, v in norm.items():
            if rx.search(k) and str(v).strip() not in ("", "-", "--", "null", "None"):
                return str(v).strip()
    return ""


def num(s):
    s = re.sub(r"[,\s]", "", s or "")
    try:
        return float(s)
    except Exception:
        return None


def ymd(s):
    """民國 1151028 / 115/10/28 / 2026-10-28 / 20261028 → 20261028"""
    s = re.sub(r"\D", "", s or "")
    if len(s) == 7:
        return f"{int(s[:3]) + 1911}{s[3:]}"
    if len(s) == 8:
        return s
    if len(s) == 6 and int(s[:2]) < 50:  # 1151028 少一位？不處理
        return ""
    return ""


def code_of(row):
    c = pick(row, r"^code$", r"securitiescompanycode", r"stockcode|securitycode|^stockno|^code")
    c = re.sub(r"\s", "", c)
    return c if re.fullmatch(r"\d{4,6}[A-Z]?", c) else ""


# ---------------------------------------------------------------- 抓
LIST = {r[0]: (r[1], r[2]) for r in load(DATA / "list.json", []) if len(r) >= 3}


def market_of(c, default):
    return LIST.get(c, ("", default))[1] or default


def name_of(c, given):
    return given or LIST.get(c, ("", ""))[0] or c


def fetch_rows(key, url):
    rows = get(url)
    if rows is None:
        return []
    (NDIR / f"raw_{key}.json").write_text(json.dumps(rows[:400], ensure_ascii=False, indent=0))
    DIAG["ok"].append(key); DIAG["rows"][key] = len(rows)
    return rows


def parse_att(rows, mkt):
    out = {}
    for r in rows:
        c = code_of(r)
        if not c:
            continue
        out[c] = {
            "c": c, "n": name_of(c, pick(r, r"^name$", r"companyname|stockname|name")), "m": market_of(c, mkt),
            "r": pick(r, r"tradinginfo", r"attention", r"information", r"reason"),
            "px": num(pick(r, r"clos")), "pe": num(pick(r, r"^pe$", r"peratio", r"^pe")),
            "cnt": num(pick(r, r"numberofannouncement", r"count|times|次數")),
            "d": ymd(pick(r, r"^date$", r"announce.*date|date")),
        }
    return out


def parse_dis(rows, mkt):
    out = {}
    for r in rows:
        c = code_of(r)
        if not c:
            continue
        out[c] = {
            "c": c, "n": name_of(c, pick(r, r"^name$", r"companyname|stockname|name")), "m": market_of(c, mkt),
            "r": pick(r, r"reason"),
            "period": pick(r, r"period"),
            "measure": pick(r, r"measure", r"condition", r"content"),
            "d": ymd(pick(r, r"^date$", r"announce.*date|date")),
        }
    return out


def parse_pre(rows, mkt):
    out = {}
    for r in rows:
        c = code_of(r)
        if not c:
            continue
        out[c] = {
            "c": c, "n": name_of(c, pick(r, r"^name$", r"companyname|stockname|name")), "m": market_of(c, mkt),
            "r": pick(r, r"criteria", r"recently", r"information", r"reason", r"situation|condition"),
            "d": ymd(pick(r, r"^date$", r"date")),
        }
    return out


att = parse_att(fetch_rows("twse_att", SRC["twse_att"]), "上市")
att.update(parse_att(fetch_rows("tpex_att", SRC["tpex_att"]), "上櫃"))
dis = parse_dis(fetch_rows("twse_dis", SRC["twse_dis"]), "上市")
dis.update(parse_dis(fetch_rows("tpex_dis", SRC["tpex_dis"]), "上櫃"))
pre = parse_pre(fetch_rows("twse_pre", SRC["twse_pre"]), "上市")
tpex_pre_src = ""
for cand in TPEX_PRE_CANDIDATES:
    rows = get(TPEX + cand)
    if rows:
        tpex_pre_src = cand
        (NDIR / "raw_tpex_pre.json").write_text(json.dumps(rows[:400], ensure_ascii=False, indent=0))
        pre.update(parse_pre(rows, "上櫃"))
        break
DIAG["tpex_pre"] = tpex_pre_src or "沒找到端點，上櫃快達處置用歷史次數推算"
DIAG["fail"] = [f for f in DIAG["fail"] if not any(c in f for c in TPEX_PRE_CANDIDATES)]

# ---------------------------------------------------------------- 資料日期：以注意股公告日為準，沒有就用今天（週末／假日不覆蓋）
dates = [v["d"] for v in list(att.values()) + list(dis.values()) if v.get("d")]
ASOF = max(dates) if dates else TODAY
if not (att or dis or pre) and DIAG["fail"]:
    print("全部抓不到，保留舊檔：", DIAG["fail"]); raise SystemExit(0)

# ---------------------------------------------------------------- 歷史與次數
hist = load(HIST, {})
hist[ASOF] = {"att": sorted(att), "dis": sorted(dis)}
keys = sorted(hist)[-150:]
hist = {k: hist[k] for k in keys}
HIST.write_text(json.dumps(hist, ensure_ascii=False, separators=(",", ":")))
days = sorted(hist)                       # 有資料的交易日（週末不會寫入）
last10, last30 = days[-10:], days[-30:]


def stats(c):
    n10 = sum(c in hist[d]["att"] for d in last10)
    n30 = sum(c in hist[d]["att"] for d in last30)
    streak = 0
    for d in reversed(days):
        if c in hist[d]["att"]:
            streak += 1
        else:
            break
    first = next((d for d in days if c in hist[d]["att"]), None)
    return n10, n30, streak, first


for v in att.values():
    v["n10"], v["n30"], v["streak"], v["first"] = stats(v["c"])
    v["warn"] = v["n10"] >= 5 or v["n30"] >= 11 or v["c"] in pre   # 快達處置：近10日5次、近30日11次（公開標準），或官方名單
# 官方名單沒有的（上櫃端點不存在時）用自己的次數補進「快達處置」
for v in att.values():
    if v["warn"] and v["c"] not in pre:
        pre[v["c"]] = {"c": v["c"], "n": v["n"], "m": v["m"], "r": f"依本站紀錄：近10日 {v['n10']} 次、近30日 {v['n30']} 次列注意（估算，非官方名單）", "d": ASOF, "est": True}
for v in pre.values():
    s = att.get(v["c"])
    v["n10"], v["n30"] = (s["n10"], s["n30"]) if s else stats(v["c"])[:2]
for v in dis.values():
    v["n30"] = stats(v["c"])[1]

order = lambda x: (x["m"] != "上市", x["c"])
out = {
    "updated": NOW.strftime("%Y-%m-%dT%H:%MZ"), "asof": ASOF, "histDays": len(days),
    "att": sorted(att.values(), key=lambda x: (-x["streak"], -(x["n10"] or 0), x["c"])),
    "dis": sorted(dis.values(), key=order),
    "pre": sorted(pre.values(), key=lambda x: (-(x.get("n10") or 0), x["c"])),
    "diag": DIAG,
}
OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
print(f"asof {ASOF}: 注意 {len(att)}（上市 {sum(v['m']=='上市' for v in att.values())}）、處置 {len(dis)}、快達 {len(pre)}；hist {len(days)} 天；fail {DIAG['fail']}")
