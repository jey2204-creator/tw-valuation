#!/usr/bin/env python3
"""掃描頁切換鈕統一成沒有「·」的樣式（2026-11-15）：排行的「合併 上市 上櫃」與「ETF 含 不含」
（「日 週 月」「量比 值 量」已在 patch_volcyc.py 拿掉）。需先套過 patch_volcyc.py（v1115s）。
用法：python3 patch_nodot.py scan.html scan.html
"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()


def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:90])
    s = s.replace(old, new)


rep(".join(V?'':'·');b.classList.toggle('sm',V);", ".join('');b.classList.toggle('sm',V);")
rep(".sb button#rkM i{font-style:normal;font-weight:400;opacity:.45;padding:0 1px}", ".sb button#rkM i{font-style:normal;font-weight:400;opacity:.45;padding:0 3px}")
rep("\">含</i>·<i class=\"${RKE?'':'on'}\">不含</i>", "\">含</i><i class=\"${RKE?'':'on'}\">不含</i>")
rep(".cnt button#rkE i{font-style:normal;opacity:.45}", ".cnt button#rkE i{font-style:normal;opacity:.45;padding:0 2px}")
rep("第 3 行可切 <b>合併·上市·上櫃</b>，統計列的 <b>ETF 含·不含</b>", "第 3 行可切 <b>合併 上市 上櫃</b>，統計列的 <b>ETF 含 不含</b>")
rep("v1115s", "v1115t")
if dst.startswith('beta') and s.count('<title>') == 1 and '[beta]' not in s:
    s = s.replace('<title>', '<title>[beta] ')
open(dst, 'w', encoding='utf-8').write(s)
print('ok')
