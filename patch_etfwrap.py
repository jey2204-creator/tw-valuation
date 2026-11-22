#!/usr/bin/env python3
"""2026-11-22 21:06 📦 ETF 分類膠囊改兩行（世杰：「希望往右少滑一點」，選 ① 兩行排列，首頁＋掃描頁一起）。
.ecb 從單行橫向捲動（nowrap＋overflow-x）改成自動換行（flex-wrap:wrap，列距 5px）；選中自動捲動的程式留著（換行後不會捲，無害）。
用法：python3 patch_etfwrap.py       → beta_etfw.html＋beta_scan_etfw.html
      python3 patch_etfwrap.py prod  → index.html＋scan.html
頁尾版本用正規式換成 v1122w。
"""
import re, sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
OLD = ".ecb{display:flex;gap:4px;flex-wrap:nowrap;margin:6px 0 2px;overflow-x:auto;scrollbar-width:none}"
NEW = ".ecb{display:flex;gap:5px 4px;flex-wrap:wrap;margin:6px 0 2px}"
I_BETA = [("$('tScan').href='scan.html#'+encodeURIComponent(t.id);", "$('tScan').href=(t.id==='etf'?'beta_scan_etfw.html?v=1#':'scan.html#')+encodeURIComponent(t.id);"),
          ("location.href='scan.html#etf'", "location.href='beta_scan_etfw.html?v=1#etf'")]


def patch(src, dst, extra):
    s = open(src, encoding='utf-8').read()
    for a, b in [(OLD, NEW)] + ([] if prod else extra):
        assert s.count(a) == 1, (src, s.count(a), a[:60])
        s = s.replace(a, b)
    s, nv = re.subn(r'<span style="opacity:\.5">v11\d\d[a-z]</span>', '<span style="opacity:.5">v1122w</span>', s)
    assert nv == 1, (src, nv)
    if not prod:
        s = s.replace('<title>', '<title>[beta] ', 1)
    open(dst, 'w', encoding='utf-8').write(s)
    print('ok', dst)


patch('index.html', 'index.html' if prod else 'beta_etfw.html', I_BETA)
patch('scan.html', 'scan.html' if prod else 'beta_scan_etfw.html', [])
