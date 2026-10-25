"""韓股市值排行 Top N（KOSPI＋KOSDAQ 合併）→ kr/data/rank.json
用法：python kr/fetch_rank.py          # 預設前 20
     python kr/fetch_rank.py 30       # 前 30
資料：Naver 行動版 API（不需金鑰）。只用 Python 標準函式庫。

做法（刻意做兩層，任一層壞掉都還排得出來）：
  1. 候選股 = Naver 市值排行清單（KOSPI 前 40、KOSDAQ 前 15）∪ SEED 常駐大型股
  2. 每檔再抓 integration 頁的市值／本益比／淨值比／殖利率／外資持股（跟 fetch_kr.py 同一支 API，格式已驗證）
  3. 依 integration 市值排序取前 N；股價日漲跌缺的話用日 K 補
抓失敗（排不出 N 檔）就不覆寫舊檔、exit 1，頁面繼續顯示上一版。
"""
import json, re, sys, time, datetime as dt
from pathlib import Path
import urllib.request

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
OUT = Path(__file__).resolve().parent / "data"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
KST = dt.timezone(dt.timedelta(hours=9))
TODAY = dt.datetime.now(KST).date()

# 常駐候選＋中文名（Naver 排行清單抓不到時也排得出來；名單外的新進榜股顯示韓文名）
ZH = {
    "005930": "三星電子", "005935": "三星電子(特)", "000660": "SK海力士", "373220": "LG新能源",
    "207940": "三星生物製劑", "005380": "現代汽車", "000270": "起亞", "068270": "賽特瑞恩",
    "105560": "KB金融", "055550": "新韓金融", "086790": "韓亞金融", "316140": "友利金融",
    "138040": "Meritz金融", "012450": "韓華航太", "329180": "HD現代重工", "009540": "HD韓國造船海洋",
    "042660": "韓華海洋", "010140": "三星重工業", "267260": "HD現代電機", "064350": "現代Rotem",
    "034020": "斗山能源", "012330": "現代摩比斯", "005490": "POSCO控股", "028260": "三星物產",
    "032830": "三星人壽", "000810": "三星火災", "006400": "三星SDI", "009150": "三星電機",
    "018260": "三星SDS", "051910": "LG化學", "066570": "LG電子", "003550": "LG",
    "035420": "NAVER", "035720": "Kakao", "323410": "KakaoBank", "015760": "韓國電力",
    "010130": "高麗亞鉛", "011200": "HMM", "096770": "SK創新", "034730": "SK",
    "402340": "SK Square", "017670": "SK電訊", "030200": "KT", "033780": "KT&G",
    "352820": "HYBE", "010120": "LS電氣", "298040": "曉星重工業", "042700": "韓美半導體",
    "247540": "Ecopro BM", "086520": "Ecopro", "196170": "Alteogen", "028300": "HLB",
    "000100": "柳韓洋行", "326030": "SK生物製藥",
}


def http(url, tries=3, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*", "Accept-Language": "ko-KR,ko;q=0.9"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception as e:
            if i == tries - 1:
                raise RuntimeError(f"{url.split('?')[0]}: {e}")
            time.sleep(2 * (i + 1))


def kv(s):
    """'1,391조 4,143억' / '10.68배' / '22,292원' / '46.18%' → 數字（金額單位：億韓元）"""
    if s is None:
        return None
    s = str(s).replace(",", "")
    if "조" in s or "억" in s:
        jo, eok = re.search(r"([\d.]+)조", s), re.search(r"([\d.]+)억", s)
        return (float(jo[1]) * 1e4 if jo else 0) + (float(eok[1]) if eok else 0)
    m = re.search(r"-?[\d.]+", s)
    return float(m[0]) if m else None


def listing(mkt, size):
    """Naver 市值排行清單 → {代號: dict(name, mkt, close, chg)}"""
    j = http(f"https://m.stock.naver.com/api/stocks/marketValue/{mkt}?page=1&pageSize={size}")
    rows = j.get("stocks") if isinstance(j, dict) else j
    out = {}
    for i, x in enumerate(rows or []):
        if i == 0:
            DIAG["sample_" + mkt] = {k: x.get(k) for k in list(x)[:30]}
        code = str(x.get("itemCode") or x.get("reutersCode") or "")[:6]
        if not re.fullmatch(r"\d{5}[0-9A-Z]", code):
            continue
        out[code] = dict(name=x.get("stockName"), mkt=mkt, close=kv(x.get("closePrice")),
                         chg=kv(x.get("fluctuationsRatio")), lrank=i + 1)
    return out


def info(code):
    j = http(f"https://m.stock.naver.com/api/stock/{code}/integration")
    t = {x.get("code"): x.get("value") for x in j.get("totalInfos", [])}
    return dict(name=j.get("stockName"), mcap=kv(t.get("marketValue")), per=kv(t.get("per")), pbr=kv(t.get("pbr")),
                dy=kv(t.get("dividendYieldRatio")), fr=kv(t.get("foreignRate")))


def last2(code):
    """日 K 最後兩根 → (收盤, 日漲跌%)"""
    st = (TODAY - dt.timedelta(days=14)).strftime("%Y%m%d") + "0000"
    en = TODAY.strftime("%Y%m%d") + "2359"
    j = http(f"https://api.stock.naver.com/chart/domestic/item/{code}/day?startDateTime={st}&endDateTime={en}")
    px = sorted([(x["localDate"], float(x["closePrice"])) for x in j if x.get("closePrice")])
    if not px:
        return None, None, None
    d = px[-1][0]
    chg = round((px[-1][1] / px[-2][1] - 1) * 100, 2) if len(px) > 1 and px[-2][1] else None
    return px[-1][1], chg, f"{d[:4]}-{d[4:6]}-{d[6:]}"


DIAG = {}


def main():
    cand = {}
    for mkt, size in (("KOSPI", 40), ("KOSDAQ", 15)):
        try:
            cand.update(listing(mkt, size))
            DIAG[mkt] = len(cand)
        except Exception as e:
            DIAG[mkt + "_err"] = str(e)[:200]
            print("排行清單失敗：", mkt, e)
    for c in ZH:
        cand.setdefault(c, dict(name=None, mkt="", close=None, chg=None))
    rows, errs = [], []
    for c, x in cand.items():
        try:
            x.update({k: v for k, v in info(c).items() if v is not None or k not in x})
        except Exception as e:
            errs.append(f"{c}: {e}"[:160])
            continue
        if x.get("mcap"):
            rows.append(dict(code=c, **x))
        time.sleep(0.15)
    rows.sort(key=lambda r: -r["mcap"])
    rows = rows[:N]
    date = None
    for r in rows:
        if r.get("close") is None or r.get("chg") is None:
            try:
                c, chg, d = last2(r["code"])
                r["close"] = r["close"] if r.get("close") is not None else c
                r["chg"] = r["chg"] if r.get("chg") is not None else chg
                date = max(date or d, d) if d else date
            except Exception as e:
                errs.append(f"{r['code']} px: {e}"[:160])
    if not date:
        try:
            date = last2(rows[0]["code"])[2]
        except Exception:
            date = TODAY.isoformat()
    tot = sum(r["mcap"] for r in rows)
    out = dict(date=date, built=dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M"), n=len(rows), total=round(tot),
               rows=[[r["code"], ZH.get(r["code"], ""), r.get("name") or "", r.get("mkt") or "", round(r["mcap"]),
                      r.get("close"), r.get("chg"), r.get("per"), r.get("pbr"), r.get("dy"), r.get("fr")] for r in rows])
    DIAG.update(cand=len(cand), errs=errs[:20])
    (OUT / "rank_diag.json").write_text(json.dumps(DIAG, ensure_ascii=False, indent=1), "utf-8")
    if len(rows) < N:
        print(f"只排出 {len(rows)} 檔（< {N}），不覆寫 rank.json")
        sys.exit(1)
    (OUT / "rank.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
    for i, r in enumerate(out["rows"], 1):
        print(f"{i:>2} {r[0]} {r[1] or r[2]:<12} {r[3]:<6} 市值 {r[4] / 1e4:,.1f} 兆韓元  PER {r[7]}  PBR {r[8]}")


if __name__ == "__main__":
    main()
