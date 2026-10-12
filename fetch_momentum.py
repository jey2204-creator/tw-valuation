"""股價動能＋法人籌碼（主題頁「🚀 動能」模式用）→ data/momentum.json

來源（證交所／櫃買官網，可指定日期查歷史，不耗 FinMind 額度）：
  上市收盤＋成交量  www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX
  上市三大法人      www.twse.com.tw/rwd/zh/fund/T86
  上櫃收盤＋成交量  www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes（舊版 php 備援）
  上櫃三大法人      www.tpex.org.tw/www/zh-tw/insti/dailyTrade（舊版 php 備援）

每個交易日存一個檔 data/hist/YYYYMMDD.json = {"src":[已完成來源], "p":{代號:[收盤,成交股數]}, "i":{代號:[外資買賣超股數,投信買賣超股數]}}
休市日存 {"closed":1}。第一次執行會往回補約 65 個交易日（約 10 分鐘，證交所有頻率限制），之後每天只抓新的一天。

輸出 d[代號] = [週%, 月%, 季%, 量比, 外資5日(張), 投信5日(張), 外資20日(張), 投信20日(張), 投信連買天數, 外資連買天數, 🔥]
  週／月／季 = 對比 5／20／60 個交易日前的收盤（未還原除權息）
  量比 = 近 5 日均量 ÷ 近 20 日均量
  🔥 = 月% > 0、量比 ≥ 1.5、且外資或投信 5 日買超 ≥ 5 日成交量的 1%
用法：python fetch_momentum.py
"""
import json, sys, time, datetime as dt
from pathlib import Path
import urllib.request, urllib.parse

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data"
HIST = OUT / "hist"
NEED_PX, NEED_INST = 61, 20          # 季%要 60 個交易日前的收盤
KEEP = 70                            # 保留最近幾個交易日的檔案
MAX_REQ = 220                        # 單次執行請求上限（避免被證交所封鎖）
BUDGET = 15 * 60                     # 單次執行最多抓 15 分鐘，沒抓完的下次繼續
T0 = time.time()
fails = {}                           # 各來源連續失敗次數，連 3 次就本次跳過
FIELDS = ["w", "m", "q", "vr", "f5", "t5", "f20", "t20", "tS", "fS", "fire"]
UA = {"User-Agent": "Mozilla/5.0 (tw-valuation; GitHub Actions)", "Accept": "application/json,text/plain,*/*"}
diag, nreq = {}, 0
last_hit = {}


def get(url, host):
    """依網站節流：證交所每次間隔 3.5 秒、櫃買 2 秒。"""
    global nreq
    gap = 3.5 if host == "twse" else 2.0
    w = last_hit.get(host, 0) + gap - time.time()
    if w > 0:
        time.sleep(w)
    nreq += 1
    req = urllib.request.Request(url, headers=UA)
    for i in range(2):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                last_hit[host] = time.time()
                return json.loads(r.read().decode("utf-8-sig"))
        except Exception as e:
            last_hit[host] = time.time()
            if i == 1:
                raise RuntimeError(f"{e}")
            time.sleep(5)


def num(v):
    s = str(v if v is not None else "").replace(",", "").replace("+", "").strip()
    if s in ("", "-", "--", "---", "N/A"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def ok_code(c):
    c = str(c).strip()
    return c if len(c) == 4 and c.isdigit() and c[0] != "0" else None


def tables_of(js):
    """各版本 JSON 格式不同，統一成 [(fields, rows)]"""
    out = []
    if isinstance(js, dict):
        for t in js.get("tables") or []:
            if isinstance(t, dict) and t.get("data"):
                out.append((t.get("fields") or [], t["data"]))
        if js.get("data") and isinstance(js["data"], list):
            out.append((js.get("fields") or [], js["data"]))
        for k, v in js.items():                      # 舊版 MI_INDEX：fields9 / data9
            if k.startswith("data") and k[4:].isdigit() and v:
                out.append((js.get("fields" + k[4:]) or [], v))
        if js.get("aaData"):
            out.append(([], js["aaData"]))
    return out


def col(fields, *must, prefer=None, avoid=None):
    hit = [i for i, f in enumerate(fields) if all(m in str(f) for m in must) and not (avoid and avoid in str(f))]
    if prefer:
        p = [i for i in hit if prefer in str(fields[i])]
        if p:
            return p[0]
    return hit[0] if hit else None


def note(name, js, fields, n):
    d = diag.setdefault(name, {})
    d["rows"] = n
    if fields:
        d["fields"] = [str(f) for f in fields][:20]
    if isinstance(js, dict):
        d["stat"] = str(js.get("stat", js.get("status", "")))[:40]


# ---------- 四個來源：回傳 {代號: [...]}；回傳 None = 當天沒資料（休市或尚未公布） ----------
def twse_px(d):
    js = get(f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={d:%Y%m%d}&type=ALLBUT0999&response=json", "twse")
    for fields, rows in tables_of(js):
        ic, ip, iv = col(fields, "證券代號"), col(fields, "收盤價"), col(fields, "成交股數")
        if ic is None or ip is None or iv is None:
            continue
        out = {}
        for r in rows:
            c = ok_code(r[ic])
            if c:
                out[c] = [num(r[ip]), num(r[iv])]
        note("pL", js, fields, len(out))
        return out or None
    note("pL", js, [], 0)
    return None


def resp_date(js):
    """回應裡的資料日期 → date；找不到回 None。舊版 php 會忽略日期參數、永遠回傳最新一天，要靠這個擋掉。"""
    if not isinstance(js, dict):
        return None
    cands = [js.get(k) for k in ("date", "reportDate", "Date")]
    cands += [t.get("date") for t in (js.get("tables") or []) if isinstance(t, dict)]
    for v in cands:
        dg = "".join(ch for ch in str(v or "") if ch.isdigit())
        try:
            if len(dg) == 8:
                return dt.date(int(dg[:4]), int(dg[4:6]), int(dg[6:]))
            if len(dg) == 7:                                   # 民國 1150901
                return dt.date(int(dg[:3]) + 1911, int(dg[3:5]), int(dg[5:]))
        except ValueError:
            pass
    return None


def tpex_px(d):
    roc = f"{d.year - 1911}/{d:%m/%d}"
    urls = [f"https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes?date={d:%Y}%2F{d:%m}%2F{d:%d}&id=&response=json",
            f"https://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/stk_quote_result.php?l=zh-tw&o=json&d={urllib.parse.quote(roc)}"]
    err = None
    for u in urls:
        try:
            js = get(u, "tpex")
        except Exception as e:
            err = e
            continue
        rd = resp_date(js)
        diag.setdefault("pO_dates", []).append(f"{d:%m%d}->{rd:%m%d}" if rd else f"{d:%m%d}->?")
        if rd != d:                                   # 日期對不上（或沒有日期）就不採用
            continue
        for fields, rows in tables_of(js):
            if fields:
                ic, ip, iv = col(fields, "代號"), col(fields, "收盤"), col(fields, "成交股數")
            else:                                     # 舊版 aaData：代號,名稱,收盤,漲跌,開,高,低,均價,成交股數
                ic, ip, iv = 0, 2, 8
            if ic is None or ip is None or iv is None:
                continue
            out = {}
            for r in rows:
                c = ok_code(r[ic])
                if c:
                    out[c] = [num(r[ip]), num(r[iv])]
            if out:
                note("pO", js, fields, len(out))
                diag["pO"]["url"] = u.split("?")[0][-40:]
                return out
        note("pO", js, [], 0)
    if err:
        raise err
    return None


def twse_inst(d):
    js = get(f"https://www.twse.com.tw/rwd/zh/fund/T86?date={d:%Y%m%d}&selectType=ALLBUT0999&response=json", "twse")
    for fields, rows in tables_of(js):
        ic = col(fields, "證券代號")
        jf = col(fields, "外", "買賣超", prefer="不含")
        jt = col(fields, "投信", "買賣超")
        if None in (ic, jf, jt):
            continue
        out = {}
        for r in rows:
            c = ok_code(r[ic])
            if c:
                out[c] = [num(r[jf]) or 0, num(r[jt]) or 0]
        note("iL", js, fields, len(out))
        return out or None
    note("iL", js, [], 0)
    return None


def tpex_inst(d):
    roc = f"{d.year - 1911}/{d:%m/%d}"
    urls = [f"https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade?type=Daily&sect=EW&date={d:%Y}%2F{d:%m}%2F{d:%d}&response=json",
            f"https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&o=json&se=EW&t=D&d={urllib.parse.quote(roc)}"]
    err = None
    for u in urls:
        try:
            js = get(u, "tpex")
        except Exception as e:
            err = e
            continue
        rd = resp_date(js)
        if rd is not None and rd != d:
            continue
        for fields, rows in tables_of(js):
            if fields and col(fields, "投信") is not None:
                ic = col(fields, "代號")
                jf = col(fields, "外", "買賣超", prefer="不含")
                jt = col(fields, "投信", "買賣超")
            else:                                     # 新版欄名只寫「買賣超股數」：外資(不含自營)=4、投信=13
                if fields and len(fields) < 24:
                    continue                                     # 舊版：外資(不含自營)買賣超=4、投信買賣超=13
                ic, jf, jt = 0, 4, 13
            if None in (ic, jf, jt):
                continue
            out = {}
            for r in rows:
                c = ok_code(r[ic])
                if c and len(r) > max(jf, jt):
                    out[c] = [num(r[jf]) or 0, num(r[jt]) or 0]
            if out:
                note("iO", js, fields, len(out))
                diag["iO"]["url"] = u.split("?")[0][-40:]
                return out
        note("iO", js, [], 0)
    if err:
        raise err
    return None


SOURCES = {"pL": (twse_px, "p"), "pO": (tpex_px, "p"), "iL": (twse_inst, "i"), "iO": (tpex_inst, "i")}


def load_day(d):
    f = HIST / f"{d:%Y%m%d}.json"
    if f.exists():
        try:
            return json.loads(f.read_text("utf-8"))
        except Exception:
            pass
    return {}


def save_day(d, rec):
    HIST.mkdir(parents=True, exist_ok=True)
    (HIST / f"{d:%Y%m%d}.json").write_text(json.dumps(rec, ensure_ascii=False, separators=(",", ":")), "utf-8")


def tw_today():
    now = dt.datetime.utcnow() + dt.timedelta(hours=8)
    # 收盤資料約 14:30 後才有；法人約 16:00 後
    return now.date(), now.hour


def collect():
    today, hour = tw_today()
    need = {"pL": NEED_PX, "pO": NEED_PX, "iL": NEED_INST, "iO": NEED_INST}
    have = {k: 0 for k in need}
    errs = []
    d = today
    for _ in range(130):                      # 最多往回看 130 天
        if all(have[k] >= need[k] for k in need):
            break
        if d.weekday() >= 5:
            d -= dt.timedelta(days=1)
            continue
        if d == today and hour < 15:
            d -= dt.timedelta(days=1)
            continue
        rec = load_day(d)
        if rec.get("closed"):
            d -= dt.timedelta(days=1)
            continue
        src = set(rec.get("src", []))
        want = [k for k in ("pL", "pO", "iL", "iO") if k not in src and have[k] < need[k]]
        changed = False
        for k in want:
            if nreq >= MAX_REQ or time.time() - T0 > BUDGET or fails.get(k, 0) >= 3:
                continue
            fn, slot = SOURCES[k]
            try:
                r = fn(d)
            except Exception as e:
                fails[k] = fails.get(k, 0) + 1
                errs.append(f"{d:%m/%d} {k}: {str(e)[:80]}")
                continue
            fails[k] = 0
            if r is None:
                if k == "pL" and d < today and not rec.get("p"):   # 過去的平日證交所沒資料 = 休市
                    rec = {"closed": 1}
                    changed = True
                    break
                if k != "pL" and d < today:              # 交易日卻沒資料 = 這個來源有問題
                    fails[k] = fails.get(k, 0) + 1
                    errs.append(f"{d:%m/%d} {k}: 無資料或日期不符")
                continue
            rec.setdefault(slot, {}).update(r)
            src.add(k)
            rec["src"] = sorted(src)
            changed = True
        if changed:
            save_day(d, rec)
        if not rec.get("closed"):
            for k in need:
                if k in src:
                    have[k] += 1
        if nreq >= MAX_REQ or time.time() - T0 > BUDGET:
            errs.append(f"達到單次上限（{nreq} 次請求／{int(time.time() - T0)} 秒），下次執行繼續回補")
            break
        if all(fails.get(k, 0) >= 3 for k in ("pL", "iL")):
            errs.append("證交所連續失敗，本次停止")
            break
        d -= dt.timedelta(days=1)
    return errs


def prune():
    files = sorted(HIST.glob("*.json"))
    trade = [f for f in files if '"closed"' not in f.read_text("utf-8")[:20]]
    keep = set(trade[-KEEP:])
    cut = (dt.date.today() - dt.timedelta(days=150)).strftime("%Y%m%d")
    for f in files:
        if f not in keep and (f in trade or f.stem < cut):
            f.unlink()


def compute():
    days = []
    for f in sorted(HIST.glob("*.json")):
        rec = json.loads(f.read_text("utf-8"))
        if not rec.get("closed") and rec.get("p"):
            days.append((f.stem, rec))
    pdays = [x for x in days if "pL" in x[1].get("src", [])]
    idays = [x for x in days if "iL" in x[1].get("src", []) and x[1].get("i")]
    ids = sorted({c for _, r in pdays[-5:] for c in r["p"]})
    out = {}

    def ret(cl, n):
        """收盤對比 n 個交易日前；當天沒成交就往前找最近一筆"""
        if len(cl) <= n or cl[-1] is None:
            return None
        base = next((x for x in reversed(cl[:len(cl) - n]) if x), None)
        return round((cl[-1] / base - 1) * 100, 1) if base else None

    for c in ids:
        cl = [r["p"].get(c, [None, None])[0] for _, r in pdays]
        vo = [r["p"].get(c, [None, None])[1] for _, r in pdays]
        w, m, q = ret(cl, 5), ret(cl, 20), ret(cl, 60)
        v5 = [x for x in vo[-5:] if x is not None]
        v20 = [x for x in vo[-20:] if x is not None]
        vr = round((sum(v5) / len(v5)) / (sum(v20) / len(v20)), 2) if v5 and v20 and sum(v20) > 0 else None
        # 某天櫃買法人沒抓到時，上櫃股那天不計（避免當成 0）
        iv = [r["i"][c] if c in r["i"] else [0, 0] for _, r in idays
              if c in r["i"] or {"iL", "iO"} <= set(r.get("src", []))]
        fi = [x[0] for x in iv]
        ti = [x[1] for x in iv]
        has_i = bool(iv)
        f5, t5 = sum(fi[-5:]), sum(ti[-5:])
        f20, t20 = sum(fi[-20:]), sum(ti[-20:])

        def streak(a):
            n = 0
            for x in reversed(a):
                if x > 0:
                    n += 1
                else:
                    break
            return n
        vol5 = sum(v5) if v5 else 0
        big = vol5 > 0 and max(f5, t5) >= vol5 * 0.01
        fire = 1 if (m is not None and m > 0 and vr is not None and vr >= 1.5 and big) else 0
        k = lambda x: round(x / 1000)       # 股 → 張
        if all(x is None for x in (w, m, q, vr)) and not idays:
            continue
        if has_i:
            out[c] = [w, m, q, vr, k(f5), k(t5), k(f20), k(t20), streak(ti), streak(fi), fire]
        else:                                # 沒有法人資料 → 顯示「—」而不是 0
            out[c] = [w, m, q, vr, None, None, None, None, None, None, 0]
    return out, pdays, idays


def main():
    OUT.mkdir(exist_ok=True)
    errs = collect()
    try:
        prune()
    except Exception as e:
        errs.append(f"prune: {e}")
    d, pdays, idays = compute()
    if not d:
        print("沒有任何資料，不輸出", file=sys.stderr)
        print(json.dumps({"errors": errs, "diag": diag}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    res = dict(updated=dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
               asof=pdays[-1][0] if pdays else None, instAsof=idays[-1][0] if idays else None,
               nPx=len(pdays), nInst=len(idays), firstPx=pdays[0][0] if pdays else None,
               fields=FIELDS, req=nreq, secs=int(time.time() - T0), fails=fails, errors=errs[:30], diag={k: (v[:12] if isinstance(v, list) and k.endswith("_dates") else v) for k, v in diag.items()}, d=d)
    (OUT / "momentum.json").write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"momentum.json: {len(d)} 檔，股價 {len(pdays)} 天、法人 {len(idays)} 天，請求 {nreq} 次，錯誤 {len(errs)}")


if __name__ == "__main__":
    main()
