"""注意／處置股 → data/notice.json（notice.html 用）

來源（免費開放資料，GitHub Actions 連得到；雲端對話環境連不到）：
  上市（證交所）
    官網 rwd JSON（優先，有當天資料、可帶 date 回補）
      https://www.twse.com.tw/rwd/zh/announcement/notice?date=YYYYMMDD&response=json       公布注意有價證券
      https://www.twse.com.tw/rwd/zh/announcement/punish?startDate=&endDate=&response=json   公布處置有價證券
      https://www.twse.com.tw/rwd/zh/announcement/notetrans?response=json                    注意累計次數可能達處置標準
    OpenAPI（備援；2026/10/29 實測 announcement/notice 回空列）
      https://openapi.twse.com.tw/v1/announcement/notice | punish | notetrans
  上櫃（櫃買中心 OpenAPI，實測會回最近兩天）
    https://www.tpex.org.tw/openapi/v1/tpex_trading_warning_information   Date,SecuritiesCompanyCode,CompanyName,TradingInformation,ClosePrice,PriceEarningRatio
    https://www.tpex.org.tw/openapi/v1/tpex_disposal_information          Date,SecuritiesCompanyCode,CompanyName,DispositionPeriod,DispositionReasons,DisposalCondition
    上櫃「注意累計次數」端點未確認 → 試候選名稱，抓不到就用歷史次數推算（近 10 日 ≥5 次或近 30 日 ≥11 次）

欄位用關鍵字比對（中英文都認），官方改名不會整支掛掉；每個來源原始回應存 data/notice/raw_*.json。
歷史：data/notice/hist.json {YYYYMMDD: {att:[代號…], dis:[代號…]}} 保留 150 天 → 連續天數、近 10／30 日次數。
環境變數：BACKFILL=天數（手動跑時回補證交所注意名單歷史，預設抓近 14 天；第一次建議 45）
權證／可轉債等 6 碼代號一律略過，只留股票、ETF。
"""
import json, os, re, time, datetime as dt, urllib.request
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
BACKFILL = int(os.environ.get("BACKFILL") or 0)
DIAG = {"src": {}, "fail": []}

RWD = "https://www.twse.com.tw/rwd/zh/announcement/"
TWSE = "https://openapi.twse.com.tw/v1/"
TPEX = "https://www.tpex.org.tw/openapi/v1/"
TPEX_PRE_CANDIDATES = ["tpex_trading_warning_accumulated_information", "tpex_accumulated_trading_warning_information", "tpex_warning_accumulation_abnormal"]


def get(url, tries=3):
    err = ""
    for i in range(tries):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, text/plain, */*", "Referer": "https://www.twse.com.tw/zh/announcement/notice.html"})
            with urllib.request.urlopen(r, timeout=60) as resp:
                raw = resp.read()
            try:
                j = json.loads(raw.decode("utf-8-sig"))
            except Exception:
                j = json.loads(raw.decode("big5", "replace"))
            if isinstance(j, dict):                       # 證交所 rwd 格式：{stat, fields, data:[[...]]}
                if not j.get("data"):
                    DIAG.setdefault("probe", {})[url[:100]] = raw.decode("utf-8", "replace")[:300]
                if j.get("fields") and isinstance(j.get("data"), list):
                    return [dict(zip(j["fields"], row)) for row in j["data"]]
                if j.get("tables"):
                    out = []
                    for t in j["tables"]:
                        if t.get("fields") and t.get("data"):
                            out += [dict(zip(t["fields"], row)) for row in t["data"]]
                    return out
                j = j.get("data") or j.get("result") or []
            return j if isinstance(j, list) else []
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
            time.sleep(3 * (i + 1))
    DIAG["fail"].append(f"{url[:90]} → {err}")
    return None


def load(p, default):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default


# ---------------------------------------------------------------- 欄位關鍵字比對（中英）
def pick(row, *pats):
    norm = {re.sub(r"[\s_\-]", "", str(k)).lower(): v for k, v in row.items()}
    for p in pats:
        rx = re.compile(p, re.I)
        for k, v in norm.items():
            if rx.search(k) and str(v).strip() not in ("", "-", "--", "null", "None", "N/A"):
                return str(v).strip()
    return ""


def num(s):
    s = re.sub(r"[,\s]", "", s or "")
    try:
        return float(s)
    except Exception:
        return None


def ymd(s):
    """1151028 / 115/10/28 / 115年10月28日 / 2026-10-28 / 20261028 → 20261028"""
    s = (s or "").strip()
    if re.fullmatch(r"\d{7}", s):
        return f"{int(s[:3]) + 1911}{s[3:]}"
    if re.fullmatch(r"\d{8}", s):
        return s
    m = re.search(r"(\d{2,4})\s*[/年.\-]\s*(\d{1,2})\s*[/月.\-]\s*(\d{1,2})", s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 1000:
            y += 1911
        return f"{y}{mo:02d}{d:02d}"
    return ""


def last_date(s):
    """處置期間 '115/10/29~115/11/06' → 迄日 20261106"""
    ds = [ymd(x) for x in re.findall(r"\d{2,4}[/年.\-]\d{1,2}[/月.\-]\d{1,2}|\d{7,8}", s or "")]
    ds = [d for d in ds if d]
    return max(ds) if ds else ""


def code_of(row):
    c = pick(row, r"^code$", r"securitiescompanycode", r"證券代號|股票代號|代號", r"stockcode|securitycode|^stockno|code")
    c = re.sub(r"\s", "", c)
    if not re.fullmatch(r"\d{4,6}[A-Z]?", c):
        return ""
    if len(re.sub(r"\D", "", c)) == 6 and not c.startswith("00"):   # 權證／可轉債／TDR
        return ""
    return c


LIST = {r[0]: (r[1], r[2]) for r in load(DATA / "list.json", []) if len(r) >= 3}
market_of = lambda c, dflt: LIST.get(c, ("", dflt))[1] or dflt
name_of = lambda c, given: re.sub(r"股份有限公司$", "", given) or LIST.get(c, ("", ""))[0] or c
NAME_PATS = (r"^name$", r"companyname|stockname", r"證券名稱|股票名稱|名稱", r"name")
DATE_PATS = (r"^date$", r"公布日期|資料日期|^日期", r"announce.*date|date")


def fetch_rows(key, url):
    rows = get(url)
    if rows is None:
        return []
    (NDIR / f"raw_{key}.json").write_text(json.dumps(rows[:300], ensure_ascii=False, indent=0))
    DIAG["src"][key] = len(rows)
    return rows


def parse_att(rows, mkt):
    out = []
    for r in rows:
        c = code_of(r)
        if not c:
            continue
        out.append({"c": c, "n": name_of(c, pick(r, *NAME_PATS)), "m": market_of(c, mkt),
                    "r": pick(r, r"tradinginfo", r"注意交易資訊|注意", r"attention", r"information", r"reason"),
                    "px": num(pick(r, r"clos", r"收盤")), "pe": num(pick(r, r"^pe$", r"priceearning|peratio", r"本益比", r"^pe")),
                    "cnt": num(pick(r, r"numberofannouncement", r"累計|次數", r"count|times")),
                    "d": ymd(pick(r, *DATE_PATS))})
    return out


def parse_dis(rows, mkt):
    out = []
    for r in rows:
        c = code_of(r)
        if not c:
            continue
        period = pick(r, r"period", r"處置期間|期間")
        out.append({"c": c, "n": name_of(c, pick(r, *NAME_PATS)), "m": market_of(c, mkt),
                    "r": pick(r, r"reason", r"處置原因|原因"), "period": period, "end": last_date(period),
                    "measure": pick(r, r"measure", r"處置措施|措施", r"condition", r"content|內容"),
                    "d": ymd(pick(r, *DATE_PATS))})
    return out


def parse_pre(rows, mkt):
    out = []
    for r in rows:
        c = code_of(r)
        if not c:
            continue
        out.append({"c": c, "n": name_of(c, pick(r, *NAME_PATS)), "m": market_of(c, mkt),
                    "r": pick(r, r"criteria", r"recently", r"標準|情形|累計", r"information", r"reason"),
                    "d": ymd(pick(r, *DATE_PATS))})
    return out


# ---------------------------------------------------------------- 抓
att, dis, pre = [], [], []

# 上市：官網 rwd 優先 → OpenAPI 備援
# 實測：證交所 rwd notice 只認 startDate／endDate（date 參數會被忽略），一次可拉一段期間，每列有「日期」
d_att = (NOW - dt.timedelta(days=BACKFILL or 14)).strftime("%Y%m%d")
rows = fetch_rows("twse_att", RWD + f"notice?startDate={d_att}&endDate={TODAY}&response=json")
if not any(code_of(r) for r in rows):
    rows = fetch_rows("twse_att_openapi", TWSE + "announcement/notice")
att += parse_att(rows, "上市")
d0 = (NOW - dt.timedelta(days=20)).strftime("%Y%m%d")
rows = fetch_rows("twse_dis", RWD + f"punish?startDate={d0}&endDate={TODAY}&response=json")
if not any(code_of(r) for r in rows):
    rows = fetch_rows("twse_dis_openapi", TWSE + "announcement/punish")
dis += parse_dis(rows, "上市")
rows = fetch_rows("twse_pre", RWD + "notetrans?response=json")
if not any(code_of(r) for r in rows):
    rows = fetch_rows("twse_pre_openapi", TWSE + "announcement/notetrans")
pre += parse_pre(rows, "上市")

# 上櫃
att += parse_att(fetch_rows("tpex_att", TPEX + "tpex_trading_warning_information"), "上櫃")
dis += parse_dis(fetch_rows("tpex_dis", TPEX + "tpex_disposal_information"), "上櫃")
tpex_pre_src = ""
for cand in TPEX_PRE_CANDIDATES:
    rows = get(TPEX + cand, tries=1)
    if rows:
        tpex_pre_src = cand
        (NDIR / "raw_tpex_pre.json").write_text(json.dumps(rows[:300], ensure_ascii=False, indent=0))
        pre += parse_pre(rows, "上櫃")
        break
DIAG["tpex_pre"] = tpex_pre_src or "沒找到端點，上櫃快達處置用歷史次數推算"
DIAG["fail"] = [f for f in DIAG["fail"] if not any(c in f for c in TPEX_PRE_CANDIDATES)]

if not (att or dis or pre):
    print("全部抓不到，保留舊檔：", DIAG["fail"]); raise SystemExit(0)

# ---------------------------------------------------------------- 資料日期：注意名單最新公告日（週末／假日不覆蓋）
dates = [v["d"] for v in att if v.get("d")]
ASOF = max(dates) if dates else TODAY

# ---------------------------------------------------------------- 歷史：來源回傳的每一天都記（櫃買會回兩天）；手動回補證交所
hist = {k: v for k, v in load(HIST, {}).items() if re.fullmatch(r"20\d{6}", k)}
by_day = {}
for v in att:
    by_day.setdefault(v["d"] or ASOF, set()).add(v["c"])
for d, s in by_day.items():
    old = set(hist.get(d, {}).get("att", []))
    hist.setdefault(d, {"att": [], "dis": []})["att"] = sorted(old | s)
hist[ASOF] = hist.get(ASOF, {"att": [], "dis": []})
hist[ASOF]["dis"] = sorted({v["c"] for v in dis})
hist = {k: hist[k] for k in sorted(hist)[-150:] if k}
HIST.write_text(json.dumps(hist, ensure_ascii=False, separators=(",", ":")))
days = [d for d in sorted(hist) if d <= ASOF and hist[d]["att"]]   # 有名單的交易日
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
    return n10, n30, streak


# ---------------------------------------------------------------- 整理輸出
att = {v["c"]: v for v in att if (v["d"] or ASOF) == ASOF}                        # 只留最新一天
dis = {v["c"]: v for v in dis if not v["end"] or v["end"] > ASOF}                 # 處置期未結束（迄日＝名單日的已結束）
pre = {v["c"]: v for v in pre}
for v in att.values():
    v["n10"], v["n30"], v["streak"] = stats(v["c"])
    v["warn"] = v["n10"] >= 5 or v["n30"] >= 11 or v["c"] in pre
for v in att.values():
    if v["warn"] and v["c"] not in pre:
        pre[v["c"]] = {"c": v["c"], "n": v["n"], "m": v["m"], "r": f"依本站紀錄：近 10 日 {v['n10']} 次、近 30 日 {v['n30']} 次列注意（估算，非官方名單）", "d": ASOF, "est": True}
for v in pre.values():
    v["n10"], v["n30"], _ = stats(v["c"])
for v in dis.values():
    v["n30"] = stats(v["c"])[1]
    v["endMd"] = f"{int(v['end'][4:6])}/{int(v['end'][6:])}" if v["end"] else ""

out = {"updated": NOW.strftime("%Y-%m-%dT%H:%MZ"), "asof": ASOF, "histDays": len(days),
       "att": sorted(att.values(), key=lambda x: (-x["streak"], -x["n10"], x["c"])),
       "dis": sorted(dis.values(), key=lambda x: (x["end"] or "9", x["c"])),
       "pre": sorted(pre.values(), key=lambda x: (-x["n10"], x["c"])),
       "diag": DIAG}
OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
print(f"asof {ASOF}: 注意 {len(att)}（上市 {sum(v['m']=='上市' for v in att.values())}）、處置 {len(dis)}、快達 {len(pre)}；hist {len(days)} 天；src {DIAG['src']}；fail {DIAG['fail']}")
