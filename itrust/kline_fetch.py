"""投本比前20名 日K資料（給 itrust 自用版頁面的 db kline 用）

由 .github/workflows/itrust_kline.yml 手動觸發（雲端排程用 workflow_dispatch 帶入參數）。
用法：python itrust/kline_fetch.py 20261019 "8021:L,3264:O,..."
  L＝上市（證交所 STOCK_DAY），O＝上櫃（櫃買 tradingStock）
輸出 itrust/kline/<D>.json：
  {"D", "generatedAt", "codes", "bars": {代號: [[YYYYMMDD, o, h, l, c, v(張)], …]},
   "ex": {代號: [[YYYYMMDD, "息"|"權"|"權息", 權值+息值], …]}, "diag": {…}}
價格不還原權息。只用 Python 標準函式庫。
"""
import json, re, sys, time, calendar, datetime as dt, urllib.request, urllib.parse
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


def months(D):
    d = dt.date(int(D[:4]), int(D[4:6]), int(D[6:]))
    res, y, m = [d], d.year, d.month
    for _ in range(MONTHS - 1):
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


def main():
    D, spec = sys.argv[1], sys.argv[2]
    assert re.fullmatch(r"20\d{6}", D), "bad date"
    codes = []
    for p in spec.split(","):
        m = re.fullmatch(r"\s*(\d{4,6}[A-Z]?):([LO])\s*", p)
        assert m, f"bad code spec: {p}"
        codes.append((m.group(1), m.group(2)))
    assert 0 < len(codes) <= 40, "1–40 codes"
    t0 = time.time()
    bars = {}
    for code, mk in codes:
        merged = {}
        for d in months(D):
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
    out = {"D": D, "generatedAt": now, "codes": [f"{c}:{m}" for c, m in codes], "bars": bars, "ex": ex, "diag": diag,
           "src": "證交所 STOCK_DAY／櫃買 tradingStock（GitHub Actions），未還原權息；v 為成交張數；ex 來自除權除息計算結果表"}
    (OUT / f"{D}.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for old in sorted(OUT.glob("2*.json"))[:-KEEP_FILES]:
        old.unlink()
    print(f"ok D={D} codes={len(codes)} lastIsD={diag['lastIsD']} req={diag['req']} fail={len(diag['fail'])} sec={diag['sec']}")
    if not last_ok:
        sys.exit("no code has a bar on D")


if __name__ == "__main__":
    main()
