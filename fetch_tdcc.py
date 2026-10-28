"""集保大戶持股比例（每週）→ data/tdcc.json

來源：
  1. 集保開放資料 opendata.tdcc.com.tw/getOD.ashx?id=1-5（全市場、只有最新一週，每週六更新上週五資料）
  2. 集保「股權分散表查詢」網頁 www.tdcc.com.tw/portal/zh/smWeb/qryStock（可查過去一年，一次一檔一週）
     → 只對 themes.json 成份股回補過去幾週，讓「週變化」第一天就有數字；失敗不影響 1

每週一個檔 data/tdcc/YYYYMMDD.json = {代號: [≥400張%, ≥1000張%, 股東人數]}（全市場週檔另含 "_all":1）
輸出 d[代號] = [≥400張%, 週變化, 4週變化, ≥1000張%, 週變化, 股東人數, 人數週變化%, 人數4週變化%]
  持股分級 12～15 = 400 張以上；15 = 1000 張以上；17 = 合計
任何一步失敗都不會讓程式以錯誤結束（除非完全沒有資料）。
用法：python fetch_tdcc.py
"""
import csv, io, json, re, sys, time, datetime as dt
from pathlib import Path
import urllib.request, urllib.parse, http.cookiejar

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data"
DIR = OUT / "tdcc"
KEEP = 30                     # 保留最近 30 週
BACKFILL_WEEKS = 5            # 主題股回補幾週
BUDGET = 8 * 60
T0 = time.time()
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
diag, errs = {}, []


def ok_code(c):
    c = str(c).strip()
    return c if len(c) == 4 and c.isdigit() and c[0] != "0" else None


def num(v):
    s = str(v or "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def rec_from_levels(lv):
    """lv: {分級: (人數, 股數, 比例%)} → [≥400張%, ≥1000張%, 股東人數]"""
    if not lv:
        return None
    b400 = sum(lv[k][2] or 0 for k in (12, 13, 14, 15) if k in lv)
    b1000 = (lv.get(15) or (0, 0, 0))[2] or 0
    ppl = (lv.get(17) or (None,))[0]
    if ppl is None:                                   # 沒有合計列就自己加
        ppl = sum(lv[k][0] or 0 for k in range(1, 16) if k in lv)
    return [round(b400, 2), round(b1000, 2), int(ppl or 0)]


def save_week(date, d, full=False):
    DIR.mkdir(parents=True, exist_ok=True)
    f = DIR / f"{date}.json"
    old = {}
    if f.exists():
        try:
            old = json.loads(f.read_text("utf-8"))
        except Exception:
            old = {}
    old.update(d)
    if full:
        old["_all"] = 1
    f.write_text(json.dumps(old, ensure_ascii=False, separators=(",", ":")), "utf-8")


# ---------- 1. 開放資料：全市場最新一週 ----------
def opendata():
    req = urllib.request.Request("https://opendata.tdcc.com.tw/getOD.ashx?id=1-5", headers={"User-Agent": UA})
    raw = None
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = r.read()
            break
        except Exception as e:
            if i == 2:
                raise
            time.sleep(10)
    txt = raw.decode("utf-8-sig", errors="replace")
    rows = list(csv.reader(io.StringIO(txt)))
    diag["od_head"] = rows[0][:6] if rows else None
    diag["od_rows"] = len(rows)
    lv, date = {}, None
    for r in rows[1:]:
        if len(r) < 6:
            continue
        c = ok_code(r[1])
        try:
            k = int(r[2])
        except ValueError:
            continue
        if not c:
            continue
        date = date or "".join(ch for ch in r[0] if ch.isdigit())
        lv.setdefault(c, {})[k] = (num(r[3]), num(r[4]), num(r[5]))
    out = {c: rec_from_levels(v) for c, v in lv.items()}
    out = {c: v for c, v in out.items() if v}
    diag["od_date"], diag["od_n"] = date, len(out)
    if date and len(date) == 8 and out:
        save_week(date, out, full=True)
    return date


# ---------- 2. 網頁查詢：主題股回補 ----------
class Web:
    URL = "https://www.tdcc.com.tw/portal/zh/smWeb/qryStock"

    def __init__(self):
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.token, self.dates = None, []

    def open(self, data=None):
        req = urllib.request.Request(self.URL, data=data, headers={"User-Agent": UA, "Referer": self.URL})
        with self.op.open(req, timeout=40) as r:
            return r.read().decode("utf-8", errors="replace")

    def init(self):
        h = self.open()
        m = re.search(r'name="SYNCHRONIZER_TOKEN"[^>]*value="([^"]+)"', h) or re.search(r'value="([^"]+)"[^>]*name="SYNCHRONIZER_TOKEN"', h)
        self.token = m.group(1) if m else None
        sel = re.search(r'<select[^>]*(?:id|name)="scaDate".*?</select>', h, re.S)
        self.dates = re.findall(r'<option[^>]*value="(\d{8})"', sel.group(0) if sel else h)
        diag["web_token"] = bool(self.token)
        diag["web_dates"] = self.dates[:6]
        return bool(self.token and self.dates)

    def query(self, code, date):
        form = {"SYNCHRONIZER_TOKEN": self.token, "SYNCHRONIZER_URI": "/portal/zh/smWeb/qryStock",
                "method": "submit", "firDate": self.dates[0], "scaDate": date, "sqlMethod": "StockNo",
                "stockNo": code, "stockName": ""}
        h = self.open(urllib.parse.urlencode(form).encode())
        m = re.search(r'name="SYNCHRONIZER_TOKEN"[^>]*value="([^"]+)"', h)
        if m:
            self.token = m.group(1)
        lv = {}
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
            td = [re.sub(r"<[^>]+>|&nbsp;", "", x).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            if len(td) >= 5 and td[0].isdigit():
                k = int(td[0])
                if "合" in td[1] or "計" in td[1]:
                    k = 17
                elif "差異" in td[1]:
                    k = 16
                lv[k] = (num(td[2]), num(td[3]), num(td[4]))
        return rec_from_levels(lv)


def theme_ids():
    th = json.loads((OUT / "themes.json").read_text("utf-8"))["themes"]
    return sorted({s[0] for t in th for s in t["stocks"]} | itrust_top_ids())

def itrust_top_ids():
    """估值頁的投本比自動主題（data/itrust_top.json：投信／外資／土洋前 20）也當成主題成份股一起抓。"""
    try:
        j = json.loads((OUT / "itrust_top.json").read_text("utf-8"))
        return {r["c"] for L in (j.get("lists") or {}).values() for r in L}
    except Exception:
        return set()


def backfill(latest):
    done = {}
    for f in DIR.glob("*.json"):
        try:
            done[f.stem] = set(json.loads(f.read_text("utf-8")).keys())
        except Exception:
            pass
    w = Web()
    if not w.init():
        errs.append("集保查詢頁：取不到 token 或日期清單")
        return
    ids = theme_ids()
    want = w.dates[:BACKFILL_WEEKS + 1]
    n = fail = 0
    for d in want:
        got = {}
        for c in ids:
            if c in done.get(d, set()):
                continue
            if time.time() - T0 > BUDGET or fail >= 5:
                break
            try:
                r = w.query(c, d)
                if r and r[2] > 0:
                    got[c] = r
                    n += 1
                    fail = 0
                else:
                    fail += 1
            except Exception as e:
                fail += 1
                errs.append(f"集保 {d} {c}: {str(e)[:60]}")
                try:
                    w.init()
                except Exception:
                    pass
            time.sleep(0.8)
        if got:
            save_week(d, got)
        if time.time() - T0 > BUDGET or fail >= 5:
            errs.append(f"集保回補中斷（{'時間到' if fail < 5 else '連續失敗'}），下次繼續")
            break
    diag["web_got"] = n


def prune():
    fs = sorted(DIR.glob("*.json"))
    for f in fs[:-KEEP]:
        f.unlink()


def compute():
    weeks = []
    for f in sorted(DIR.glob("*.json")):
        try:
            weeks.append((f.stem, json.loads(f.read_text("utf-8"))))
        except Exception:
            pass
    if not weeks:
        return {}, []
    out = {}
    cur_date, cur = weeks[-1]
    for c, v in cur.items():
        if c.startswith("_") or not v:
            continue
        hist = [(d, w[c]) for d, w in weeks if c in w and w[c]]
        if not hist or hist[-1][0] != cur_date:
            continue
        def ago(n):
            # n 週前那一筆：日期要剛好相隔 n 週（±3 天），避免缺週時誤算
            t = dt.datetime.strptime(cur_date, "%Y%m%d") - dt.timedelta(weeks=n)
            for d, x in hist:
                if abs((dt.datetime.strptime(d, "%Y%m%d") - t).days) <= 3:
                    return x
            return None
        p1, p4 = ago(1), ago(4)
        b4, b10, ppl = v
        out[c] = [b4, round(b4 - p1[0], 2) if p1 else None, round(b4 - p4[0], 2) if p4 else None,
                  b10, round(b10 - p1[1], 2) if p1 else None, ppl,
                  round((ppl / p1[2] - 1) * 100, 1) if p1 and p1[2] else None,
                  round((ppl / p4[2] - 1) * 100, 1) if p4 and p4[2] else None]
    return out, [d for d, _ in weeks]


def main():
    OUT.mkdir(exist_ok=True)
    latest = None
    try:
        latest = opendata()
    except Exception as e:
        errs.append(f"集保開放資料: {str(e)[:100]}")
    try:
        backfill(latest)
    except Exception as e:
        errs.append(f"集保回補: {str(e)[:100]}")
    try:
        prune()
    except Exception:
        pass
    d, weeks = compute()
    if not d:
        print("沒有集保資料，不輸出", errs, diag, file=sys.stderr)
        sys.exit(0)
    res = dict(updated=dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"), asof=weeks[-1], weeks=weeks[-8:],
               fields=["b400", "b400w", "b400m", "b1000", "b1000w", "ppl", "pplw", "pplm"],
               errors=errs[:20], diag=diag, secs=int(time.time() - T0), d=d)
    (OUT / "tdcc.json").write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"tdcc.json: {len(d)} 檔，最新 {weeks[-1]}，共 {len(weeks)} 週，錯誤 {len(errs)}")


if __name__ == "__main__":
    main()
