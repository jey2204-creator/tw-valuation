"""上市櫃公司「非擔任主管職務之全時員工薪資」→ data/salary.json（個股頁、主題頁顯示薪資中位數用）

來源：證交所／櫃買中心 OpenAPI 的「企業ESG資訊揭露彙總資料-人力發展」（全市場一次抓完，不耗 FinMind）
  上市：openapi.twse.com.tw/v1/opendata/t187ap46_L_5
  上櫃：www.tpex.org.tw/openapi/v1/t187ap46_O_5（櫃買同系列命名為 t187ap46_O_<編號>；抓不到會再試其他寫法）
  欄位（仟元/人）：員工福利平均數、員工薪資平均數（全體員工，財報附註口徑）、非擔任主管職務之全時員工薪資平均數＋變動%、
       非擔任主管之全時員工薪資中位數＋變動%（排除經理人與部分工時，證交所／櫃買每年 6 月底公布前一年度）
輸出 d[代號] = [中位數(萬), 中位數變動%, 非主管平均數(萬), 平均數變動%, 全體員工福利平均數(萬), 全體員工薪資平均數(萬), 報告年度(民國)]
     另存 data/salary/{報告年度}.json 當歷史（之後可做年度比較）
一年只更新一次，但每次 Actions 都跑（2 個請求）：內容沒變就不寫檔、不產生 commit；來源失敗沿用上一版。
用法：python fetch_salary.py
"""
import json, sys, time, datetime as dt
from pathlib import Path
import urllib.request

OUT = Path(__file__).resolve().parent / "data"
TWSE = "https://openapi.twse.com.tw/v1"
TPEX = "https://www.tpex.org.tw/openapi/v1"
FIELDS = ["med", "medChg", "avg", "avgChg", "welf", "allAvg", "yr"]
SRC = {   # 市場: 候選網址（依序試，第一個有「中位數」欄位的採用）
    "上市": [f"{TWSE}/opendata/t187ap46_L_5"],
    "上櫃": [f"{TPEX}/t187ap46_O_5", f"{TPEX}/mopsfin_t187ap46_O_5", f"{TPEX}/opendata/t187ap46_O_5"],
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 tw-valuation", "Accept": "application/json"})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8-sig"))
        except Exception as e:
            if i == 2:
                raise RuntimeError(f"{url}: {e}")
            time.sleep(5 * (i + 1))


def num(v):
    """'1,273' / '2.05%' / 'N/A' / '' → float 或 None"""
    if v is None:
        return None
    s = str(v).replace(",", "").replace("%", "").replace("+", "").strip()
    if s in ("", "-", "--", "N/A", "NA", "null"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def pick(row, *needles):
    """欄名有尾端空白、各市場寫法略不同 → 用「包含全部關鍵字」比對（先 strip）"""
    for k, v in row.items():
        kk = k.strip()
        if all(n in kk for n in needles):
            return v
    return None


def wan(v):
    """仟元 → 萬元（一位小數）"""
    v = num(v)
    return None if v is None else round(v / 10, 1)


def parse(rows):
    """→ {代號: [中位數萬, 中位數變動%, 平均數萬, 平均變動%, 福利萬, 全體薪資萬, 年度]}"""
    d = {}
    for r in rows:
        c = str(pick(r, "公司代號") or "").strip()
        if not (len(c) == 4 and c.isdigit() and c[0] != "0"):
            continue
        yr = num(pick(r, "報告年度"))
        med = wan(pick(r, "全時員工薪資中位數", "仟元"))
        avg = wan(pick(r, "全時員工薪資平均數", "仟元"))
        if med is None and avg is None:
            continue
        chg = num(pick(r, "全時員工薪資中位數變動"))
        achg = num(pick(r, "全時員工薪資平均數變動"))
        welf = wan(pick(r, "員工福利平均數"))
        all_avg = wan(next((v for k, v in r.items() if k.strip() == "員工薪資平均數(仟元/人)"), None))
        d[c] = [med, chg, avg, achg, welf, all_avg, int(yr) if yr else None]
    return d


def fetch_market(name, urls, errs, src):
    last = None
    for u in urls:
        try:
            rows = get(u)
        except Exception as e:
            last = e
            continue
        if not isinstance(rows, list) or not rows:
            last = RuntimeError(f"{u}: 空資料")
            continue
        if not any("中位數" in k for k in rows[0]):
            last = RuntimeError(f"{u}: 欄位對不上 {list(rows[0])[:6]}")
            continue
        d = parse(rows)
        src[name] = u.rsplit("/", 1)[-1]
        print(f"{name}: {len(rows)} 列，解析 {len(d)} 檔（{src[name]}）")
        return d
    errs.append(f"{name}: {last}")
    print(f"{name} FAILED: {last}", file=sys.stderr)
    return {}


def main():
    OUT.mkdir(exist_ok=True)
    try:
        old = json.loads((OUT / "salary.json").read_text("utf-8"))
    except Exception:
        old = {}
    d, errs, src = {}, [], {}
    for name, urls in SRC.items():
        d.update(fetch_market(name, urls, errs, src))
    if not d:
        print("全部來源都失敗，保留舊檔", file=sys.stderr)
        sys.exit(1)
    for c, v in (old.get("d") or {}).items():   # 某個市場失敗 → 沿用上一版
        d.setdefault(c, v)
    years = {}
    for v in d.values():
        if v[6]:
            years[v[6]] = years.get(v[6], 0) + 1
    yr = max(years, key=years.get) if years else None
    med_all = sorted(v[0] for v in d.values() if v[0] is not None and v[6] == yr)
    stats = {"n": len(med_all), "medOfMed": med_all[len(med_all) // 2] if med_all else None,
             "p25": med_all[len(med_all) // 4] if med_all else None, "p75": med_all[len(med_all) * 3 // 4] if med_all else None,
             "years": {str(k): v for k, v in sorted(years.items())}}
    for c in ("2330", "2454", "1301", "5274", "2002"):
        if c in d:
            print(f"  {c}: 中位數 {d[c][0]} 萬（{d[c][1]}%）、平均 {d[c][2]} 萬、年度 {d[c][6]}")
    print(f"報告年度 {yr}：{stats['n']} 檔有中位數，全市場中位數的中位數 {stats['medOfMed']} 萬（P25 {stats['p25']}、P75 {stats['p75']}）")

    changed = old.get("d") != d or old.get("yr") != yr
    if not changed and not errs:
        print("內容沒有變動，不寫檔")
        return
    now = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
    out = dict(updated=now if changed else old.get("updated", now), yr=yr, yrAD=yr + 1911 if yr else None,
               fields=FIELDS, sources=src, errors=errs, stats=stats, d=d)
    (OUT / "salary.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
    if yr and changed:                                   # 歷史：每個報告年度一個檔
        (OUT / "salary").mkdir(exist_ok=True)
        hist = {c: v for c, v in d.items() if v[6] == yr}
        p = OUT / "salary" / f"{yr}.json"
        try:
            same = json.loads(p.read_text("utf-8")).get("d") == hist
        except Exception:
            same = False
        if not same:
            p.write_text(json.dumps({"yr": yr, "updated": now, "d": hist}, ensure_ascii=False, separators=(",", ":")), "utf-8")
            print(f"歷史檔 salary/{yr}.json：{len(hist)} 檔")
    print(f"salary.json: {len(d)} 檔，報告年度 {yr}，失敗 {len(errs)} 個來源")


if __name__ == "__main__":
    main()
