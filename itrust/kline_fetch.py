"""投信／外資／土洋同買前20名（聯集）日K資料（給 itrust 自用版頁面的 db kline 用）

代號清單＝近 20 個交易日每天的三份前20名聯集（頁面「上榜隔日」要算名單隔天與之後抱著的報酬），最多 300 檔。
由 .github/workflows/itrust_kline.yml 手動觸發（雲端排程用 workflow_dispatch 帶入參數）。
用法：python itrust/kline_fetch.py 20261019 "8021:L,3264:O:202610,..."
  L＝上市（證交所 STOCK_DAY），O＝上櫃（櫃買 tradingStock）
  第三段 YYYYMM（選填）＝只抓這個月到 D 所在月份（db 已有日K的股票只補最近月份）；沒填就抓 7 個月
輸出 itrust/kline/<D>.json：
  {"D", "generatedAt", "codes", "bars": {代號: [[YYYYMMDD, o, h, l, c, v(張)], …]},
   "ex": {代號: [[YYYYMMDD, "息"|"權"|"權息", 權值+息值], …]},
   "inst": {代號: [[YYYYMMDD, 投信張, 外資張], …]}（FinMind，外資＝外陸資不含自營商；需 FINMIND_TOKEN）,
   "idx": {"TAIEX": [[YYYYMMDD, 加權指數收盤], …]}（證交所 FMTQIK，7 個月；FinMind 交叉核對記在 diag.taiexCheck）, "diag": {…}}
價格不還原權息。只用 Python 標準函式庫。
"""
import json, os, re, sys, time, calendar, datetime as dt, urllib.request, urllib.parse
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

OUT = Path(__file__).resolve().parent / "kline"
MONTHS = 7                     # D 所在月份＋往前 6 個月，約 140 個交易日
KEEP_FILES = 15                # itrust/kline/ 只保留最近幾份
GAP = {"twse": 1.3, "tpex": 1.0}
_last = {}
diag = {"req": 0, "fail": [], "month_rows": {}}


def get(url, host):
    for i in range(4):
        wait = GAP[host] - (time.time() - _last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        _last[host] = time.time()
        diag["req"] += 1
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
            time.sleep(3 * (i + 1))
    diag["fail"].append(url + " → " + err)
    return None


def num(x):
    s = str(x).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def clean(x):
    return int(x) if float(x).is_integer() else x


def half_up(x):
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def roc(s):
    y, m, d = re.findall(r"\d+", s)[:3]
    return f"{int(y) + 1911}{int(m):02d}{int(d):02d}"


def months(D, since=None):
    d = dt.date(int(D[:4]), int(D[4:6]), int(D[6:]))
    n = MONTHS
    if since:   # 只抓 since 月份到 D 所在月份（最少 1 個月、最多 MONTHS 個月）
        n = max(1, min(MONTHS, (d.year - int(since[:4])) * 12 + d.month - int(since[4:]) + 1))
    res, y, m = [d], d.year, d.month
    for _ in range(n - 1):
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
        res.append(dt.date(y, m, calendar.monthrange(y, m)[1]))   # 之前月份用月底，避開月初快取
    return res


def rows_twse(code, d):
    js = get(f"https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date={d:%Y%m%d}&stockNo={code}&response=json", "twse")
    if not js or js.get("stat") != "OK":
        return []
    out = []
    for r in js.get("data") or []:
        o, h, l, c, sh = num(r[3]), num(r[4]), num(r[5]), num(r[6]), num(r[1])
        if None in (o, h, l, c, sh) or c <= 0:
            continue
        out.append([roc(r[0]), clean(o), clean(h), clean(l), clean(c), half_up(sh / 1000)])
    return out


def rows_tpex(code, d):
    q = urllib.parse.quote(f"{d:%Y/%m/%d}", safe="")
    js = get(f"https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock?code={code}&date={q}&response=json", "tpex")
    t = ((js or {}).get("tables") or [{}])[0]
    out = []
    for r in t.get("data") or []:
        o, h, l, c, v = num(r[3]), num(r[4]), num(r[5]), num(r[6]), num(r[1])
        if None in (o, h, l, c, v) or c <= 0:
            continue
        out.append([roc(r[0]), clean(o), clean(h), clean(l), clean(c), half_up(v)])
    return out


def ex_twse(start, end, want):
    res, s = [], start
    while s <= end:   # 每段約 3 個月
        e = min(end, s + dt.timedelta(days=90))
        js = get(f"https://www.twse.com.tw/rwd/zh/exRight/TWT49U?startDate={s:%Y%m%d}&endDate={e:%Y%m%d}&response=json", "twse")
        if js and js.get("stat") == "OK":
            f = js.get("fields") or []
            iD, iC, iT, iV = f.index("資料日期"), f.index("股票代號"), f.index("權/息"), f.index("權值+息值")
            for r in js.get("data") or []:
                c = str(r[iC]).strip()
                if c in want and num(r[iV]) is not None:
                    res.append([c, roc(r[iD]), str(r[iT]).strip().replace("除", ""), num(r[iV])])
        else:
            diag["fail"].append(f"TWT49U {s:%Y%m%d}-{e:%Y%m%d}")
        s = e + dt.timedelta(days=1)
    return res


def ex_tpex(start, end, want):
    q = lambda d: urllib.parse.quote(f"{d:%Y/%m/%d}", safe="")
    js = get(f"https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ?startDate={q(start)}&endDate={q(end)}&response=json", "tpex")
    t = ((js or {}).get("tables") or [{}])[0]
    f = t.get("fields") or []
    if "代號" not in f:
        diag["fail"].append("exDailyQ fields missing")
        return []
    iD, iC, iT, iV = f.index("除權息日期"), f.index("代號"), f.index("權/息"), f.index("權值+息值")
    res = []
    for r in t.get("data") or []:
        c = str(r[iC]).strip()
        if c in want and num(r[iV]) is not None:
            res.append([c, roc(r[iD]), str(r[iT]).strip().replace("除", ""), num(r[iV])])
    return res


def inst_finmind(code, start, D):
    """FinMind TaiwanStockInstitutionalInvestorsBuySell → [[YYYYMMDD, 投信張, 外資張]]（張＝(買−賣)÷1000 四捨五入）"""
    tok = os.environ.get("FINMIND_TOKEN", "")
    q = urllib.parse.urlencode(dict(dataset="TaiwanStockInstitutionalInvestorsBuySell", data_id=code,
                                    start_date=f"{start[:4]}-{start[4:6]}-{start[6:]}"))
    for i in range(4):
        wait = 0.4 - (time.time() - _last.get("fm", 0))
        if wait > 0:
            time.sleep(wait)
        _last["fm"] = time.time()
        diag["req"] += 1
        try:
            req = urllib.request.Request("https://api.finmindtrade.com/api/v4/data?" + q,
                                         headers={"User-Agent": "Mozilla/5.0", **({"Authorization": "Bearer " + tok} if tok else {})})
            with urllib.request.urlopen(req, timeout=30) as r:
                js = json.loads(r.read().decode("utf-8"))
            break
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
            time.sleep(5 * (i + 1))
    else:
        diag["fail"].append(f"FinMind {code} → {err}")
        return None
    agg = {}
    for r in js.get("data") or []:
        d = str(r.get("date", "")).replace("-", "")
        if not d or d > D:
            continue
        k = {"Investment_Trust": 1, "Foreign_Investor": 2}.get(r.get("name"))
        if not k:
            continue
        net = (num(r.get("buy")) or 0) - (num(r.get("sell")) or 0)
        agg.setdefault(d, [d, 0, 0])[k] = half_up(abs(net) / 1000) * (1 if net >= 0 else -1)
    return [agg[k] for k in sorted(agg)]


def taiex(D):
    """加權指數收盤：證交所 FMTQIK「發行量加權股價指數」，D 所在月份往前共 MONTHS 個月 → [[YYYYMMDD, 收盤], …]。
    另抓 FinMind TaiwanStockPrice（data_id=TAIEX）逐日交叉核對收盤，結果記在 diag["taiexCheck"]（FinMind 沒資料就只記原因）。"""
    res = {}
    for d in months(D):
        js = get(f"https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?date={d:%Y%m%d}&response=json", "twse")
        if not js or js.get("stat") != "OK":
            diag["fail"].append(f"FMTQIK {d:%Y%m}")
            continue
        f = js.get("fields") or []
        if "日期" not in f or "發行量加權股價指數" not in f:
            diag["fail"].append(f"FMTQIK {d:%Y%m} fields {f}")
            continue
        iD, iC = f.index("日期"), f.index("發行量加權股價指數")
        for r in js.get("data") or []:
            c, k = num(r[iC]), roc(r[iD])
            if c and c > 0 and k <= D:
                res[k] = [k, clean(c)]
    rows = [res[k] for k in sorted(res)]
    chk = {"src": "FinMind TaiwanStockPrice TAIEX"}
    if rows:
        tok = os.environ.get("FINMIND_TOKEN", "")
        s = rows[0][0]
        q = urllib.parse.urlencode(dict(dataset="TaiwanStockPrice", data_id="TAIEX", start_date=f"{s[:4]}-{s[4:6]}-{s[6:]}"))
        try:
            diag["req"] += 1
            req = urllib.request.Request("https://api.finmindtrade.com/api/v4/data?" + q,
                                         headers={"User-Agent": "Mozilla/5.0", **({"Authorization": "Bearer " + tok} if tok else {})})
            with urllib.request.urlopen(req, timeout=30) as r:
                fm = {str(x.get("date", "")).replace("-", ""): num(x.get("close")) for x in (json.loads(r.read().decode("utf-8")).get("data") or [])}
            both = [(k, c, fm[k]) for k, c in rows if fm.get(k)]
            chk.update(n=len(both), last=both[-1][0] if both else None,
                       bad=[[k, c, f] for k, c, f in both if abs(c - f) > 0.005][:10])
        except Exception as e:  # noqa: BLE001
            chk["err"] = f"{type(e).__name__}: {e}"
    diag["taiexCheck"] = chk
    return rows


def main():
    D, spec = sys.argv[1], sys.argv[2]
    tag = sys.argv[3].strip() if len(sys.argv) > 3 else ""   # 一次性回補：輸出 <D>_<tag>.json，不覆蓋每日檔
    assert re.fullmatch(r"20\d{6}", D), "bad date"
    assert tag == "" or re.fullmatch(r"[A-Za-z0-9]{1,12}", tag), "bad tag"
    codes, seen, since = [], set(), {}
    for p in spec.split(","):
        m = re.fullmatch(r"\s*(\d{4,6}[A-Z]?):([LO])(?::(20\d{2}(?:0[1-9]|1[0-2])))?\s*", p)
        assert m, f"bad code spec: {p}"
        if m.group(1) in seen:   # 重複代號只抓一次
            continue
        seen.add(m.group(1))
        codes.append((m.group(1), m.group(2)))
        if m.group(3) and m.group(3) <= D[:6]:
            since[m.group(1)] = m.group(3)
    assert 0 < len(codes) <= 300, "1–300 codes"
    diag["since"] = len(since)
    t0 = time.time()
    bars = {}
    for code, mk in codes:
        merged = {}
        for d in months(D, since.get(code)):
            rows = rows_twse(code, d) if mk == "L" else rows_tpex(code, d)
            key = f"{mk}{d:%Y%m}"
            diag["month_rows"].setdefault(key, {})[code] = len(rows)
            for r in rows:
                if r[0] <= D:
                    merged[r[0]] = r
        bars[code] = [merged[k] for k in sorted(merged)]
    # 除權息（價格不還原，只標記）
    start = min((b[0][0] for b in bars.values() if b), default=D)
    sd, ed = dt.date(int(start[:4]), int(start[4:6]), int(start[6:])), dt.date(int(D[:4]), int(D[4:6]), int(D[6:]))
    exl = ex_twse(sd, ed, {c for c, mk in codes if mk == "L"}) + ex_tpex(sd, ed, {c for c, mk in codes if mk == "O"})
    ex = {c: {} for c, _ in codes}
    for c, d, t, v in exl:
        if d in {b[0] for b in bars[c]}:
            ex[c][d] = [d, t, v]
    ex = {c: [v[k] for k in sorted(v)] for c, v in ex.items()}
    # 法人買賣超張數（FinMind），範圍與 bars 相同；失敗的代號不放（頁面保留既有 inst）
    inst = {}
    for c, _ in codes:
        if not bars[c]:
            continue
        rows = inst_finmind(c, bars[c][0][0], D)
        if rows is not None:
            inst[c] = rows
    diag["instLastIsD"] = f"{sum(1 for v in inst.values() if v and v[-1][0] == D)}/{len(codes)}"
    # 加權指數收盤（頁面「大盤在 20 日線上」濾網用）
    idx = {"TAIEX": taiex(D)}
    diag["taiexLast"] = idx["TAIEX"][-1] if idx["TAIEX"] else None
    # 同月份各檔筆數應一致（停牌或新上市除外），不一致記在 diag
    odd = {}
    for key, cnt in diag["month_rows"].items():
        vals = sorted(cnt.values())
        mode = max(set(vals), key=vals.count)
        bad = {c: n for c, n in cnt.items() if n != mode}
        if bad:
            odd[key] = {"mode": mode, "diff": bad}
    diag["month_odd"] = odd
    diag["sec"] = round(time.time() - t0, 1)
    del diag["month_rows"]
    last_ok = [c for c, _ in codes if bars[c] and bars[c][-1][0] == D]
    diag["lastIsD"] = f"{len(last_ok)}/{len(codes)}"
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y/%m/%d %H:%M")
    OUT.mkdir(exist_ok=True)
    out = {"D": D, "generatedAt": now, "codes": [f"{c}:{m}" + (f":{since[c]}" if c in since else "") for c, m in codes], "bars": bars, "ex": ex, "inst": inst, "idx": idx, "diag": diag,
           "src": "證交所 STOCK_DAY／櫃買 tradingStock（GitHub Actions），未還原權息；v 為成交張數；ex 來自除權除息計算結果表"}
    if tag:
        out["tag"] = tag
    (OUT / (f"{D}_{tag}.json" if tag else f"{D}.json")).write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for old in sorted(OUT.glob("2???????.json"))[:-KEEP_FILES]:   # 只輪替每日檔；回補檔用完手動刪
        old.unlink()
    print(f"ok D={D} tag={tag or '-'} codes={len(codes)} lastIsD={diag['lastIsD']} instLastIsD={diag['instLastIsD']} taiex={diag['taiexLast']} req={diag['req']} fail={len(diag['fail'])} sec={diag['sec']}")
    if not last_ok:
        sys.exit("no code has a bar on D")


if __name__ == "__main__":
    main()
