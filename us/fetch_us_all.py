"""美股全市場財報：SEC EDGAR → us/data/all/{TICKER}.json（只有財報，股價由瀏覽器即時抓 FinMind）
用法：python us/fetch_us_all.py                 # 依 UNIVERSE 設定（預設 top 600 市值 + 45 檔 + 常用清單）
     python us/fetch_us_all.py TSLA AAPL       # 指定代號
環境變數：
  SEC_UA        SEC 要求的 User-Agent（含聯絡 email）
  FINMIND_TOKEN 選填
  UNIVERSE_N    依市值取前 N 檔（預設 600；設 0 = 不限，全市場）
  SEC_MODE      api（預設，逐檔抓 companyfacts API）或 zip（下載 companyfacts.zip 一次解開，全市場用）
財報抽取邏輯完全沿用 fetch_us.py（build_fin），確保 45 檔與全市場數字一致。
"""
import json, os, sys, time, datetime as dt, zipfile, io, re
from pathlib import Path
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_us as F   # 共用 sec()/finmind()/build_fin()

OUT = Path(__file__).resolve().parent / "data" / "all"
MODE = os.environ.get("SEC_MODE", "api")
N = int(os.environ.get("UNIVERSE_N", "600"))
YEARS = F.YEARS

# 無論市值排名如何都一定收錄的常用代號（供應鏈客戶、巨型股、使用者常查）
ALWAYS = """
AAPL MSFT NVDA AMZN GOOGL GOOG META TSLA AVGO BRK-B LLY JPM V UNH XOM MA COST PG JNJ HD ABBV WMT NFLX BAC CRM ORCL KO
CVX MRK AMD PEP CSCO ADBE TMO ACN LIN MCD ABT WFC IBM GE CAT TXN QCOM INTU DHR AMGN NOW ISRG PM VZ AXP NEE SPGI PFE
AMAT UBER RTX CMCSA LOW HON UNP T BKNG PGR GS BLK ETN COP SYK ADP MU LRCX VRTX TJX PANW BSX KLAC PLTR ADI ANET MDLZ
GILD CB SBUX MMC REGN LMT CI FI PLD DE BX MO SCHW AMT TMUS INTC SO ELV ZTS DUK CMG KKR BMY APH SHW MSI CTAS CL ICE
PYPL TT MCK EQIX WM PH AON USB ITW GD CVS NOC CDNS SNPS APD ORLY MAR CRWD ABNB PNC MELI WDAY ROP COF EMR HCA FDX
CSX ECL TGT AJG NXPI MCO DELL SMCI ARM TSM ASML CEG VST GEV VRT COHR LITE CRDO ALAB MRVL ONTO ENTG CAMT FORM AMKR
WOLF VSH LFUS TTMI SANM JBL CLS FN CIEN AAOI SNDK ASTS RKLB SATS IRDM GSAT VSAT NBIS CRWV IONQ RGTI QBTS DDOG SNOW
MDB NET ZS FTNT OKTA TEAM SHOP SQ COIN HOOD SOFI AFRM RIVN LCID NIO XPEV LI BABA PDD JD BIDU TCEHY SPOT TTD ROKU U
""".split()


def universe(cik_map):
    """市值前 N 檔（FinMind USStockInfo）∪ 45 檔 ∪ ALWAYS，再過濾掉 SEC 查無 CIK 的"""
    ids = set(F.STOCKS) | set(ALWAYS)
    if N != 1:   # N=1 代表只要固定清單（測試用）
        try:
            info = F.finmind("USStockInfo", "", "")
            if info:
                keys = list(info[0].keys())
                capk = next((k for k in keys if "cap" in k.lower()), None)
                print(f"USStockInfo 欄位：{keys}；市值欄位：{capk}；共 {len(info)} 檔")
                rows = [r for r in info if r.get("stock_id") and re.fullmatch(r"[A-Z][A-Z.\-]{0,5}", str(r["stock_id"]))]
                if capk:
                    rows = [r for r in rows if r.get(capk) not in (None, "", 0)]
                    rows.sort(key=lambda r: -float(r[capk]))
                if N > 0:
                    rows = rows[:N]
                ids |= {r["stock_id"] for r in rows}
        except Exception as e:
            print(f"USStockInfo 失敗（改用固定清單）：{e}", file=sys.stderr)
    have = [t for t in sorted(ids) if t.replace("-", ".") in cik_map or t in cik_map]
    print(f"清單 {len(ids)} 檔，SEC 有 CIK 的 {len(have)} 檔")
    return have


def cik_of(tk, cik_map):
    return cik_map.get(tk) or cik_map.get(tk.replace("-", "."))


def fin_from_cf(cf):
    """build_fin 以 cik 當參數並自己打 API；zip 模式要直接餵 companyfacts 內容，所以暫時替換 F.sec"""
    orig = F.sec
    F.sec = lambda url: cf
    try:
        return F.build_fin(0)
    finally:
        F.sec = orig


def pack(tk, cik, fin):
    today = dt.date.today()
    q = [[x["cal"], x["fis"], x["rev"], x["gm"], x["om"], x["nm"], x["eps"], x["capex"], x["sh"], x["end"], x["filed"]]
         for x in fin["q"] if x["end"] >= f"{today.year - YEARS - 1}-01-01"]
    note = []
    if fin["freq"] == "A":
        note.append("外國發行人只交年報（20-F／40-F），財報為年度資料")
    elif len(fin["q"]) < 4:
        note.append(f"上市不久，財報只有 {len(fin['q'])} 季，歷史資料不足")
    if fin["splits"]:
        note.append("EPS 已依分割調整：" + "、".join(f"{d[:7]} 1拆{n}" for d, n in fin["splits"]))
    return dict(id=tk, name=fin["name"], cik=cik, freq=fin["freq"], fye=fin["fye"], splits=fin["splits"],
                updated=dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"), q=q, eq=fin["eq"], note=note)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tick = F.sec("https://www.sec.gov/files/company_tickers.json")
    cik_map = {v["ticker"].upper(): int(v["cik_str"]) for v in tick.values()}
    name_map = {v["ticker"].upper(): v["title"] for v in tick.values()}
    ids = [a.upper() for a in sys.argv[1:]] or universe(cik_map)
    ok, bad = {}, []
    t0 = time.time()

    if MODE == "zip":
        # 全市場：一次下載 companyfacts.zip（約 1 GB），串流逐檔讀，不整包進記憶體
        zp = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "companyfacts.zip"
        req = urllib.request.Request("https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip",
                                     headers={"User-Agent": F.UA})
        with urllib.request.urlopen(req, timeout=600) as r, open(zp, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
        print(f"companyfacts.zip {zp.stat().st_size / 1e9:.2f} GB，{time.time() - t0:.0f}s")
        want = {cik_of(t, cik_map): t for t in ids if cik_of(t, cik_map)}
        with zipfile.ZipFile(zp) as z:
            names = set(z.namelist())
            for cik, tk in want.items():
                fn = f"CIK{cik:010d}.json"
                if fn not in names:
                    bad.append(tk); continue
                try:
                    cf = json.loads(z.read(fn))
                    ok[tk] = pack(tk, cik, fin_from_cf(cf))
                except Exception as e:
                    bad.append(tk); print(f"{tk:6} FAILED: {e}", file=sys.stderr)
    else:
        for tk in ids:
            cik = cik_of(tk, cik_map)
            if not cik:
                bad.append(tk); continue
            try:
                ok[tk] = pack(tk, cik, F.build_fin(cik))
            except Exception as e:
                bad.append(tk); print(f"{tk:6} FAILED: {e}", file=sys.stderr)

    for tk, d in ok.items():
        (OUT / f"{tk}.json").write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), "utf-8")
        lq = d["q"][-1] if d["q"] else None
        print(f"{tk:6} ok {d['name'][:30]:30} {d['freq']} n={len(d['q'])} "
              f"{(lq[0] + ' rev=' + str(lq[2]) + ' eps=' + str(lq[6])) if lq else '無財報'}")

    # 索引：[代號, 公司名, 財報頻率, 季數, 最新季]；指定代號時與舊索引合併
    idx = OUT / "index.json"
    old = {r[0]: r for r in json.loads(idx.read_text("utf-8"))} if idx.exists() else {}
    for tk, d in ok.items():
        lq = d["q"][-1][0] if d["q"] else None
        old[tk] = [tk, d["name"] or name_map.get(tk, ""), d["freq"], len(d["q"]), lq]
    if not sys.argv[1:]:   # 全量更新時，清單外的舊檔從索引拿掉（檔案保留）
        old = {k: v for k, v in old.items() if k in ok}
    idx.write_text(json.dumps([old[k] for k in sorted(old)], ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"完成 {len(ok)}／{len(ids)}，{time.time() - t0:.0f}s，失敗 {len(bad)}：{bad[:30]}")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
