"""除權除息預告 → data/exdiv.json（2026-11-22，📦 ETF 主題「除息提醒」用）

來源依序試（官網預告表；ETF 也在裡面）：
  上市  www.twse.com.tw/rwd/zh/exRight/TWT48U          （除權除息預告表）
        openapi.twse.com.tw/v1/exchangeReport/TWT48U_ALL（備援）
  上櫃  www.tpex.org.tw/www/zh-tw/bulletin/exRightPre    （除權除息預告）
        www.tpex.org.tw/openapi/v1/tpex_exright_prepost   （備援）
        www.tpex.org.tw/web/stock/exright/preAnnouncement/PrePost_result.php（舊版備援）
輸出 {"updated","asof","n","ev":{代號:[[除權息日YYYYMMDD, 現金股利元 或 null, 名稱]]},"src":{…},"diag":[…]}
  只留今天（含）之後的事件；股票、ETF 都收（網頁目前只用 ETF）。某來源失敗就沿用舊檔該市場的資料。
用法：python fetch_exdiv.py
"""
import json, re, time, datetime as dt, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "exdiv.json"
UA = {"User-Agent": "Mozilla/5.0 (tw-valuation; GitHub Actions)", "Accept": "application/json,text/plain,*/*"}
CODE = re.compile(r"^(\d{4}|00[0-9A-Z]{2,4})$")
DIAG = []


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
        return json.loads(r.read().decode("utf-8-sig"))


def num(v):
    try:
        x = float(str(v).replace(",", "").strip())
        return x if x > 0 else None
    except ValueError:
        return None


def ymd(v):
    dg = "".join(ch for ch in str(v) if ch.isdigit())
    if len(dg) == 7:
        dg = str(int(dg[:3]) + 1911) + dg[3:]
    return dg if len(dg) == 8 else None


def tables(js):
    """官網 rwd JSON（tables/fields/data）或 OpenAPI（list of dict）→ [(fields, rows)]"""
    out = []
    if isinstance(js, list) and js and isinstance(js[0], dict):
        fs = list(js[0].keys())
        out.append((fs, [[d.get(f) for f in fs] for d in js]))
    elif isinstance(js, dict):
        for t in js.get("tables") or []:
            if isinstance(t, dict) and t.get("data"):
                out.append((t.get("fields") or [], t["data"]))
        if isinstance(js.get("data"), list) and js["data"]:
            out.append((js.get("fields") or [], js["data"]))
        if isinstance(js.get("aaData"), list) and js["aaData"]:
            out.append((js.get("fields") or [], js["aaData"]))
    return out


def parse(js, name):
    ev = {}
    for fields, rows in tables(js):
        fs = [str(f) for f in fields]
        pick = lambda *ks: next((i for i, f in enumerate(fs) if any(k in f for k in ks)), None)
        idt, ic, inm = pick("除權除息日", "除權息日", "日期", "Date"), pick("代號", "Code"), pick("名稱", "Name")
        icash = pick("現金股利", "息值", "CashDividend")
        DIAG.append(f"{name}: 欄位 {fs[:14]} → 日期{idt} 代號{ic} 現金{icash}，{len(rows)} 列")
        if idt is None or ic is None:
            continue
        for r in rows:
            try:
                c, d = str(r[ic]).strip(), ymd(r[idt])
                if not CODE.match(c) or not d:
                    continue
                cash = num(r[icash]) if icash is not None and icash < len(r) else None
                nm = str(r[inm]).strip() if inm is not None else ""
                ev.setdefault(c, []).append([d, cash, nm])
            except Exception:
                continue
    return ev


def first_ok(name, urls):
    for u in urls:
        try:
            ev = parse(get(u), name)
            DIAG.append(f"{name}: {u[:90]} → {len(ev)} 檔")
            if ev:
                return ev, u
        except Exception as e:
            DIAG.append(f"{name}: {u[:90]} 失敗 {str(e)[:80]}")
        time.sleep(3)
    return None, None


def main():
    today = (dt.datetime.utcnow() + dt.timedelta(hours=8)).date()
    t0, t1 = f"{today:%Y%m%d}", f"{today + dt.timedelta(days=90):%Y%m%d}"
    sl = lambda d: f"{d:%Y}%2F{d:%m}%2F{d:%d}"
    old = {}
    try:
        old = json.loads(OUT.read_text("utf-8"))
    except Exception:
        pass
    L, uL = first_ok("上市", [
        f"https://www.twse.com.tw/rwd/zh/exRight/TWT48U?startDate={t0}&endDate={t1}&response=json",
        "https://www.twse.com.tw/rwd/zh/exRight/TWT48U?response=json",
        "https://openapi.twse.com.tw/v1/exchangeReport/TWT48U_ALL",
    ])
    O, uO = first_ok("上櫃", [
        f"https://www.tpex.org.tw/www/zh-tw/bulletin/exRightPre?startDate={sl(today)}&endDate={sl(today + dt.timedelta(days=90))}&response=json",
        "https://www.tpex.org.tw/www/zh-tw/bulletin/exRightPre?response=json",
        "https://www.tpex.org.tw/openapi/v1/tpex_exright_prepost",
        "https://www.tpex.org.tw/web/stock/exright/preAnnouncement/PrePost_result.php?l=zh-tw&o=json",
    ])
    src = {"L": uL, "O": uO}
    oev = old.get("ev") or {}
    ev = {}
    for part, got in (("L", L), ("O", O)):
        if got is None:                     # 這個市場沒抓到 → 沿用舊檔（用舊檔記的市場分）
            got = {c: v for c, v in oev.items() if (old.get("mkt") or {}).get(c) == part}
            src[part] = "沿用舊檔"
        for c, v in got.items():
            ev.setdefault(c, []).extend(v)
    mkt = {c: ("O" if O and c in O else "L") for c in ev}
    if not L and not O and not oev:
        print("fetch_exdiv: 都沒抓到", DIAG)
    out = {}
    for c, v in ev.items():
        seen = {}
        for d, cash, nm in v:
            if d >= t0:
                k = seen.get(d)
                if not k or (cash and not k[1]):
                    seen[d] = [d, cash, nm]
        if seen:
            out[c] = sorted(seen.values())
    res = {"updated": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"), "asof": t0, "n": len(out), "ev": out,
           "mkt": {c: mkt[c] for c in out}, "src": src, "diag": DIAG[:30]}
    OUT.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), "utf-8")
    etf = {c: v for c, v in out.items() if c.startswith("00")}
    print(f"exdiv.json: {len(out)} 檔（ETF {len(etf)}）", src)
    for x in DIAG:
        print("  ", x)


if __name__ == "__main__":
    main()
