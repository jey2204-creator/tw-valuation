"""「投信＋外資買超佔股本 每日更新」主排程 方案B：GitHub Actions 抓原始資料（只抓，不算）。

把原本在使用者電腦內建瀏覽器做的步驟 1～7 全部移到這裡：
  證交所 T86（D 與前 4 個交易日）、FMTQIK 交易日、MI_QFIIS 掛牌股數（當日沒發布就往前備援最多 3 個交易日）、
  MI_INDEX（D 與近 40 個交易日的開高低收）、處置、TWT49U 除權息、openapi t187ap03_L／TWT85U、
  櫃買 dailyTrade（D 與前 4 日）、otc 收盤（D 與近 40 日）、qfii、disposal、exDailyQ、mopsfin_t187ap03_O、tpex_cmode、
  公開資訊觀測站 t05st03（只查投信買超且掛牌股數≠觀測站股數的公司）。
計算（佔股本、金額、技術欄位、產業彙總）在雲端排程用 itrust/daily_build.py 做，觸發價／停損等欄位不進 repo。

用法：python itrust/daily_fetch.py 20261021
輸出：itrust/daily/<D>.json（只用 Python 標準函式庫）。
"""
import json, re, sys, time, datetime as dt, urllib.request, urllib.parse
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

OUT = Path(__file__).resolve().parent / "daily"
KEEP_FILES = 15
GAP = {"twse": 1.3, "tpex": 1.0, "openapi": 0.8, "mops": 0.9}
TW = "https://www.twse.com.tw"
TP = "https://www.tpex.org.tw"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*"}
COMMON = re.compile(r"^[1-9]\d{3}$")
_last = {}
diag = {"req": 0, "fail": [], "notes": [], "fields": {}}


def log(msg):
    print(msg, flush=True)
    diag["notes"].append(msg)


def req(host, url, method="GET", body=None, headers=None, referer=None, retries=4):
    for i in range(retries):
        wait = GAP[host] - (time.time() - _last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        _last[host] = time.time()
        diag["req"] += 1
        h = dict(UA)
        if referer:
            h["Referer"] = referer
        if headers:
            h.update(headers)
        data = None
        if body is not None:
            data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        try:
            r = urllib.request.Request(url, data=data, method=method, headers=h)
            with urllib.request.urlopen(r, timeout=60) as resp:
                raw = resp.read()
            return json.loads(raw.decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
            time.sleep(4 * (i + 1))
    diag["fail"].append(f"{url} {body if isinstance(body, str) else ''} → {err}")
    return None


def twse(path, referer=f"{TW}/zh/"):
    return req("twse", TW + path, referer=referer)


def tpex_post(path, body):
    return req("tpex", TP + path, "POST", body, {"Content-Type": "application/x-www-form-urlencoded"}, referer=f"{TP}/zh-tw/")


def tpex_get(path):
    return req("tpex", TP + path, referer=f"{TP}/zh-tw/")


def num(x):
    """去逗號轉數字；非數字回 None。"""
    s = re.sub(r"<[^>]*>", "", str(x)).replace(",", "").strip()
    if s in ("", "--", "---", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def inum(x):
    v = num(x)
    return None if v is None else int(v)


def clean(x):
    if isinstance(x, float) and x.is_integer():
        return int(x)
    return x


def half_up(x, nd=0):
    q = Decimal(1).scaleb(-nd)
    v = Decimal(str(x)).quantize(q, rounding=ROUND_HALF_UP)
    return int(v) if nd == 0 else float(v)


def roc_to_ymd(s):
    """'115/10/21'、'1151021'、'115年10月21日' → '20261021'；轉不了回 None。"""
    s = str(s).strip()
    m = re.match(r"^(\d{2,3})[/年.](\d{1,2})[/月.](\d{1,2})", s)
    if m:
        return f"{int(m.group(1)) + 1911:04d}{int(m.group(2)):02d}{int(m.group(3)):02d}"
    m = re.match(r"^(\d{3})(\d{2})(\d{2})$", s)
    if m:
        return f"{int(m.group(1)) + 1911:04d}{m.group(2)}{m.group(3)}"
    return None


def ymd_to_sl(d):
    return f"{d[:4]}/{d[4:6]}/{d[6:]}"


def ymd_to_roc(d):
    return f"{int(d[:4]) - 1911}/{d[4:6]}/{d[6:]}"


def fidx(fields, *names, default=None):
    """依欄位名稱找索引（去空白後完全相符或包含）；找不到用 default。"""
    norm = [re.sub(r"\s+", "", str(f)) for f in (fields or [])]
    for n in names:
        if n in norm:
            return norm.index(n)
    for n in names:
        for i, f in enumerate(norm):
            if n in f:
                return i
    return default


def main():
    D = sys.argv[1]
    assert re.match(r"^\d{8}$", D), "日期格式 YYYYMMDD"
    SL, ROC = ymd_to_sl(D), ymd_to_roc(D)
    t0 = time.time()
    out = {"D": D, "fetchedAt": None, "days40": [], "p4": [], "twse": {}, "tpex": {}, "mops": {}, "diag": diag}

    # ── 1) 證交所 T86（判斷開市）
    j = twse(f"/rwd/zh/fund/T86?date={D}&selectType=ALLBUT0999&response=json", f"{TW}/zh/trading/foreign/t86.html")
    if not j or j.get("stat") != "OK" or not j.get("data") or str(j.get("date")) != D:
        out["open"] = False
        out["reason"] = f"T86 stat={j and j.get('stat')} date={j and j.get('date')} rows={len((j or {}).get('data') or [])}"
        log("休市或資料未發布：" + out["reason"])
        write(out, D)
        return
    out["open"] = True
    f = j.get("fields") or []
    diag["fields"]["T86"] = f
    i_fv = fidx(f, "外陸資買賣超股數(不含外資自營商)", default=4)
    i_v = fidx(f, "投信買賣超股數", default=10)
    assert i_fv == 4 and i_v == 10, f"T86 欄位位置改變 fv={i_fv} v={i_v}"
    rows = []
    for r in j["data"]:
        code = str(r[0]).strip()
        if not COMMON.match(code):
            continue
        rows.append([code, str(r[1]), inum(r[i_fv]) or 0, inum(r[i_v]) or 0])
    out["twse"]["t86"] = {"date": D, "t86Rows": len(j["data"]), "rows": rows}
    log(f"T86 {D}: 全部 {len(j['data'])} 列，普通股 {len(rows)}")

    # ── 2) 交易日 FMTQIK（本月＋前 3 個月）
    days = set()
    y, m = int(D[:4]), int(D[4:6])
    for k in range(4):
        mm, yy = m - k, y
        while mm <= 0:
            mm += 12
            yy -= 1
        jj = twse(f"/rwd/zh/afterTrading/FMTQIK?date={yy:04d}{mm:02d}01&response=json")
        for r in (jj or {}).get("data") or []:
            d = roc_to_ymd(r[0])
            if d:
                days.add(d)
    if D not in days:
        log(f"FMTQIK 尚未包含 {D}，自行加入")
        days.add(D)
    alld = sorted(d for d in days if d <= D)
    DAYS40 = alld[-40:]
    P4 = DAYS40[-5:-1]
    out["days40"], out["p4"] = DAYS40, P4
    log(f"DAYS40 {DAYS40[0]}～{DAYS40[-1]}（{len(DAYS40)} 天），P4={P4}")

    # ── 2) 掛牌股數 MI_QFIIS（備援：往前最多 3 個交易日）
    sx = None
    qrows = []
    for d in [D] + list(reversed(P4[-3:])):
        jj = twse(f"/rwd/zh/fund/MI_QFIIS?date={d}&selectType=ALLBUT0999&response=json")
        if jj and jj.get("stat") == "OK" and jj.get("data"):
            sx = d
            diag["fields"]["MI_QFIIS"] = jj.get("fields")
            for r in jj["data"]:
                code = str(r[0]).strip()
                if COMMON.match(code):
                    qrows.append([code, inum(r[3]), num(r[6]), num(r[7])])
            break
        log(f"MI_QFIIS {d}: stat={jj and jj.get('stat')}，改抓前一交易日")
    out["twse"]["qfiis"] = {"date": sx, "rows": qrows}
    log(f"MI_QFIIS 採用 {sx}：{len(qrows)} 列")

    # ── 2) 收盤與漲跌 MI_INDEX（D）
    def mi_index(d):
        jj = twse(f"/rwd/zh/afterTrading/MI_INDEX?date={d}&type=ALLBUT0999&response=json")
        if not jj or jj.get("stat") != "OK":
            raise RuntimeError(f"MI_INDEX {d} stat={jj and jj.get('stat')}")
        tb = next(t for t in jj["tables"] if t.get("fields") and re.sub(r"\s+", "", t["fields"][0]) == "證券代號")
        f = tb["fields"]
        io, ih, il, ic = fidx(f, "開盤價"), fidx(f, "最高價"), fidx(f, "最低價"), fidx(f, "收盤價")
        isg, idf = fidx(f, "漲跌(+/-)"), fidx(f, "漲跌價差")
        return tb, io, ih, il, ic, isg, idf

    tb, io, ih, il, ic, isg, idf = mi_index(D)
    diag["fields"]["MI_INDEX"] = tb["fields"]
    assert None not in (io, ih, il, ic, isg, idf), "MI_INDEX 欄位名稱改變"
    px = []
    for r in tb["data"]:
        code = str(r[0]).strip()
        if not COMMON.match(code):
            continue
        cl = num(r[ic])
        sign = re.sub(r"<[^>]*>", "", str(r[isg])).strip()
        diff = num(r[idf])
        if sign == "X" or diff is None:
            chg = None
        elif sign == "-":
            chg = -diff
        else:
            chg = diff
        px.append([code, clean(cl), clean(chg), clean(num(r[io])), clean(num(r[ih])), clean(num(r[il]))])
    out["twse"]["px"] = {"date": D, "rows": px}
    log(f"MI_INDEX {D}: 普通股 {len(px)} 列")

    # ── 2) 處置（45 天內）
    d45 = (dt.datetime.strptime(D, "%Y%m%d") - dt.timedelta(days=45)).strftime("%Y%m%d")
    jj = twse(f"/rwd/zh/announcement/punish?startDate={d45}&endDate={D}&response=json")
    dp = []
    diag["fields"]["punish"] = (jj or {}).get("fields")
    for r in (jj or {}).get("data") or []:
        code = str(r[2]).strip()
        m = re.findall(r"(\d{2,3}/\d{1,2}/\d{1,2})", str(r[6]))
        if len(m) >= 2:
            a, b = roc_to_ymd(m[0]), roc_to_ymd(m[1])
            if a and b:
                dp.append([code, a, b])
    out["twse"]["punish"] = dp
    log(f"處置公告 {len(dp)} 筆")

    # ── 4) openapi：觀測站股數對照、全額交割
    jj = req("openapi", "https://openapi.twse.com.tw/v1/opendata/t187ap03_L")
    t187 = []
    if jj:
        diag["fields"]["t187ap03_L"] = list(jj[0].keys()) if jj else []
        for r in jj:
            code = str(r.get("公司代號", "")).strip()
            if COMMON.match(code):
                t187.append([code, inum(r.get("已發行普通股數或TDR原股發行股數")), inum(r.get("私募股數")) or 0,
                             str(r.get("產業別", "")).strip(), str(r.get("出表日期", "")).strip()])
    out["twse"]["t187"] = t187
    jj = req("openapi", "https://openapi.twse.com.tw/v1/exchangeReport/TWT85U")
    out["twse"]["fd"] = sorted({str(r.get("Code", "")).strip() for r in (jj or [])} - {""})
    log(f"t187ap03_L {len(t187)} 列；全額交割 {len(out['twse']['fd'])} 檔")

    # ── 5) 櫃買
    jj = tpex_post("/www/zh-tw/insti/dailyTrade", f"type=Daily&sect=EW&date={urllib.parse.quote(SL)}&response=json")
    tb = ((jj or {}).get("tables") or [{}])[0]
    tdate = str((jj or {}).get("date") or tb.get("date") or "")
    diag["fields"]["dailyTrade"] = tb.get("fields")
    trows = []
    if tdate == D and tb.get("data"):
        f = tb.get("fields") or []
        i_fv = fidx(f, "外資及陸資(不含外資自營商)買賣超股數", default=4)
        i_v = fidx(f, "投信買賣超股數", default=13)
        if (i_fv, i_v) != (4, 13):
            log(f"dailyTrade 欄位名稱對應到 fv={i_fv} v={i_v}（預期 4/13），改用預期位置")
            i_fv, i_v = 4, 13
        for r in tb["data"]:
            code = str(r[0]).strip()
            if COMMON.match(code):
                trows.append([code, str(r[1]), inum(r[i_fv]) or 0, inum(r[i_v]) or 0])
        out["tpex"]["daily"] = {"date": D, "t86Rows": len(tb["data"]), "rows": trows}
        log(f"櫃買 dailyTrade {D}: 全部 {len(tb['data'])} 列，普通股 {len(trows)}")
    else:
        out["tpex"]["daily"] = None
        log(f"櫃買 dailyTrade 回傳 date={tdate}≠{D}，上櫃未更新")

    def otc(d):
        jj = tpex_post("/www/zh-tw/afterTrading/otc", f"date={ymd_to_sl(d)}&type=EW&response=json")
        if not jj or str(jj.get("date")) != d:
            raise RuntimeError(f"otc {d} got {jj and jj.get('date')}")
        return jj["tables"][0]

    tpx = []
    if out["tpex"]["daily"]:
        tb = otc(D)
        diag["fields"]["otc"] = tb.get("fields")
        for r in tb["data"]:
            code = str(r[0]).strip()
            if COMMON.match(code):
                # 0 代號 2 收盤 3 漲跌 4 開 5 高 6 低 14 掛牌股數
                tpx.append([code, clean(num(r[2])), clean(num(r[3])), clean(num(r[4])), clean(num(r[5])), clean(num(r[6])), inum(r[14])])
        out["tpex"]["px"] = {"date": D, "rows": tpx}
        log(f"櫃買 otc {D}: 普通股 {len(tpx)} 列")

        jj = tpex_post("/www/zh-tw/insti/qfii", f"date={urllib.parse.quote(SL)}&response=json")
        tb = ((jj or {}).get("tables") or [{}])[0]
        qd = str((jj or {}).get("date") or tb.get("date") or "")
        diag["fields"]["qfii"] = tb.get("fields")
        if qd in (D, ROC) and tb.get("data"):
            out["tpex"]["qfii"] = {"date": D, "rows": [[str(r[1]).strip(), num(str(r[6]).replace("%", "")), num(str(r[7]).replace("%", ""))]
                                                       for r in tb["data"] if COMMON.match(str(r[1]).strip())]}
            log(f"櫃買 qfii {len(out['tpex']['qfii']['rows'])} 列")
        else:
            out["tpex"]["qfii"] = None
            log(f"櫃買 qfii 回傳 date={qd}≠{D}，hp／rm 留 null")

        jj = tpex_post("/www/zh-tw/bulletin/disposal", f"startDate={ymd_to_sl(d45)}&endDate={SL}&response=json")
        tb = ((jj or {}).get("tables") or [{}])[0]
        diag["fields"]["disposal"] = tb.get("fields")
        tdp = []
        for r in tb.get("data") or []:
            m = re.findall(r"(\d{2,3}/\d{1,2}/\d{1,2})", str(r[5]))
            if len(m) >= 2:
                a, b = roc_to_ymd(m[0]), roc_to_ymd(m[1])
                if a and b:
                    tdp.append([str(r[2]).strip(), a, b])
        out["tpex"]["punish"] = tdp
        log(f"櫃買處置公告 {len(tdp)} 筆")

        jj = tpex_get("/openapi/v1/mopsfin_t187ap03_O")
        tt = []
        if jj:
            diag["fields"]["mopsfin_t187ap03_O"] = list(jj[0].keys()) if jj else []
            for r in jj:
                code = str(r.get("SecuritiesCompanyCode", "")).strip()
                if not COMMON.match(code):
                    continue
                ps = r.get("PrivateStock")
                if isinstance(ps, dict):
                    priv = inum(ps.get("shares")) or 0
                else:
                    priv = inum(r.get("PrivateStock.shares", ps)) or 0
                tt.append([code, inum(r.get("IssueShares")), priv, str(r.get("SecuritiesIndustryCode", "")).strip(), str(r.get("Date", "")).strip()])
        out["tpex"]["t187"] = tt
        jj = tpex_get("/openapi/v1/tpex_cmode")
        fd = []
        if jj:
            diag["fields"]["tpex_cmode"] = list(jj[0].keys()) if jj else []
            for r in jj:
                code = str(r.get("SecuritiesCompanyCode") or r.get("Code") or "").strip()
                if COMMON.match(code) and str(r.get("AlteredTrading", "")).strip():
                    fd.append(code)
        out["tpex"]["fd"] = sorted(set(fd))
        log(f"櫃買 t187 {len(tt)} 列；全額交割 {len(fd)} 檔")

    # ── 前 4 個交易日的法人買賣超（f4、前 2 日核對）
    prev = {}
    for d in P4:
        jj = twse(f"/rwd/zh/fund/T86?date={d}&selectType=ALLBUT0999&response=json")
        if jj and jj.get("stat") == "OK":
            prev[d] = [[str(r[0]).strip(), inum(r[4]) or 0, inum(r[10]) or 0] for r in jj["data"] if COMMON.match(str(r[0]).strip())]
        else:
            log(f"T86 {d} 抓取失敗")
    out["twse"]["prev"] = prev
    tprev = {}
    if out["tpex"]["daily"]:
        for d in P4:
            jj = tpex_post("/www/zh-tw/insti/dailyTrade", f"type=Daily&sect=EW&date={urllib.parse.quote(ymd_to_sl(d))}&response=json")
            tb = ((jj or {}).get("tables") or [{}])[0]
            if str((jj or {}).get("date") or tb.get("date") or "") == d and tb.get("data"):
                tprev[d] = [[str(r[0]).strip(), inum(r[4]) or 0, inum(r[13]) or 0] for r in tb["data"] if COMMON.match(str(r[0]).strip())]
            else:
                log(f"dailyTrade {d} 抓取失敗")
    out["tpex"]["prev"] = tprev

    # ── 技術欄位用的代號：投信 v>0 ∪ 外資買超且金額約 ≥0.5 億（放寬到 0.45 當超集合）
    def need_codes(rows, pxrows, srows):
        cl = {r[0]: r[1] for r in pxrows}
        ss = {r[0]: r[1] for r in srows}
        codes = set()
        for code, _n, fv, v in rows:
            if v > 0:
                codes.add(code)
            elif fv > 0 and cl.get(code) and ss.get(code):
                if half_up(fv / 1000) * 1000 * cl[code] / 1e8 >= 0.45:
                    codes.add(code)
        return codes

    codes_tw = need_codes(rows, px, qrows)
    codes_tp = need_codes(trows, [[r[0], r[1]] for r in tpx], [[r[0], r[6]] for r in tpx]) if out["tpex"]["daily"] else set()
    log(f"技術欄位代號：上市 {len(codes_tw)}、上櫃 {len(codes_tp)}")

    # ── 3) 上市近 40 日開高低收（MI_INDEX 逐日）＋除權息
    ohlc = {c: [] for c in codes_tw}
    px_prev = {}  # 前 2 個交易日全市場收盤（前 2 日核對重算產業彙總用）
    for d in DAYS40:
        if d == D:  # 當日已抓過（px：代號, 收盤, 漲跌, 開, 高, 低）
            for code, cl, _chg, o, h, l in px:
                if code in ohlc and cl and cl > 0:
                    ohlc[code].append([d, o, h, l, cl])
            continue
        try:
            tbx, jo, jh, jl, jc, _s, _d = mi_index(d)
        except Exception as e:  # noqa: BLE001
            log(f"MI_INDEX {d} 失敗：{e}")
            continue
        for r in tbx["data"]:
            code = str(r[0]).strip()
            c = num(r[jc])
            if d in P4[-2:] and COMMON.match(code) and c is not None:
                px_prev.setdefault(d, {})[code] = clean(c)
            if code not in ohlc:
                continue
            if not c or c <= 0:
                continue
            ohlc[code].append([d, clean(num(r[jo])), clean(num(r[jh])), clean(num(r[jl])), clean(c)])
    out["twse"]["ohlc"] = ohlc
    out["twse"]["px_prev"] = px_prev
    jj = twse(f"/rwd/zh/exRight/TWT49U?startDate={DAYS40[0]}&endDate={D}&response=json")
    ex = []
    diag["fields"]["TWT49U"] = (jj or {}).get("fields")
    for r in (jj or {}).get("data") or []:
        d = roc_to_ymd(r[0])
        if d:
            ex.append([str(r[1]).strip(), d, clean(num(r[3])), clean(num(r[4]))])
    out["twse"]["ex"] = ex
    log(f"上市日K {sum(len(v) for v in ohlc.values())} 根；除權息 {len(ex)} 筆")

    # ── 5) 上櫃近 40 日開高低收（otc 逐日）＋除權息
    if out["tpex"]["daily"]:
        tohlc = {c: [] for c in codes_tp}
        tpx_prev = {}
        for d in DAYS40:
            if d == D:  # 當日已抓過（tpx：代號, 收盤, 漲跌, 開, 高, 低, 股數）
                for code, cl, _chg, o, h, l, _s in tpx:
                    if code in tohlc and cl and cl > 0:
                        tohlc[code].append([d, o, h, l, cl])
                continue
            try:
                tbx = otc(d)
            except Exception as e:  # noqa: BLE001
                log(f"otc {d} 失敗：{e}")
                continue
            for r in tbx["data"]:
                code = str(r[0]).strip()
                c = num(r[2])
                if d in P4[-2:] and COMMON.match(code) and c is not None:
                    tpx_prev.setdefault(d, {})[code] = clean(c)
                if code not in tohlc:
                    continue
                if not c or c <= 0:
                    continue
                tohlc[code].append([d, clean(num(r[4])), clean(num(r[5])), clean(num(r[6])), clean(c)])
        out["tpex"]["ohlc"] = tohlc
        out["tpex"]["px_prev"] = tpx_prev
        jj = tpex_post("/www/zh-tw/bulletin/exDailyQ", f"startDate={urllib.parse.quote(ymd_to_sl(DAYS40[0]))}&endDate={urllib.parse.quote(SL)}&response=json")
        tb = ((jj or {}).get("tables") or [{}])[0]
        diag["fields"]["exDailyQ"] = tb.get("fields")
        tex = []
        for r in tb.get("data") or []:
            d = roc_to_ymd(r[0])
            if d:
                tex.append([str(r[1]).strip(), d, clean(num(r[3])), clean(num(r[4]))])
        out["tpex"]["ex"] = tex
        log(f"上櫃日K {sum(len(v) for v in tohlc.values())} 根；除權息 {len(tex)} 筆")

    # ── 7) 觀測站：投信 v>0 且 掛牌股數 s ≠ 觀測站 sm 的公司
    sm_tw = {r[0]: r[1] for r in t187}
    sm_tp = {r[0]: r[1] for r in out["tpex"].get("t187") or []}
    s_tw = {r[0]: r[1] for r in qrows}
    s_tp = {r[0]: r[6] for r in tpx}
    need = []
    for code, _n, _fv, v in rows:
        if v > 0 and s_tw.get(code) is not None and sm_tw.get(code) != s_tw.get(code):
            need.append(code)
    for code, _n, _fv, v in trows:
        if v > 0 and s_tp.get(code) is not None and sm_tp.get(code) != s_tp.get(code):
            need.append(code)
    mops = {}
    for code in need:
        jj = req("mops", "https://mops.twse.com.tw/mops/api/t05st03", "POST", {"companyId": code},
                 {"Content-Type": "application/json"}, referer="https://mops.twse.com.tw/mops/")
        res = (jj or {}).get("result") or {}
        csa = res.get("commonStockAmount")
        csa = csa.get("value") if isinstance(csa, dict) else csa
        hcb = res.get("haveCompanyBonds")
        hcb = hcb.get("value") if isinstance(hcb, dict) else hcb
        m = re.match(r"^\s*([\d,]+)", str(csa or ""))
        mops[code] = {"sm": int(m.group(1).replace(",", "")) if m else None, "cb": bool(hcb) if hcb is not None else None,
                      "raw": str(csa)[:60] if csa is not None else None}
    out["mops"] = mops
    log(f"觀測站查詢 {len(need)} 家，取得 {sum(1 for v in mops.values() if v['sm'] is not None)} 家")

    # ── 檢查碼（由原始列直接算，給雲端比對）
    def H(pairs):
        return sum(v * (int(c) % 97) for c, v in pairs)

    chk = {}
    for mk, rs in (("twse", rows), ("tpex", trows)):
        nz = [(c, v) for c, _n, fv, v in rs if v != 0]
        chk[mk] = {"trustN": len(nz), "trustSum": sum(v for _c, v in nz), "Hv": H(nz),
                   "trustBuy": sum(1 for _c, v in nz if v > 0), "trustSell": sum(1 for _c, v in nz if v < 0),
                   "foreignBuy": sum(1 for _c, _n, fv, _v in rs if fv > 0), "foreignSell": sum(1 for _c, _n, fv, _v in rs if fv < 0),
                   "Hfv": H([(c, fv) for c, _n, fv, _v in rs if fv != 0])}
    out["check"] = chk
    out["fetchedAt"] = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y/%m/%d %H:%M")
    diag["seconds"] = int(time.time() - t0)
    write(out, D)


def write(out, D):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{D}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    files = sorted(OUT.glob("*.json"))
    for old in files[:-KEEP_FILES]:
        old.unlink()
    print(f"寫出 {p}（{p.stat().st_size / 1e6:.2f} MB），請求 {diag['req']} 次，失敗 {len(diag['fail'])}")
    if diag["fail"]:
        print("\n".join(diag["fail"]))


if __name__ == "__main__":
    main()
