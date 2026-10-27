#!/usr/bin/env python3
"""連通性探測：GitHub Actions 能否抓到 MoneyDJ 系統的「法人持股明細」（投信估計持股張數）。
只讀，結果印成 Markdown（由 workflow 寫進 itrust/probe/fubon_<日期>.md）。
用法：python itrust/probe_fubon.py
"""
import datetime, html, re, sys, time, urllib.request

CODES = ["2330", "2486", "6510", "3357", "8103"]  # 上市大型、上市中小、上櫃（含投信有持股與無持股）
HOSTS = [
    "https://fubon-ebrokerdj.fbs.com.tw",   # 富邦 e 點通
    "https://jdata.yuanta.com.tw",          # 元大（同 MoneyDJ 系統，備援）
    "https://concords.moneydj.com",         # 康和（備援）
    "https://www.moneydj.com",              # MoneyDJ 本站（備援）
]
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
      "Accept-Language": "zh-TW,zh;q=0.9"}
DATE_RE = re.compile(r"^\d{3}/\d{2}/\d{2}$")


def decode(raw):
    for enc in ("cp950", "big5", "utf-8"):
        try:
            return raw.decode(enc)
        except Exception:
            pass
    return raw.decode("utf-8", "replace")


def cells(tr):
    out = []
    for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I):
        t = html.unescape(re.sub(r"<[^>]+>", "", td)).replace("\xa0", " ").strip()
        out.append(t)
    return out


def parse(text):
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S | re.I):
        c = cells(tr)
        if len(c) >= 11 and DATE_RE.match(c[0]):
            rows.append(c[:11])
    return rows


def fetch(url):
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, int((time.time() - t0) * 1000), decode(raw), len(raw)
    except urllib.error.HTTPError as e:
        return e.code, int((time.time() - t0) * 1000), "", 0
    except Exception as e:
        return "ERR", int((time.time() - t0) * 1000), str(e)[:100], 0


now = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
print(f"# MoneyDJ 法人持股明細 連通測試（{now:%Y-%m-%d %H:%M} 台灣時間）\n")
print("欄位：最新日期｜投信買賣超｜**投信估計持股(張)**｜外資估計持股(張)｜外資持股比重｜三大法人比重\n")
print("| 來源 | 代號 | HTTP | ms | 大小 | 解析列數 | 最新日期 | 投信買賣超 | 投信持股(張) | 外資持股(張) | 外資比重 | 三大法人比重 |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|")
ok_hosts = {}
samples = []
for host in HOSTS:
    ok = 0
    for code in CODES:
        url = f"{host}/z/zc/zcl/zcl_{code}.djhtm"
        st, ms, text, size = fetch(url)
        rows = parse(text) if st == 200 else []
        if rows:
            r = rows[0]
            ok += 1
            print(f"| {host.split('//')[1]} | {code} | {st} | {ms} | {size} | {len(rows)} | {r[0]} | {r[2]} | {r[6]} | {r[5]} | {r[9]} | {r[10]} |")
            if not samples or samples[-1][0] != host:
                samples.append((host, code, rows[:3]))
        else:
            note = text[:60].replace("\n", " ").replace("|", "/") if st != 200 else "無資料列"
            print(f"| {host.split('//')[1]} | {code} | {st} | {ms} | {size} | 0 | {note} | | | | | |")
        time.sleep(1.0)
    ok_hosts[host] = ok

print("\n## 小結\n")
for h, n in ok_hosts.items():
    print(f"- {h.split('//')[1]}：{n}/{len(CODES)} 檔成功")
print("\n## 原始列樣本（每個成功來源取前 3 列）\n")
for host, code, rows in samples:
    print(f"**{host.split('//')[1]} {code}**\n")
    for r in rows:
        print("- " + " ｜ ".join(r))
    print()
sys.exit(0)
