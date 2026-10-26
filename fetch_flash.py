"""財報快訊 → data/flash.json（beta.html 用）

來源：觀測站新版 API（GitHub Actions 連得到；雲端對話環境連不到）
  POST https://mops.twse.com.tw/mops/api/t05st02          {"year":"115","month":"10","day":"26"} → 當日重大訊息清單
  POST https://mops.twse.com.tw/mops/api/t05st02_detail   清單每列最後一格附的 parameters → 說明全文
  ⚠️ 用日期查清單時，前一天傍晚的訊息也可能歸在隔天 → 每次查今天＋昨天，用 (代號, enterDate, serialNumber) 去重

只抓兩種重訊（符合條款第 31 款的標準格式）：
  ① 董事會通過財報：說明內有「報導期間 115/01/01~115/09/30」與 1 月 1 日累計的營收／毛利／營益／稅前／
     本期淨利／歸母淨利／EPS（仟元、元）→ 用 data/health/q/ 的 MOPS 累計數換算單季、年增、季增
  ② 財報董事會召開日期：說明內有「董事會預計召開日期:115/11/03」→ 公布日曆
另收主旨含「每股盈餘」的自行公告（例：台積電法說當天 15:12「2026年第二季每股盈餘新台幣27.25元」）→ 只取 EPS

原始明細存 data/flash/raw.json（同一則不重抓，保留 200 天），每次由 raw 重算 flash.json
推播：設 Secret TELEGRAM_TOKEN 才會送（Telegram 機器人；chat id 自動抓，存 data/flash/tg.json），只送追蹤股（fetch.py STOCKS＋themes.json 成份股＋data/flash_watch.json）
      且發言時間在 6 小時內的新公告，避免回補時洗版
環境變數：BACKFILL_FROM=YYYY-MM-DD（回補起日）、BUDGET_MIN（時間預算，預設 12 分）、GAP（每次請求間隔秒，預設 0.9）
"""
import json, os, re, time, datetime as dt, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RAW = DATA / "flash" / "raw.json"
OUT = DATA / "flash.json"
API = "https://mops.twse.com.tw/mops/api/"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
TZ = dt.timezone(dt.timedelta(hours=8))
NOW = dt.datetime.now(TZ)
T0 = time.time()
BUDGET = float(os.environ.get("BUDGET_MIN") or 12) * 60
GAP = float(os.environ.get("GAP") or 0.9)
DIAG = {"req": 0, "fail": [], "days": {}, "newDetail": 0, "parsed": 0, "notified": 0, "stop": None}

FIN = re.compile(r"財務報告|財務報表|財報|每股盈餘|自結")
SKIP = re.compile(r"法人說明會|法說會|補正|背書|資金貸與|主管|異動|注意交易|應收帳款|負債比率|淨值百分|淨值\d|盈餘分配|分派|除息|股利|iXBRL|附註|"
                  r"代子公司|代重要子公司|更正|重新核閱|會計師|現金餘額|月份?自結|\d{1,2}月(份)?(自結|合併)|理財|取得|處分")
CAL = re.compile(r"召開|預計|召集|提報董事會|提請董事會|將提|董事會(決議)?日期")


# ---------------------------------------------------------------- 請求
def post(ep, body):
    if time.time() - T0 > BUDGET:
        DIAG["stop"] = DIAG["stop"] or f"超過時間預算 {BUDGET/60:.0f} 分"
        return None
    for i in range(3):
        time.sleep(GAP)
        DIAG["req"] += 1
        r = urllib.request.Request(API + ep, data=json.dumps(body).encode(), headers={
            "User-Agent": UA, "Content-Type": "application/json", "Accept": "application/json",
            "Referer": "https://mops.twse.com.tw/mops/"})
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                j = json.loads(resp.read().decode("utf-8", "replace"))
            if j.get("code") == 200:
                return j.get("result") or {}
            err = f"code {j.get('code')} {j.get('message')}"
            if "頻繁" in str(j.get("message")):
                time.sleep(20)
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
        time.sleep(3 * (i + 1))
    DIAG["fail"].append(f"{ep} {json.dumps(body, ensure_ascii=False)[:90]} → {err}")
    return None


def load(p, default):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default


# ---------------------------------------------------------------- 解析
def num(s):
    s = (s or "").strip().replace(",", "").replace(" ", "")
    neg = s.startswith("(") and s.endswith(")") or s.startswith("-") or s.startswith("－")
    s = s.strip("()-－")
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


VAL = re.compile(r"[:：]\s*(?:NT\$|新[台臺]幣)?\s*(\(?[-－]?[\d,]+(?:\.\d+)?\)?)\s*(?:元|仟元|千元)?\s*$")
PERIOD = re.compile(r"(\d{2,4})/(\d{1,2})/(\d{1,2})\s*[~～\-至]\s*(\d{2,4})/(\d{1,2})/(\d{1,2})")


def parse_report(txt):
    """標準格式（第 31 款）→ {y, n, rev, gp, op, pre, np, ni, eps}；不是財報格式回傳 None"""
    flat = re.sub(r"\s*\n\s*", "", txt)          # 有些公司把標籤斷成兩行
    m = PERIOD.search(flat)
    if not m:
        return None
    y1, mo1, y2, mo2 = int(m.group(1)), int(m.group(2)), int(m.group(4)), int(m.group(5))
    y = y2 + 1911 if y2 < 1000 else y2
    if mo1 != 1 or mo2 not in (3, 6, 9, 12):
        return {"y": y, "n": None, "bad": f"期間 {m.group(0)}"}
    out = {"y": y, "n": mo2 // 3}
    lines = re.split(r"\n(?=\s*\d{1,2}\s*[.．、])", txt)
    for ln in lines:
        one = re.sub(r"\s+", "", ln)
        v = VAL.search(one)
        if not v:
            continue
        val = num(v.group(1))
        lab = one[:v.start()]
        if "總資產" in lab or "總負債" in lab or "權益" in lab and "淨利" not in lab:
            continue
        if "每股盈餘" in lab:
            k = "eps"
        elif "歸屬於母公司" in lab:
            k = "ni"
        elif "稅前" in lab:
            k = "pre"
        elif "本期淨利" in lab or "本期稅後淨利" in lab:
            k = "np"
        elif "營業利益" in lab:
            k = "op"
        elif "營業毛利" in lab:
            k = "gp"
        elif "營業收入" in lab or (lab.endswith("淨收益(仟元)") and "利息" not in lab):
            k = "rev"
        else:
            continue
        out.setdefault(k, val)
    if out.get("ni") is None and out.get("np") is not None:
        out["ni"] = out["np"]
    return out if (out.get("ni") is not None or out.get("eps") is not None) else {"y": y, "n": out["n"], "bad": "找不到淨利"}


ROCD = re.compile(r"(\d{3})\s*[/年]\s*(\d{1,2})\s*[/月]\s*(\d{1,2})")


def parse_cal(subj, txt):
    m = re.search(r"預計召開日期[^\d]{0,6}(\d{3})/(\d{1,2})/(\d{1,2})", re.sub(r"\s+", "", txt or ""))
    if not m:
        m = re.search(r"(?:召開|預計)[^\d]{0,12}(\d{3})\s*[/年]\s*(\d{1,2})\s*[/月]\s*(\d{1,2})", subj + (txt or ""))
    if not m:
        return None
    try:
        d = dt.date(int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None
    q = None
    mq = re.search(r"(\d{3,4})年(?:度)?(?:第([一二三四1-4])季|(上半年)|(年度|全年))", subj + (txt or ""))
    if mq:
        yy = int(mq.group(1)); yy = yy + 1911 if yy < 1000 else yy
        n = mq.group(2)
        n = {"一": 1, "二": 2, "三": 3, "四": 4}.get(n, n) if n else (2 if mq.group(3) else 4)
        q = f"{yy}Q{int(n)}"
    return {"d": d.isoformat(), "q": q}


CN = {"一": 1, "二": 2, "三": 3, "四": 4}


def parse_self(subj, txt):
    """董事會前的自行公告：法說 EPS（台積電）、季度自結損益（台塑四寶等）。只收單季（主旨要有第 X 季）"""
    mq = re.search(r"(\d{3,4})年(?:度)?(?:第([一二三四1-4])季|Q([1-4]))", subj)
    if not mq or re.search(r"\d{1,2}月份?(?:及|自結|合併)", subj) and "季" not in subj:
        return None
    if not re.search(r"每股盈餘|EPS|自結|損益|營運|財務", subj):
        return None
    yy = int(mq.group(1)); yy = yy + 1911 if yy < 1000 else yy
    n = int(CN.get(mq.group(2), mq.group(2) or mq.group(3)))
    body = subj + "。" + re.sub(r"\s+", " ", txt or "")      # 保留空白：表格欄位才分得開
    if "人民幣" in body or "美元" in body:                 # KY 公司常先列外幣表、再列新台幣表 → 只看新台幣段
        i = max(body.rfind("(新台幣)"), body.rfind("(新臺幣)"), body.rfind("新台幣表"), body.rfind("（新台幣）"))
        if i > 0:
            body = subj + "。" + body[i:]
    eps = None
    N = r"([-－(（]?\d+\.\d+)"
    G = r"[為約:：\s]{0,4}(?:新[台臺]幣\s?)?"
    for pat in (r"單季\s?(?:稅後)?\s?(?:EPS|每股(?:稅後)?盈餘)[^\d\-－(（]{0,8}" + N,
                r"(?<!稅前)(?:每股稅後盈餘|稅後每股盈餘|稅後\s?EPS|EPS|每股盈餘)" + G + N + r"\s?元",
                r"(?:每股稅後盈餘|稅後每股盈餘|稅後\s?EPS|每股盈餘\(?稅後\)?)" + G + N,
                r"(?<!稅前)(?:基本)?(?:EPS|每股盈餘)(?:\(虧損\))?(?:\(元\))?" + G + N):
        m = re.search(pat, body)
        if m:
            eps = num(m.group(1).replace("（", "(").replace("－", "-"))
            break
    if eps is None:
        return None
    ytd = ("累計" in subj or (re.search(r"上半年|前三季", subj) and not re.search(r"第[一二三四1-4]季", subj))) \
        and not re.search(r"單季", body)
    return {"y": yy, "n": n, "eps": eps, "single": not ytd}


# ---------------------------------------------------------------- 抓清單＋明細
def fetch_day(d, raw):
    old = d < NOW.date() - dt.timedelta(days=40)
    res = post("t05st02", {"year": str(d.year - 1911), "month": f"{d.month:02d}", "day": f"{d.day:02d}"})
    if res is None:
        return False
    rows = res.get("data") or []
    hit = 0
    for r in rows:
        try:
            date, tm, code, name, subj, link = r[0], r[1], r[2], r[3], re.sub(r"\s+", "", r[4]), r[5]
        except Exception:
            continue
        p = (link or {}).get("parameters") or {}
        if not re.fullmatch(r"\d{4}", str(code)) or not FIN.search(subj) or SKIP.search(subj):
            continue
        if p.get("marketKind") not in ("sii", "otc"):
            continue
        key = f"{code}_{p.get('enterDate')}_{p.get('serialNumber')}"
        if old and CAL.search(subj) and "通過" not in subj:
            continue                                   # 回補時過期的董事會日期不必抓
        hit += 1
        if key in raw:
            continue
        det = post((link or {}).get("apiName") or "t05st02_detail", p)
        if det is None:
            if DIAG["stop"]:
                break
            continue
        rec = (det.get("data") or [[None] * 10])[0]
        raw[key] = {"c": code, "nm": name, "mk": p.get("marketKind"), "d": date, "tm": tm, "subj": subj,
                    "cl": str(rec[7]) if len(rec) > 7 else None, "txt": rec[9] if len(rec) > 9 else "",
                    "got": NOW.isoformat(timespec="minutes")}
        DIAG["newDetail"] += 1
    DIAG["days"][d.isoformat()] = {"rows": len(rows), "fin": hit}
    return True


# ---------------------------------------------------------------- 計算
QCACHE = {}


def hq(y, n):
    """MOPS 累計數：{代號: [市場, 歸母淨利千, 稅前千, 營收百萬, EPS]}"""
    if n == 0:
        y, n = y - 1, 4
    k = (y, n)
    if k not in QCACHE:
        QCACHE[k] = (load(DATA / "health" / "q" / f"{y}Q{n}.json", {}) or {}).get("d") or {}
    return QCACHE[k]


def prev_ytd(code, y, n, ann):
    """(y, n) 的累計數；優先用自己存的重訊（有毛利、營益），沒有再用 MOPS 彙總"""
    if n == 0:
        return {"ni": 0, "eps": 0, "rev": 0, "pre": 0, "gp": 0, "op": 0}   # 第 1 季前一期累計＝0
    a = ann.get((code, y, n))
    if a:
        return a
    h = hq(y, n).get(code)
    if h:
        return {"ni": h[1], "pre": h[2], "rev": h[3] * 1000 if h[3] is not None else None, "eps": h[4]}
    return None


def sub(a, b, k):
    if a is None or b is None or a.get(k) is None or b.get(k) is None:
        return None
    return a[k] - b[k]


def single(code, y, n, ann, cur=None):
    """單季：累計(y,n) − 累計(y,n−1)"""
    c = cur or prev_ytd(code, y, n, ann)
    p = prev_ytd(code, y, n - 1, ann)
    if c is None or p is None:
        return None
    o = {k: sub(c, p, k) for k in ("rev", "gp", "op", "pre", "ni", "eps")}
    if o["eps"] is not None:
        o["eps"] = round(o["eps"], 2)
    return o


def growth(cur, prev):
    """回傳 (年增%, 標籤)"""
    if cur is None or prev is None:
        return None, None
    if prev <= 0:
        return None, ("轉盈" if cur > 0 else "虧損")
    if cur <= 0:
        return None, "轉虧"
    g = (cur / prev - 1) * 100
    return round(g, 1), (">+300%" if g > 300 else None)


def pct(a, b):
    return round(a / b * 100, 1) if a is not None and b not in (None, 0) else None


def ttm_pe(code, y, n, ytd_eps, ann, sd):
    """近四季 EPS＝今年累計＋(去年全年 − 去年同期累計)；本益比用 summary.json 收盤"""
    close = (sd.get(code) or [None])[0]
    if ytd_eps is None:
        return None, None, close
    if n == 4:
        ttm = ytd_eps
    else:
        fy, ly = prev_ytd(code, y - 1, 4, ann), prev_ytd(code, y - 1, n, ann)
        if not fy or not ly or fy.get("eps") is None or ly.get("eps") is None:
            return None, None, close
        ttm = ytd_eps + fy["eps"] - ly["eps"]
    ttm = round(ttm, 2)
    pe = round(close / ttm, 1) if close and ttm > 0.01 else None
    return ttm, pe, close


def build(raw):
    names = {r[0]: r[1] for r in load(DATA / "list.json", [])}
    summ = load(DATA / "summary.json", {})
    sd, se = summ.get("d") or {}, summ.get("eps") or {}
    ann, items, cal, selfs = {}, [], {}, []
    for key, r in sorted(raw.items(), key=lambda kv: (kv[1]["d"], kv[1]["tm"])):
        rep = parse_report(r.get("txt") or "") if r.get("cl") in ("31", None) or "每股盈餘" in (r.get("txt") or "") else None
        if rep and rep.get("n") and not rep.get("bad"):
            rep["key"], rep["r"] = key, r
            ann[(r["c"], rep["y"], rep["n"])] = rep          # 同季多則（例：更正）以最後一則為準
            continue
        if (CAL.search(r["subj"]) or "預計召開日期" in (r.get("txt") or "")) and "董事會" in (r["subj"] + (r.get("txt") or ""))[:400]:
            c = parse_cal(r["subj"], r.get("txt"))
            if c:
                cal[(r["c"], c["q"])] = {"c": r["c"], "n": names.get(r["c"], r["nm"]), "d": c["d"], "q": c["q"],
                                         "mk": 0 if r["mk"] == "sii" else 1}
            continue
        s = parse_self(r["subj"], r.get("txt"))
        if s:
            s["r"], s["key"] = r, key
            selfs.append(s)

    for (code, y, n), a in ann.items():
        r = a["r"]
        s = single(code, y, n, ann, cur=a) or {}
        ly = single(code, y - 1, n, ann) or {}
        pq = single(code, y, n - 1, ann) if n > 1 else single(code, y - 1, 4, ann)
        pq = pq or {}
        lyy = prev_ytd(code, y - 1, n, ann) or {}
        g_ni, t_ni = growth(s.get("ni"), ly.get("ni"))
        g_eps, t_eps = growth(s.get("eps"), ly.get("eps"))
        q_ni, tq_ni = growth(s.get("ni"), pq.get("ni"))
        y_ni, ty_ni = growth(a.get("ni"), lyy.get("ni"))
        # 業外占比：單季算得出來用單季，否則用累計
        if s.get("op") is not None and s.get("pre") is not None and s["pre"] > 0:
            nonop, nonop_src = pct(s["pre"] - s["op"], s["pre"]), "單季"
        elif a.get("op") is not None and a.get("pre") is not None and a["pre"] > 0:
            nonop, nonop_src = pct(a["pre"] - a["op"], a["pre"]), "累計"
        else:
            nonop, nonop_src = None, None
        rev_s = s.get("rev")
        margin_src = "單季" if s.get("gp") is not None and rev_s else "累計"
        base = s if margin_src == "單季" else a
        gm = pct(base.get("gp"), base.get("rev"))
        om = pct(base.get("op"), base.get("rev"))
        nm = pct(s.get("ni"), rev_s) if rev_s else pct(a.get("ni"), a.get("rev"))
        ttm, pe, close = ttm_pe(code, y, n, a.get("eps"), ann, sd)
        items.append({
            "c": code, "n": names.get(code, r["nm"]), "mk": 0 if r["mk"] == "sii" else 1,
            "t": f"{r['d']} {r['tm'][:5]}", "q": f"{y}Q{n}", "k": "board", "subj": r["subj"][:60],
            "s": {k: (round(v / 1e5, 2) if k in ("rev", "gp", "op", "pre", "ni") and v is not None else v)
                  for k, v in s.items()},                                # 金額單位：億元
            "ly": {"ni": round(ly["ni"] / 1e5, 2) if ly.get("ni") is not None else None, "eps": ly.get("eps")},
            "pq": {"ni": round(pq["ni"] / 1e5, 2) if pq.get("ni") is not None else None, "eps": pq.get("eps")},
            "ytd": {"ni": round(a["ni"] / 1e5, 2) if a.get("ni") is not None else None, "eps": a.get("eps"),
                    "rev": round(a["rev"] / 1e5, 2) if a.get("rev") is not None else None},
            "yoy": g_ni, "yoyT": t_ni, "epsYoy": g_eps, "epsYoyT": t_eps, "qoq": q_ni, "qoqT": tq_ni,
            "ytdYoy": y_ni, "ytdYoyT": ty_ni,
            "gm": gm, "om": om, "nm": nm, "mSrc": margin_src, "nonop": nonop, "nonopSrc": nonop_src,
            "ttm": ttm, "pe": pe, "close": close,
        })
    for s in selfs:
        r = s["r"]
        q = f"{s['y']}Q{s['n']}"
        if (r["c"], s["y"], s["n"]) in ann:
            continue                                                   # 董事會版已出，以董事會版為準
        if not s["single"]:                                            # 累計數 → 扣掉上一季累計
            p = prev_ytd(r["c"], s["y"], s["n"] - 1, ann)
            if p is None or p.get("eps") is None:
                continue
            s["eps"] = round(s["eps"] - p["eps"], 2)
        ly = single(r["c"], s["y"] - 1, s["n"], ann) or {}
        g, t = growth(s["eps"], ly.get("eps"))
        p = prev_ytd(r["c"], s["y"], s["n"] - 1, ann)
        ttm, pe, close = ttm_pe(r["c"], s["y"], s["n"], (p["eps"] + s["eps"]) if p and p.get("eps") is not None else None, ann, sd)
        items.append({"c": r["c"], "ttm": ttm, "pe": pe, "close": close, "n": names.get(r["c"], r["nm"]), "mk": 0 if r["mk"] == "sii" else 1,
                      "t": f"{r['d']} {r['tm'][:5]}", "q": q, "k": "self", "subj": r["subj"][:60],
                      "s": {"eps": s["eps"]}, "ly": {"eps": ly.get("eps")}, "epsYoy": g, "epsYoyT": t})
    # 已公布的不再列在日曆
    done = {(i["c"], i["q"]) for i in items}
    today = NOW.date().isoformat()
    cal = [v for v in cal.values() if (v["c"], v["q"]) not in done and v["d"] >= (NOW.date() - dt.timedelta(days=3)).isoformat()]
    cal.sort(key=lambda v: (v["d"], v["c"]))
    items.sort(key=lambda i: i["t"], reverse=True)
    DIAG["parsed"] = len(items)
    cnt = {}
    for i in items:
        cnt[i["q"]] = cnt.get(i["q"], 0) + 1
    seasons = sorted((q for q, n in cnt.items() if n >= 5), reverse=True)
    return {"updated": NOW.isoformat(timespec="minutes"), "today": today, "seasons": seasons, "unit": "億元",
            "items": items, "cal": cal, "diag": DIAG}


# ---------------------------------------------------------------- 推播（選用）
SITE = "https://jey2204-creator.github.io/tw-valuation/"


def tg(method, payload=None):
    tok = os.environ.get("TELEGRAM_TOKEN")
    r = urllib.request.Request(f"https://api.telegram.org/bot{tok}/{method}",
                               data=json.dumps(payload or {}).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"ok": False, "description": f"HTTP {e.code}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "description": str(e)}


def tg_chat():
    """chat id：Secret TELEGRAM_CHAT_ID → data/flash/tg.json → getUpdates（使用者對機器人按「開始」後 24 小時內抓得到）"""
    c = os.environ.get("TELEGRAM_CHAT_ID")
    if c:
        return c, False
    saved = load(DATA / "flash" / "tg.json", {}).get("chat")
    if saved:
        return saved, False
    j = tg("getUpdates", {"allowed_updates": ["message"]})
    chats = [u["message"]["chat"]["id"] for u in (j.get("result") or []) if (u.get("message") or {}).get("chat", {}).get("type") == "private"]
    if not chats:
        DIAG["tg"] = "還沒有人對機器人按「開始」：" + str(j.get("description") or "getUpdates 空的")
        return None, False
    (DATA / "flash" / "tg.json").write_text(json.dumps({"chat": chats[-1]}))
    return chats[-1], True


def watch_codes():
    watch = set(load(DATA / "flash_watch.json", []))
    try:
        watch |= set(re.findall(r'"(\d{4})"', re.search(r"STOCKS\s*=\s*\[[^\]]*\]", (ROOT / "fetch.py").read_text()).group(0)))
    except Exception:
        pass
    for t in (load(DATA / "themes.json", {}).get("themes") or []):
        watch |= {s[0] for s in t.get("stocks") or []}
    return watch


def esc(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def gtxt(v, t):
    if t:
        return t
    return "—" if v is None else f"{v:+.0f}%"


def card(i):
    s = i.get("s") or {}
    kind = "法說／自結" if i["k"] == "self" else "董事會財報"
    e = s.get("eps")
    arrow = "🔴" if (i.get("epsYoy") or 0) > 0 or i.get("epsYoyT") == "轉盈" or i.get("epsYoyT") == ">+300%" else \
            "🟢" if (i.get("epsYoy") or 0) < 0 or i.get("epsYoyT") in ("轉虧", "虧損") else "⚪"
    L = [f"{arrow} <b>{esc(i['c'])} {esc(i['n'])}</b>　{i['q'][2:]} {kind}",
         f"EPS <b>{e if e is not None else '—'}</b> 元（年增 {gtxt(i.get('epsYoy'), i.get('epsYoyT'))}・去年 {(i.get('ly') or {}).get('eps', '—')}）"]
    if s.get("ni") is not None:
        L.append(f"淨利 {s['ni']:,.1f} 億（年增 {gtxt(i.get('yoy'), i.get('yoyT'))}・季增 {gtxt(i.get('qoq'), i.get('qoqT'))}）")
    m = []
    if i.get("gm") is not None:
        m.append(f"毛 {i['gm']:.1f}%")
    if i.get("om") is not None:
        m.append(f"營 {i['om']:.1f}%")
    if i.get("nonop") is not None:
        m.append(("⚠️ " if i["nonop"] >= 30 else "") + f"業外 {i['nonop']:.0f}%")
    if m:
        L.append("・".join(m))
    if i.get("ttm") is not None:
        L.append(f"近四季 EPS {i['ttm']}" + (f" → 本益比 {i['pe']}" if i.get("pe") else ""))
    L.append(f'<a href="{SITE}#{i["c"]}">個股頁</a>　<a href="{SITE}flash.html">快訊</a>')
    return "\n".join(L)


def notify(out, raw):
    """Telegram 推播（設了 Secret TELEGRAM_TOKEN 才會送）：追蹤股的新公告＋追蹤股明天要開董事會"""
    if not os.environ.get("TELEGRAM_TOKEN"):
        return
    chat, first = tg_chat()
    if not chat:
        return
    watch = watch_codes()
    sentp = DATA / "flash" / "sent.json"
    sent = load(sentp, [])

    def send(text):
        j = tg("sendMessage", {"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True})
        if not j.get("ok"):
            DIAG["fail"].append(f"telegram: {j.get('description')}")
        else:
            DIAG["notified"] += 1
        return j.get("ok")

    if first or os.environ.get("TG_TEST"):
        mine = [i for i in out["items"] if i["c"] in watch][:1]
        send(f"✅ 財報快訊已連上 Telegram\n追蹤 {len(watch)} 檔（主題成份股＋持股），公布後 30–40 分鐘內推播。"
             + ("\n\n範例：\n" + card(mine[0]) if mine else ""))
    cutoff = NOW - dt.timedelta(hours=6)
    new = []
    for i in out["items"]:
        k = f"{i['c']}_{i['q']}_{i['k']}"
        if k in sent or i["c"] not in watch:
            continue
        try:
            y, mo, d = [int(x) for x in i["t"][:9].split("/")]
            when = dt.datetime(y + 1911, mo, d, int(i["t"][10:12]), int(i["t"][13:15]), tzinfo=TZ)
        except Exception:
            continue
        if when >= cutoff:
            new.append(i)
        sent.append(k)                                  # 太舊的也記下，之後不會補推
    if len(new) <= 4:
        for i in new:
            send(card(i))
    else:                                              # 一次很多家 → 合併成一則，避免洗版
        send(f"📢 {len(new)} 家追蹤股公布財報\n\n" + "\n\n".join(card(i) for i in new[:12])
             + (f"\n\n…還有 {len(new) - 12} 家，看<a href=\"{SITE}flash.html\">快訊</a>" if len(new) > 12 else ""))
    # 董事會日期提醒：每天第一次執行（13:00 後）提醒「明天」開董事會的追蹤股
    tomorrow = (NOW.date() + dt.timedelta(days=1)).isoformat()
    ck = f"cal_{tomorrow}"
    if ck not in sent and NOW.hour >= 13:
        due = [c for c in out["cal"] if c["d"] == tomorrow and c["c"] in watch]
        if due:
            send("📅 明天開董事會（財報）：" + "、".join(f"{c['c']} {esc(c['n'])}" for c in due))
        sent.append(ck)
    sentp.write_text(json.dumps(sent[-3000:]))


def main():
    raw = load(RAW, {})
    start = os.environ.get("BACKFILL_FROM")
    days = []
    if start:
        d = dt.date.fromisoformat(start)
        while d <= NOW.date():
            days.append(d)
            d += dt.timedelta(days=1)
    else:
        days = [NOW.date() - dt.timedelta(days=1), NOW.date()]
    for d in days:
        fetch_day(d, raw)
        if DIAG["stop"]:
            break
    keep = (NOW.date() - dt.timedelta(days=200)).isoformat()
    def iso(roc):
        try:
            y, m, d = roc.split("/"); return f"{int(y) + 1911}-{m}-{d}"
        except Exception:
            return "9999"
    raw = {k: v for k, v in raw.items() if iso(v["d"]) >= keep}
    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_text(json.dumps(raw, ensure_ascii=False, separators=(",", ":")))
    out = build(raw)
    notify(out, raw)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(json.dumps({k: v for k, v in DIAG.items() if k != "days"}, ensure_ascii=False))
    print("快訊", len(out["items"]), "日曆", len(out["cal"]), "季別", out["seasons"][:3])


if __name__ == "__main__":
    main()
