"""台股體檢資料 → data/health.json（health.html 用）

三塊資料：
1. 估值快照（每次執行）：summary.json 收盤 × 股數＝市值 → 市值加權本益比（排除虧損／無本益比）、市值加權殖利率、
   台積電市值占比、前 10 大市值占比、隱含近四季獲利（Σ 市值 ÷ 本益比）與台積電占比 → v[] 每個交易日一筆
2. 月營收廣度：MOPS 營收彙總靜態頁 t21sc03（上市／上櫃 × 國內／KY 共 4 頁，千元）→ m[] 每月一筆：
   年增 > 0 家數、全體營收年增、扣台積電營收年增、年增中位數（只算去年同月營收 > 0 的公司）
3. 季獲利：MOPS 綜合損益表彙總 ajax_t163sb04（上市 sii／上櫃 otc，當年累計數，千元）
   → data/health/q/{YYYY}Q{n}.json 逐家原始 d[代號] = [市場0上市/1上櫃, 歸母淨利(千), 稅前淨利(千), 營收(百萬), EPS]
   → q[] 每期一筆：全體歸母淨利、台積電、扣台積電、獲利家數、成長家數（與去年同期「同一批公司」比）
節流：MOPS ajax 每次間隔 4 秒、靜態頁 1.5 秒；每次執行最多 MAXREQ 次請求（環境變數，預設 24）；
      出現「查詢過於頻繁」或連續 4 次失敗就停，下次執行接著補（新的期別優先）
重抓規則：季資料在申報截止後 40 天內每 3 天重抓一次（補晚交的公司），之後定案；
          月資料在次次月 1 日前每天重抓一次，之後定案
任何一塊失敗都不影響其他塊；每次嘗試寫進 health.json 的 diag 方便除錯
用法：python fetch_health.py          （MAXREQ=400 python fetch_health.py 一次補完歷史）
"""
import json, os, re, sys, time, html, statistics, datetime as dt
from pathlib import Path
from html.parser import HTMLParser
import urllib.request, urllib.parse

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data"
QDIR = OUT / "health" / "q"
HOSTS = ["https://mopsov.twse.com.tw", "https://mops.twse.com.tw"]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
TSMC = "2330"
START_Q = (2018, 1)          # 2019 起才有「與去年同期比」
START_M = (2019, 1)
MAXREQ = int(os.environ.get("MAXREQ") or 24)
BUDGET = float(os.environ.get("BUDGET_MIN") or 30) * 60      # 秒；超過就停止打 MOPS，先存檔提交
T0 = time.time()
TODAY = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date()
DIAG = {"tries": [], "notes": []}
REQ = {"n": 0, "fail": 0, "stop": None}
BLOCKED = set()      # 回應「FOR SECURITY REASONS」的主機，本次執行不再使用


# ---------------------------------------------------------------- 共用
def clean(s):
    return re.sub(r"\s+", " ", html.unescape(s or "")).strip()


def num(s):
    s = str(s if s is not None else "").replace(",", "").replace("%", "").strip()
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    if s in ("", "-", "--", "---", "N/A", "NA", "不適用"):
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def decode(raw, ctype=""):
    m = re.search(rb'charset=["\']?([\w-]+)', raw[:2000]) or re.search(r"charset=([\w-]+)", ctype or "")
    enc = (m.group(1).decode() if isinstance(m.group(1), bytes) else m.group(1)).lower() if m else ""
    for e in ([enc] if enc else []) + ["utf-8", "cp950", "big5hkscs"]:
        try:
            return raw.decode({"big5": "cp950"}.get(e, e))
        except Exception:
            continue
    return raw.decode("utf-8", "replace")


def req(url, data=None, referer=None, gap=4.0):
    """MOPS 請求（含節流、診斷、次數上限）。回傳 (status, text) 或 (None, '') 表示額度用完"""
    if REQ["stop"] or REQ["n"] >= MAXREQ or time.time() - T0 > BUDGET:
        REQ["stop"] = REQ["stop"] or (f"達到 MAXREQ={MAXREQ}" if REQ["n"] >= MAXREQ else f"超過時間預算 {BUDGET/60:.0f} 分")
        return None, ""
    if REQ["n"]:
        time.sleep(gap)
    REQ["n"] += 1
    hdr = {"User-Agent": UA, "Accept": "text/html,*/*;q=0.8", "Accept-Language": "zh-TW,zh;q=0.9", "Referer": referer or url}
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        hdr["Content-Type"] = "application/x-www-form-urlencoded"
    r = urllib.request.Request(url, data=body, headers=hdr, method="POST" if body is not None else "GET")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=180) as resp:
            txt, st = decode(resp.read(), resp.headers.get("Content-Type", "")), resp.status
    except urllib.error.HTTPError as e:
        txt, st = decode(e.read()), e.code
    except Exception as e:
        txt, st = "", f"ERR {e}"
    DIAG["tries"].append({"url": url, "post": {k: v for k, v in (data or {}).items() if k in ("TYPEK", "year", "season")},
                          "status": st, "len": len(txt), "sec": round(time.time() - t0, 1),
                          "snippet": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", txt))[:240]})
    if "查詢過於頻繁" in txt:
        REQ["stop"] = "MOPS 回應查詢過於頻繁"
    elif "FOR SECURITY REASONS" in txt.upper():
        BLOCKED.add(url.split("/")[2])
        DIAG["tries"][-1]["blocked"] = True
    return st, txt


def raw_sample(txt):
    """解析失敗時存一段原始 HTML（第一個含「公司」的表格附近）到 diag，方便改解析器"""
    i = txt.find("<table")
    j = txt.find("公司", i if i >= 0 else 0)
    k = txt.rfind("<tr", 0, j) if j > 0 else i
    DIAG["tries"][-1]["raw"] = txt[max(k, 0):max(k, 0) + 2500]


class Tables(HTMLParser):
    """所有 <table> → [[cell 文字, …], …]；支援巢狀表格"""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.stack, self.row, self.cell = [], [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            t = []
            self.tables.append(t)
            self.stack.append(t)
        elif tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            if self.row is not None:
                self.row.append(clean("".join(self.cell)))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.stack and self.row:
                self.stack[-1].append(self.row)
            self.row = None
        elif tag == "table" and self.stack:
            self.stack.pop()

    def handle_data(self, d):
        if self.cell is not None:
            self.cell.append(d)


def tables_of(txt):
    p = Tables()
    p.feed(txt)
    return p.tables


CODE = re.compile(r"[1-9]\d{3}[A-Z]?|\d{6}")


def load(path, default):
    try:
        return json.loads(Path(path).read_text("utf-8"))
    except Exception:
        return default


# ---------------------------------------------------------------- 1. 估值快照
def valuation():
    s = load(OUT / "summary.json", None)
    if not s or "sh" not in s:
        DIAG["notes"].append("summary.json 沒有 sh（股數），跳過估值快照")
        return None
    d, sh = s["d"], s["sh"]
    cap = {c: v[0] * sh[c] for c, v in d.items() if v[0] and sh.get(c)}
    tot = sum(cap.values())
    if not tot or TSMC not in cap:
        return None
    pe_c = [c for c in cap if d[c][2] and d[c][2] > 0]
    earn = sum(cap[c] / d[c][2] for c in pe_c)                 # 隱含近四季獲利（元）
    pe = sum(cap[c] for c in pe_c) / earn if earn else None
    yld = sum(cap[c] * (d[c][4] or 0) for c in cap) / tot
    top10 = sum(sorted(cap.values(), reverse=True)[:10]) / tot
    ts_e = cap[TSMC] / d[TSMC][2] if d[TSMC][2] else 0
    date = s.get("pxAsof") or s.get("updated", "")[:10].replace("-", "")
    return [date, round(tot / 1e12, 2), round(pe, 2) if pe else None, round(yld, 2), round(cap[TSMC] / tot * 100, 1),
            round(earn / 1e12, 3), round(ts_e / earn * 100, 1) if earn else None, round(top10 * 100, 1), len(pe_c), len(cap)]


V_FIELDS = ["date", "cap兆", "pe", "yld%", "tsmcCap%", "earn兆", "tsmcEarn%", "top10%", "nPE", "n"]


# ---------------------------------------------------------------- 2. 月營收廣度
def month_due(y, m, today=TODAY):
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    return today >= dt.date(ny, nm, 11)


def month_final(y, m, fetched):
    """次次月 1 日之後抓到的就定案"""
    y2, m2 = (y, m + 2) if m <= 10 else (y + 1, m - 10)
    return fetched and dt.date.fromisoformat(fetched) >= dt.date(y2, m2, 1)


def parse_t21(txt):
    """t21sc03：資料列 = [代號, 名稱, 當月, 上月, 去年當月, 上月比%, 去年同月%, 當月累計, 去年累計, 前期比%, 備註]"""
    out = {}
    for t in tables_of(txt):
        for r in t:
            if len(r) >= 10 and CODE.fullmatch(r[0]) and len(r) <= 12:
                cur, ly = num(r[2]), num(r[4])
                if cur is not None:
                    out[r[0]] = (cur, ly)
    return out


def fetch_month(y, m):
    roc = y - 1911
    rows, src = {}, []
    for mk in ("sii", "otc"):
        for kind in ("0", "1"):
            got = None
            for h in HOSTS:
                if h.split("/")[2] in BLOCKED:
                    continue
                st, txt = req(f"{h}/nas/t21/{mk}/t21sc03_{roc}_{m}_{kind}.html", gap=1.5)
                if st is None:
                    return None, src
                p = parse_t21(txt) if st == 200 else {}
                DIAG["tries"][-1]["rows"] = len(p)
                if not p and st == 200 and len(txt) > 3000:
                    raw_sample(txt)
                if p:
                    got = p
                    src.append(f"{mk}{kind}@{h.split('//')[1].split('.')[0]}:{len(p)}")
                    break
            if got is None and kind == "1" and not REQ["stop"]:
                got = {}                       # 國外（KY）頁不存在或沒有資料：國內頁有抓到就算完成
                src.append(f"{mk}{kind}:無")
            if got is None:
                REQ["fail"] += 1
                return None, src
            rows.update(got)
    return rows, src


def month_agg(y, m, rows):
    pairs = [(c, cur, ly) for c, (cur, ly) in rows.items() if ly is not None and ly > 0]
    up = sum(1 for _, cur, ly in pairs if cur > ly)
    cs, ps = sum(p[1] for p in pairs), sum(p[2] for p in pairs)
    ex = [p for p in pairs if p[0] != TSMC]
    ce, pe_ = sum(p[1] for p in ex), sum(p[2] for p in ex)
    med = statistics.median((cur / ly - 1) * 100 for _, cur, ly in pairs) if pairs else None
    k = 1e5   # 千元 → 億
    return [f"{y}-{m:02d}", len(rows), len(pairs), up, round(cs / k, 1), round(ps / k, 1), round(ce / k, 1), round(pe_ / k, 1),
            round(med, 1) if med is not None else None, TODAY.isoformat()]


M_FIELDS = ["ym", "nAll", "n", "up", "cur億", "prev億", "curEx億", "prevEx億", "medYoY%", "fetched"]


def update_months(old):
    have = {r[0]: r for r in old}
    todo = []
    y, m = START_M
    while True:
        if not month_due(y, m):
            break
        k = f"{y}-{m:02d}"
        r = have.get(k)
        if r is None or (not month_final(y, m, r[-1]) and r[-1] != TODAY.isoformat()):
            todo.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    todo.sort(reverse=True)                  # 新的先抓
    done = 0
    for y, m in todo:
        rows, src = fetch_month(y, m)
        if rows is None:
            if REQ["stop"]:
                break
            if REQ["fail"] >= 4:
                REQ["stop"] = "月營收連續失敗"
                break
            continue
        REQ["fail"] = 0
        have[f"{y}-{m:02d}"] = month_agg(y, m, rows)
        done += 1
    DIAG["months"] = {"todo": len(todo), "done": done}
    return [have[k] for k in sorted(have)]


# ---------------------------------------------------------------- 3. 季獲利
DEADLINE = {1: (5, 15), 2: (8, 14), 3: (11, 14)}


def q_deadline(y, n):
    return dt.date(y + 1, 3, 31) if n == 4 else dt.date(y, *DEADLINE[n])


def q_label(y, n):
    return f"{y}Q{n}"


def pick_col(hdr, *preds):
    for p in preds:
        for i, h in enumerate(hdr):
            try:
                if p(h):
                    return i
            except Exception:
                pass
    return None


def parse_t163(txt):
    """ajax_t163sb04：每種產業格式一張表（一般業、銀行、證券、保險、金控、異業），用表頭找欄位"""
    out, used = {}, []
    for t in tables_of(txt):
        hdr = None
        for r in t:
            rn = [re.sub(r"\s+", "", c) for c in r]
            if "公司代號" in rn:
                if hdr is None:
                    hdr = rn
                    ci = rn.index("公司代號")
                    ni = pick_col(hdr, lambda h: "歸屬於母公司業主" in h and h.startswith("淨利"),
                                  lambda h: "歸屬於母公司業主" in h and "綜合" not in h,
                                  lambda h: h.startswith("本期淨利") or h.startswith("本期稅後淨利"))
                    pre = pick_col(hdr, lambda h: "稅前" in h and "綜合" not in h)
                    rev = pick_col(hdr, lambda h: h in ("營業收入", "營業收入合計", "收益合計", "淨收益", "收入合計"),
                                   lambda h: h.startswith("營業收入"), lambda h: h.endswith("淨收益") and "利息" not in h)
                    eps = pick_col(hdr, lambda h: "基本每股盈餘" in h)
                    used.append({k: (hdr[i] if i is not None else None) for k, i in (("ni", ni), ("pre", pre), ("rev", rev), ("eps", eps))})
                    maxcol = max(i for i in (ci, ni, pre, rev, eps) if i is not None)
                continue
            if hdr is None or len(r) <= maxcol:
                continue
            code = r[ci]
            if not CODE.fullmatch(code) or ni is None:
                continue
            v = num(r[ni])
            if v is None:
                continue
            out[code] = [int(round(v)), int(round(num(r[pre]) or 0)) if pre is not None and num(r[pre]) is not None else None,
                         round(num(r[rev]) / 1000) if rev is not None and num(r[rev]) is not None else None,
                         num(r[eps]) if eps is not None else None]
    return out, used


def fetch_quarter(y, n):
    """回傳 {代號: [市場, 歸母淨利千, 稅前千, 營收百萬, EPS]}，或 None"""
    roc = y - 1911
    allrows, info = {}, {}
    for mi, mk in enumerate(("sii", "otc")):
        got = None
        for h in HOSTS:
            if h.split("/")[2] in BLOCKED:
                continue
            form = {"encodeURIComponent": 1, "step": 1, "firstin": 1, "off": 1, "isQuery": "Y",
                    "TYPEK": mk, "year": str(roc), "season": f"{n:02d}"}
            st, txt = req(f"{h}/mops/web/ajax_t163sb04", data=form, referer=f"{h}/mops/web/t163sb04", gap=4.0)
            if st is None:
                return None, info
            rows, used = parse_t163(txt) if st == 200 else ({}, [])
            DIAG["tries"][-1]["rows"] = len(rows)
            DIAG["tries"][-1]["cols"] = used[:6]
            if not rows and st == 200 and len(txt) > 3000:
                raw_sample(txt)
            if rows:
                got = rows
                info[mk] = {"host": h.split("//")[1].split(".")[0], "n": len(rows), "cols": used}
                break
        if got is None:
            REQ["fail"] += 1
            return None, info
        for c, v in got.items():
            allrows[c] = [mi] + v
    return allrows, info


def update_quarters():
    QDIR.mkdir(parents=True, exist_ok=True)
    todo = []
    y, n = START_Q
    while TODAY > q_deadline(y, n):
        f = QDIR / f"{q_label(y, n)}.json"
        j = load(f, None)
        if j is None:
            todo.append((y, n))
        else:
            fetched = dt.date.fromisoformat(j.get("fetched", "2000-01-01"))
            if TODAY <= q_deadline(y, n) + dt.timedelta(days=40) and (TODAY - fetched).days >= 3:
                todo.append((y, n))
        y, n = (y + 1, 1) if n == 4 else (y, n + 1)
    todo.sort(reverse=True)
    if todo:
        y0, n0 = todo[0]
        first = [t for t in todo if t in ((y0, n0), (y0 - 1, n0))]
        q4 = [t for t in todo if t[1] == 4 and t not in first]
        todo = first + q4 + [t for t in todo if t not in first and t not in q4]
    done = 0
    for y, n in todo:
        if time.time() - T0 > BUDGET * 0.7:          # 留三成時間給月營收
            DIAG["notes"].append("季財報用完七成時間預算，其餘下次補")
            break
        rows, info = fetch_quarter(y, n)
        if rows is None:
            if REQ["stop"]:
                break
            if REQ["fail"] >= 4:
                REQ["stop"] = "季財報連續失敗"
                break
            continue
        REQ["fail"] = 0
        j = {"p": q_label(y, n), "fetched": TODAY.isoformat(), "unit": "歸母淨利、稅前＝千元；營收＝百萬元",
             "fields": ["市場0上市1上櫃", "歸母淨利", "稅前淨利", "營收", "EPS"], "src": info, "d": dict(sorted(rows.items()))}
        (QDIR / f"{q_label(y, n)}.json").write_text(json.dumps(j, ensure_ascii=False, separators=(",", ":")), "utf-8")
        done += 1
    DIAG["quarters"] = {"todo": len(todo), "done": done}


def q_agg():
    files = sorted(QDIR.glob("*.json"))
    raw = {f.stem: load(f, {}).get("d", {}) for f in files}
    out = []
    for p in sorted(raw):
        d = raw[p]
        y, n = int(p[:4]), int(p[5])
        prev = raw.get(f"{y - 1}Q{n}")
        rec = {"p": p, "n": len(d), "nS": sum(1 for v in d.values() if v[0] == 0), "nO": sum(1 for v in d.values() if v[0] == 1)}
        k = 1e5      # 千元 → 億
        rec["ni"] = round(sum(v[1] for v in d.values()) / k, 1)
        rec["pre"] = round(sum(v[2] or 0 for v in d.values()) / k, 1)
        rec["rev"] = round(sum(v[3] or 0 for v in d.values()) / 100, 1)          # 百萬 → 億
        rec["ts"] = round(d[TSMC][1] / k, 1) if TSMC in d else None
        rec["prof"] = sum(1 for v in d.values() if v[1] > 0)
        rec["profS"] = sum(1 for v in d.values() if v[1] > 0 and v[0] == 0)
        rec["profO"] = sum(1 for v in d.values() if v[1] > 0 and v[0] == 1)
        if prev:
            both = [c for c in d if c in prev]
            rec["cmp"] = len(both)
            rec["grow"] = sum(1 for c in both if d[c][1] > prev[c][1])
            rec["growS"] = sum(1 for c in both if d[c][1] > prev[c][1] and d[c][0] == 0)
            rec["cmpS"] = sum(1 for c in both if d[c][0] == 0)
            rec["growO"] = sum(1 for c in both if d[c][1] > prev[c][1] and d[c][0] == 1)
            rec["cmpO"] = sum(1 for c in both if d[c][0] == 1)
            rec["growPre"] = sum(1 for c in both if d[c][2] is not None and prev[c][2] is not None and d[c][2] > prev[c][2])
            rec["niC"] = round(sum(d[c][1] for c in both) / k, 1)
            rec["niP"] = round(sum(prev[c][1] for c in both) / k, 1)
            rec["exC"] = round(sum(d[c][1] for c in both if c != TSMC) / k, 1)
            rec["exP"] = round(sum(prev[c][1] for c in both if c != TSMC) / k, 1)
            g = [(d[c][1] / prev[c][1] - 1) * 100 for c in both if prev[c][1] > 0]
            rec["med"] = round(statistics.median(g), 1) if g else None
        out.append(rec)
    return out


# ---------------------------------------------------------------- main
def main():
    old = load(OUT / "health.json", {})
    res = dict(old)
    res["updated"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")

    # 1. 估值快照
    try:
        v = valuation()
        hist = [r for r in old.get("v", []) if not v or r[0] != v[0]]
        if v:
            hist.append(v)
        res["v"] = sorted(hist)[-800:]
        res["vFields"] = V_FIELDS
    except Exception as e:
        DIAG["notes"].append(f"估值快照失敗：{e}")

    # 3. 季獲利（先做：資料最重要；新的期別優先）
    try:
        update_quarters()
        res["q"] = q_agg()
    except Exception as e:
        DIAG["notes"].append(f"季獲利失敗：{e!r}")

    # 2. 月營收廣度（用剩下的請求額度）
    try:
        res["m"] = update_months(old.get("m", []))
        res["mFields"] = M_FIELDS
    except Exception as e:
        DIAG["notes"].append(f"月營收失敗：{e!r}")

    DIAG["requests"] = REQ["n"]
    DIAG["stop"] = REQ["stop"]
    res["diag"] = {**DIAG, "tries": DIAG["tries"][-60:]}
    (OUT / "health.json").write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), "utf-8")
    q = res.get("q", [])
    print(f"估值 {len(res.get('v', []))} 天；月營收 {len(res.get('m', []))} 個月；季獲利 {len(q)} 期"
          f"（最新 {q[-1]['p'] if q else '—'}）；MOPS 請求 {REQ['n']} 次；停止原因：{REQ['stop']}")


if __name__ == "__main__":
    main()
