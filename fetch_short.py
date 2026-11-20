"""做空資訊 → data/short.json（掃描頁「空」模式小卡與放大卡用；2026-11-20）

每檔：融券餘額／融券限額／融券增減／融資餘額（張）＋標記（平盤下可否放空、停券、前一日跌停）＋停券（最後回補日）預告。
來源（都是公開資料；券商自己的券源查不到，只能用「融券限額還剩多少」當參考）：
  上市融資融券  www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN（跟 fetch_chip.py 同一支）
  上櫃融資融券  www.tpex.org.tw/www/zh-tw/margin/balance
  平盤下得融(借)券賣出之證券名單、停券預告表：證交所／櫃買 OpenAPI（路徑由 swagger.json 依中文說明找，找不到再用猜的）
輸出 data/short.json：
  {"upd": "…", "md": "YYYYMMDD"(融資融券資料日), "fd": {"twse": …, "tpex": …}(平盤下名單資料日；沒抓到＝null),
   "s": {代號: [融券餘額, 融券限額, 融券增減, 融資餘額, 標記]},   標記字元：F＝在平盤下可空名單、X＝暫停融券賣出、B＝暫停借券賣出、L＝前一日跌停（當日不得平盤下放空）、N＝融資融券表註記停券
   "r": {代號: [停券起日(最後回補日), 停券迄日, 原因]}}
  不在 s 裡的股票＝不是信用交易股（不能融券）。
診斷 data/short_diag.json（欄位名稱、筆數、找到的 OpenAPI 路徑）。
用法：python fetch_short.py
"""
import json, sys, time, datetime as dt
from pathlib import Path
import urllib.request
import fetch_momentum as fm

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data"
diag = {}


def digits(v):
    return "".join(ch for ch in str(v or "") if ch.isdigit())


def ymd(v):
    """各種日期寫法 → YYYYMMDD（民國 7 碼、西元 8 碼、115/11/20）"""
    s = str(v or "").strip()
    p = [x for x in s.replace("-", "/").replace(".", "/").split("/") if x.strip()]
    try:
        if len(p) == 3:
            y = int(p[0]); y += 1911 if y < 1911 else 0
            return f"{y:04d}{int(p[1]):02d}{int(p[2]):02d}"
        dg = digits(s)
        if len(dg) == 8:
            return dg
        if len(dg) == 7:
            return f"{int(dg[:3]) + 1911:04d}{dg[3:]}"
    except ValueError:
        pass
    return None


# ---------- 融資融券（rwd，可指定日期）----------
def twse_margin(d):
    js = fm.get(f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={d:%Y%m%d}&selectType=ALL&response=json", "twse")
    for fields, rows in fm.tables_of(js):
        fs = [str(f) for f in fields]
        ic = fm.col(fs, "代號")
        prev = [i for i, f in enumerate(fs) if "前日餘額" in f]
        now = [i for i, f in enumerate(fs) if "今日餘額" in f]
        lim = [i for i, f in enumerate(fs) if "限額" in f]
        nt = next((i for i, f in enumerate(fs) if "註記" in f), None)
        if ic is None or len(prev) < 2 or len(now) < 2:
            continue
        out = {}
        for r in rows:
            c = fm.ok_code(r[ic])
            if not c or len(r) <= now[1]:
                continue
            mb, sp, sb = fm.num(r[now[0]]), fm.num(r[prev[1]]), fm.num(r[now[1]])
            if sb is None:
                continue
            sl = fm.num(r[lim[1]]) if len(lim) >= 2 and len(r) > lim[1] else None
            mark = str(r[nt]).strip() if nt is not None and len(r) > nt else ""
            out[c] = [sb, sl, sb - (sp or 0), mb, mark]
        if out:
            diag["mL"] = {"rows": len(out), "fields": fs, "marks": sorted({v[4] for v in out.values()})[:20], "notes": [str(x)[:200] for x in (js.get("notes") or [])][:12] if isinstance(js, dict) else []}
            return out
    diag["mL"] = {"rows": 0, "stat": str(js.get("stat", ""))[:60] if isinstance(js, dict) else ""}
    return None


def tpex_margin(d):
    js = fm.get(f"https://www.tpex.org.tw/www/zh-tw/margin/balance?date={d:%Y}%2F{d:%m}%2F{d:%d}&id=&response=json", "tpex")
    rd = fm.resp_date(js)
    if rd != d:
        diag["mO"] = {"rows": 0, "resp_date": str(rd)}
        return None
    for fields, rows in fm.tables_of(js):
        fs = [str(f) for f in fields]
        f_ = lambda key, avoid=None: next((i for i, f in enumerate(fs) if key in f and not (avoid and avoid in f)), None)
        n1, p2, n2, l2 = f_("資餘額", "前"), f_("前券餘額"), f_("券餘額", "前"), f_("券限額")
        nt = f_("備註") if f_("備註") is not None else f_("註記")
        if None in (n1, p2, n2):
            continue
        out = {}
        for r in rows:
            c = fm.ok_code(r[0])
            if not c or len(r) <= n2:
                continue
            mb, sp, sb = fm.num(r[n1]), fm.num(r[p2]), fm.num(r[n2])
            if sb is None:
                continue
            sl = fm.num(r[l2]) if l2 is not None and len(r) > l2 else None
            mark = str(r[nt]).strip() if nt is not None and len(r) > nt else ""
            out[c] = [sb, sl, sb - (sp or 0), mb, mark]
        if out:
            diag["mO"] = {"rows": len(out), "fields": fs, "marks": sorted({v[4] for v in out.values()})[:20], "notes": [str(x)[:200] for x in (js.get("notes") or [])][:12]}
            return out
    diag["mO"] = {"rows": 0}
    return None


# ---------- OpenAPI：用 swagger 的中文說明找路徑 ----------
def raw(url, timeout=45):
    req = urllib.request.Request(url, headers=fm.UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8-sig"))


def find_paths(base, sw_url, tag):
    """回傳 [(path, 說明)]：說明裡有 融券／平盤／停券／借券 的全部記到診斷檔"""
    try:
        sw = raw(sw_url)
    except Exception as e:
        diag[tag + "_swagger"] = f"ERR {e}"[:200]
        return []
    out = []
    for p, v in (sw.get("paths") or {}).items():
        g = (v or {}).get("get") or {}
        desc = f"{g.get('summary', '')} {g.get('description', '')}"
        if any(k in desc for k in ("融券", "平盤", "停券", "借券")):
            out.append((p, desc.strip()[:80]))
    diag[tag + "_swagger"] = out
    diag[tag + "_base"] = (sw.get("servers") or [{}])[0].get("url") or sw.get("basePath") or ""
    return out


def api(base, path, tag):
    try:
        js = raw(base + path)
    except Exception as e:
        diag[tag] = {"path": path, "err": str(e)[:160]}
        return []
    rows = js if isinstance(js, list) else []
    diag[tag] = {"path": path, "rows": len(rows), "keys": list(rows[0].keys()) if rows and isinstance(rows[0], dict) else [], "first": rows[0] if rows else None,
                 "sample": rows[1:4]}
    return [r for r in rows if isinstance(r, dict)]


def code_of(r):
    for k, v in r.items():
        if "代號" in k or k.lower() in ("code", "securitiescompanycode", "stockno", "stockcode", "symbol"):
            c = fm.ok_code(v)
            if c:
                return c
    for v in r.values():                                   # 找不到欄名就取第一個像代號的值
        c = fm.ok_code(v)
        if c:
            return c
    return None


def date_of(rows):
    for r in rows[:3]:
        for k, v in r.items():
            if "日期" in k or k.lower() in ("date", "datadate"):
                d = ymd(v)
                if d:
                    return d
    return None


def flat_list(rows):
    """平盤下得融(借)券賣出名單 → {代號: 標記}；欄位名稱含 融券／借券／跌停 且有值＝該項暫停"""
    out = {}
    for r in rows:
        c = code_of(r)
        if not c:
            continue
        m = "F"
        for k, v in r.items():
            v = str(v or "").strip()
            if not v or v in ("0", "N", "n", "否", "-") or "代號" in k or "名稱" in k or "日期" in k or k.lower() in ("date", "code", "name", "companyname", "securitiescompanycode"):
                continue
            kl = k.lower()
            if "跌停" in k or "limit" in kl:
                m += "L"
            elif "融券" in k or "margin" in kl or "shortsale" in kl:
                m += "X"
            elif "借券" in k or "sbl" in kl or "lending" in kl or "borrow" in kl:
                m += "B"
        out[c] = m
    return out


def stop_list(rows):
    """停券預告 → {代號: [起日(最後回補日), 迄日, 原因]}"""
    out = {}
    for r in rows:
        c = code_of(r)
        if not c:
            continue
        ds = [ymd(v) for k, v in r.items() if ("起" in k or "迄" in k or "回補" in k or "start" in k.lower() or "end" in k.lower()) and ymd(v)]
        why = next((str(v).strip()[:20] for k, v in r.items() if "原因" in k or "reason" in k.lower()), "")
        if ds:
            out[c] = [min(ds), max(ds), why]
    return out


def main():
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date()
    s, md = {}, None
    for back in range(0, 7):                               # 往回找最近一個有上市融資融券的交易日
        d = today - dt.timedelta(days=back)
        if d.weekday() >= 5:
            continue
        try:
            L = twse_margin(d)
        except Exception as e:
            diag["mL_err"] = str(e)[:160]
            L = None
        if not L:
            continue
        md = f"{d:%Y%m%d}"
        s.update(L)
        try:
            O = tpex_margin(d)
        except Exception as e:
            diag["mO_err"] = str(e)[:160]
            O = None
        if O:
            s.update(O)
        break
    # 平盤下名單、停券預告（OpenAPI，最新一天）
    flat, stop, fd = {}, {}, {"twse": None, "tpex": None}
    for tag, base, sw in (("twse", "https://openapi.twse.com.tw/v1", "https://openapi.twse.com.tw/v1/swagger.json"),
                          ("tpex", "https://www.tpex.org.tw/openapi/v1", "https://www.tpex.org.tw/openapi/swagger.json")):
        ps = find_paths(base, sw, tag)
        fp = [p for p, dsc in ps if "平盤" in dsc] or (["/exchangeReport/TWT92U"] if tag == "twse" else [])
        sp = [p for p, dsc in ps if "停券" in dsc or "暫停融券賣出預告" in dsc or "融券回補" in dsc] or (["/exchangeReport/BFI84U"] if tag == "twse" else [])
        for p in fp[:1]:
            rows = api(base, p, tag + "_flat")
            fl = flat_list(rows)
            flat.update(fl)
            if fl:
                fd[tag] = date_of(rows) or "?"
        for p in sp[:1]:
            stop.update(stop_list(api(base, p, tag + "_stop")))
    if not s:
        diag["fatal"] = "沒抓到融資融券"
        (OUT / "short_diag.json").write_text(json.dumps(diag, ensure_ascii=False, indent=1), "utf-8")
        print("no margin data", file=sys.stderr)
        sys.exit(1)
    res = {}
    for c, (sb, sl, dv, mb, mark) in s.items():
        m = flat.get(c, "")
        if "X" in mark.upper() and "X" not in m:           # 融資融券表註記 X＝停券
            m += "N"
        res[c] = [int(sb), int(sl) if sl is not None else None, int(dv), int(mb) if mb is not None else None, m]
    out = {"upd": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M"), "md": md, "fd": fd, "s": res, "r": stop}
    (OUT / "short.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
    diag["out"] = {"md": md, "fd": fd, "n": len(res), "flat": len(flat), "flatmarks": {k: sum(1 for v in flat.values() if k in v) for k in "FXBL"}, "stop": len(stop), "N": sum(1 for v in res.values() if "N" in v[4])}
    (OUT / "short_diag.json").write_text(json.dumps(diag, ensure_ascii=False, indent=1), "utf-8")
    print(json.dumps(diag["out"], ensure_ascii=False))


if __name__ == "__main__":
    main()
