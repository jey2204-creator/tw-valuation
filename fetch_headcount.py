"""上市櫃公司員工人數 → data/headcount.json（個股頁薪資列、薪資排行頁用）

來源：公開資訊觀測站（MOPS）兩張彙總表，證交所／櫃買 OpenAPI 沒有這些欄位，只能爬 MOPS（一年 4 次請求）
  t100sb15 非擔任主管職務之全時員工薪資資訊：員工薪資總額(仟元)、員工人數-年度平均（非主管全時）、平均數、中位數、EPS…
  t100sb14 財務報告附註揭露之員工福利(薪資)資訊：員工人數（全體，含經理人、部分工時）、員工薪資費用(仟元)、平均薪資費用…（個體財報口徑）
  MOPS 2025 年改版，新舊站都試：mopsov.twse.com.tw（舊站 ajax）、mops.twse.com.tw（ajax 與 api JSON）；每次嘗試都寫進 data/headcount_diag.json 方便除錯
輸出 d[代號] = [非主管全時人數, 非主管薪資總額(億), 全體員工人數, 全體薪資費用(億)]；抓不到的欄位 null
  欄位靠數字關係辨認（薪資總額 ÷ 人數 ≈ 平均數、中位數 ≈ salary.json），不靠表頭文字，表頭改版也不怕
  年度同 salary.json（報告年度，民國）；另存 data/headcount/{年度}.json
排程：平時只有 headcount.json 不存在、年度落後 salary.json、或 FORCE=1 時才抓（MOPS 不宜常打）；內容沒變不寫檔
用法：python fetch_headcount.py   （環境變數 FORCE=1 強制重抓）
"""
import json, os, re, sys, time, html, datetime as dt
from pathlib import Path
from html.parser import HTMLParser
import urllib.request, urllib.parse

OUT = Path(__file__).resolve().parent / "data"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
HOSTS = ["https://mopsov.twse.com.tw", "https://mops.twse.com.tw"]
DIAG = {"tries": []}


def req(url, data=None, json_body=None, referer=None):
    hdr = {"User-Agent": UA, "Accept": "text/html,application/json;q=0.9,*/*;q=0.8", "Accept-Language": "zh-TW,zh;q=0.9",
           "Referer": referer or url}
    body = None
    if json_body is not None:
        body = json.dumps(json_body).encode()
        hdr["Content-Type"] = "application/json"
    elif data is not None:
        body = urllib.parse.urlencode(data).encode()
        hdr["Content-Type"] = "application/x-www-form-urlencoded"
    r = urllib.request.Request(url, data=body, headers=hdr, method="POST" if body is not None else "GET")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read()
            txt = raw.decode("utf-8", "replace")
            st = resp.status
    except urllib.error.HTTPError as e:
        txt, st = e.read().decode("utf-8", "replace"), e.code
    except Exception as e:
        txt, st = "", f"ERR {e}"
    DIAG["tries"].append({"url": url, "kind": "json" if json_body is not None else "form", "status": st, "len": len(txt),
                          "sec": round(time.time() - t0, 1), "snippet": re.sub(r"\s+", " ", txt)[:600]})
    return st, txt


class Tables(HTMLParser):
    """把回應裡所有 <table> 變成 [[cell, …], …]（跨列表頭也只取文字）"""
    def __init__(self):
        super().__init__(); self.tables, self.row, self.cell, self.in_cell = [], None, None, False
    def handle_starttag(self, tag, attrs):
        if tag == "table": self.tables.append([])
        elif tag == "tr": self.row = []
        elif tag in ("td", "th"): self.cell, self.in_cell = [], True
    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.in_cell:
            if self.row is not None: self.row.append(re.sub(r"\s+", " ", html.unescape("".join(self.cell))).strip())
            self.in_cell = False
        elif tag == "tr" and self.row is not None:
            if self.tables and self.row: self.tables[-1].append(self.row)
            self.row = None
    def handle_data(self, d):
        if self.in_cell: self.cell.append(d)


def num(s):
    s = str(s or "").replace(",", "").replace("%", "").strip()
    if s in ("", "-", "--", "N/A", "NA"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def rows_from(txt):
    """HTML 或 JSON 回應 → 含 4 碼代號的資料列（每列 = 文字 cell 清單）"""
    out = []
    t = txt.lstrip()
    if t.startswith("{") or t.startswith("["):
        try:
            j = json.loads(t)
        except Exception:
            j = None
        def walk(x):
            if isinstance(x, list):
                if x and all(not isinstance(v, (list, dict)) for v in x):
                    out.append([str(v) for v in x])
                else:
                    for v in x: walk(v)
            elif isinstance(x, dict):
                for v in x.values(): walk(v)
        if j is not None:
            walk(j)
    if not out:
        p = Tables(); p.feed(txt)
        for tb in p.tables:
            out.extend(tb)
    return [r for r in out if any(re.fullmatch(r"[1-9]\d{3}", c.strip()) for c in r)]


def fetch_table(tid, typek, year):
    """依序試各種端點，回傳 (資料列, 來源說明)"""
    form = {"encodeURIComponent": 1, "step": 1, "firstin": 1, "off": 1, "TYPEK": typek, "RYEAR": year, "YEAR": year, "year": year, "code": ""}
    tries = []
    for h in HOSTS:
        tries.append((f"{h}/mops/web/ajax_{tid}", form, None, f"{h}/mops/web/{tid}"))
    tries.append((f"https://mops.twse.com.tw/mops/api/{tid}", None, {"encodeURIComponent": 1, "step": 1, "firstin": 1, "off": 1, "TYPEK": typek, "RYEAR": str(year), "YEAR": str(year), "year": str(year), "code": ""}, f"https://mops.twse.com.tw/mops/web/{tid}"))
    for url, data, jb, ref in tries:
        st, txt = req(url, data=data, json_body=jb, referer=ref)
        rows = rows_from(txt) if txt else []
        DIAG["tries"][-1]["rows"] = len(rows)
        if rows:
            DIAG["tries"][-1]["sample"] = rows[0][:16]
            return rows, url.split("//")[1]
        time.sleep(3)
    return [], None


def code_of(r):
    return next((c.strip() for c in r if re.fullmatch(r"[1-9]\d{3}", c.strip())), None)


def vote(counter):
    return max(counter, key=counter.get) if counter else None


def parse_generic(rows, ref, label):
    """用數字關係找欄位（整張表投票決定欄位位置，再逐列套用）：
    ref[代號] = 參考值（仟元）：sb15 用 salary.json 的中位數、sb14 用 ESG 的員工薪資平均數
    1) 參考欄 = 每列最接近 ref 的 cell，投票取多數 → ref_idx
    2) 總額 ÷ 人數 ≈ 某個 cell（人數為整數、總額最大）→ 投票 (total_idx, n_idx, avg_idx)
    回傳 {代號: [人數, 總額(億)]}、失敗列數、欄位索引"""
    from collections import Counter
    lens = Counter(len(r) for r in rows)
    L = vote(lens)
    rows = [r for r in rows if len(r) == L]
    nums = [[num(c) for c in r] for r in rows]
    codes = [code_of(r) for r in rows]
    c1 = Counter()
    for r, nr, code in zip(rows, nums, codes):
        v = ref.get(code)
        if v is None: continue
        cand = [(abs(x - v * 10) / (v * 10), i) for i, x in enumerate(nr) if x is not None and x > 0]
        if cand:
            e, i = min(cand)
            if e < 0.01: c1[i] += 1
    ref_idx = vote(c1)
    c2 = Counter()
    for nr in nums:
        best = None
        for i, total in enumerate(nr):
            if total is None or total <= 0: continue
            for j, n in enumerate(nr):
                if j == i or n is None or n < 1 or round(n * 10) != n * 10 or total <= n: continue   # 人數允許一位小數（年度平均）
                avg = total / n
                for k, a in enumerate(nr):
                    if k in (i, j) or a is None or a <= 0: continue
                    if ref_idx is not None and k != ref_idx and label == "sb14": continue   # sb14 的平均數就是參考欄
                    if ref_idx is not None and nr[ref_idx] and not (0.3 <= a / nr[ref_idx] <= 3): continue  # 平均數跟中位數同數量級
                    err = abs(a - avg) / a
                    if err < 0.02 and (best is None or err < best[0]): best = (err, i, j, k)
        if best: c2[best[1:]] += 1
    idx = vote(c2)
    DIAG.setdefault("cols", {})[label] = {"len": L, "ref_idx": ref_idx, "idx": idx, "votes": c2.most_common(3), "head": rows[0] if rows else None}
    out, bad = {}, 0
    if not idx: return out, len(rows), idx
    ti, ni, ai = idx
    for r, nr, code in zip(rows, nums, codes):
        total, n, a = nr[ti], nr[ni], nr[ai]
        if not code or total is None or n is None or a is None or n < 1 or round(n * 10) != n * 10 or abs(total / n - a) / a > 0.03:
            bad += 1; continue
        v = ref.get(code)
        if v is not None and ref_idx is not None and nr[ref_idx] is not None and abs(nr[ref_idx] - v * 10) / (v * 10) > 0.03:
            bad += 1; continue
        out[code] = [int(round(n)), round(total / 1e5, 2)]       # 仟元 → 億
    return out, bad, idx


def parse_sb15(rows, med_ref):
    o, b, _ = parse_generic(rows, med_ref, "sb15"); return o, b


def parse_sb14(rows, avg_ref):
    o, b, _ = parse_generic(rows, avg_ref, "sb14"); return o, b


def main():
    try:
        sal = json.loads((OUT / "salary.json").read_text("utf-8"))
    except Exception:
        print("沒有 salary.json，先跑 fetch_salary.py", file=sys.stderr); sys.exit(1)
    yr = sal.get("yr")
    try:
        old = json.loads((OUT / "headcount.json").read_text("utf-8"))
    except Exception:
        old = {}
    force = os.environ.get("FORCE", "") == "1"
    if not force and old.get("yr") == yr and not old.get("errors") and old.get("d"):
        print(f"headcount.json 已是 {yr} 年度且無錯誤，不重抓（FORCE=1 可強制）"); return
    med_ref = {c: v[0] for c, v in sal["d"].items() if v[0] is not None}
    avg_ref = {c: v[5] for c, v in sal["d"].items() if len(v) > 5 and v[5] is not None}
    d, errs, src, bad = {}, [], {}, {}
    for typek, mk in (("sii", "上市"), ("otc", "上櫃")):
        rows, s = fetch_table("t100sb15", typek, yr)
        if rows:
            p, b = parse_sb15(rows, med_ref); src[f"{mk} 非主管"] = f"{s} {len(rows)} 列→{len(p)} 檔"; bad[f"{mk} 非主管"] = b
            for c, v in p.items(): d.setdefault(c, [None] * 4)[0:2] = v
        else:
            errs.append(f"{mk} t100sb15 抓不到")
        time.sleep(3)
        rows, s = fetch_table("t100sb14", typek, yr)
        if rows:
            p, b = parse_sb14(rows, avg_ref); src[f"{mk} 全體"] = f"{s} {len(rows)} 列→{len(p)} 檔"; bad[f"{mk} 全體"] = b
            for c, v in p.items(): d.setdefault(c, [None] * 4)[2:4] = v
        else:
            errs.append(f"{mk} t100sb14 抓不到")
        time.sleep(3)
    DIAG["sources"], DIAG["bad"], DIAG["errors"] = src, bad, errs
    for c in ("2330", "2454", "1301", "5274", "2002", "2317"):
        if c in d: print(f"  {c}: 非主管 {d[c][0]} 人、薪資總額 {d[c][1]} 億；全體 {d[c][2]} 人、薪資費用 {d[c][3]} 億")
    (OUT / "headcount_diag.json").write_text(json.dumps(DIAG, ensure_ascii=False, indent=1), "utf-8")
    print(f"來源：{src}；解析失敗：{bad}；錯誤：{errs}")
    if not d:
        print("全部抓不到，保留舊檔", file=sys.stderr); sys.exit(1)
    for c, v in (old.get("d") or {}).items():       # 某張表失敗 → 沿用上一版那張表的欄位
        x = d.setdefault(c, [None] * 4)
        for i in range(4):
            if x[i] is None and v[i] is not None: x[i] = v[i]
    changed = old.get("d") != d or old.get("yr") != yr
    if not changed and not errs:
        print("內容沒有變動，不寫檔"); return
    now = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
    n1 = sum(1 for v in d.values() if v[0] is not None); n2 = sum(1 for v in d.values() if v[2] is not None)
    out = dict(updated=now if changed else old.get("updated", now), yr=yr, yrAD=yr + 1911 if yr else None,
               fields=["nFull", "payFull", "nAll", "payAll"], sources=src, errors=errs, stats={"nFull": n1, "nAll": n2}, d=d)
    (OUT / "headcount.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
    if yr and changed:
        (OUT / "headcount").mkdir(exist_ok=True)
        (OUT / "headcount" / f"{yr}.json").write_text(json.dumps({"yr": yr, "updated": now, "d": d}, ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"headcount.json: {len(d)} 檔（非主管人數 {n1}、全體人數 {n2}），年度 {yr}")


if __name__ == "__main__":
    main()
