#!/usr/bin/env python3
"""2026-11-15 首頁「🔥 主力訊號」控制列加「📈 掃K線」入口（連到 scan.html#fire）。
用法：python3 patch_fscanlink.py → beta.html；python3 patch_fscanlink.py prod → index.html
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
s=open('index.html',encoding='utf-8').read()
def rep(old,new,n=1):
    global s;assert s.count(old)==n,(s.count(old),old[:90]);s=s.replace(old,new)
rep('''    +(isNow?'<a class="ntm" href="fstats.html" style="text-decoration:none">📊 統計</a>':''',
    '''    +'<a class="ntm" href="scan.html#fire" style="text-decoration:none" title="用 3 欄小卡 K 線看這份名單（K 棒標上榜日）">K線 ›</a>'
    +(isNow?'<a class="ntm" href="fstats.html" style="text-decoration:none">📊 統計</a>':''')
# 控制列要維持一行（402pt）：膠囊縮短（K線／統計／最新·當日）、間距縮小
rep('''style="text-decoration:none">📊 統計</a>':`<button type="button" id="fhMode" class="ntm">數字 <i''','''style="text-decoration:none">統計</a>':`<button type="button" id="fhMode" class="ntm" title="數字：最新／當日"><i''')
rep('''#hotCtl{display:flex;align-items:center;gap:6px;''','''#hotCtl .ntm{padding:0 6px}#hotCtl{display:flex;align-items:center;gap:4px;''')
rep('''<span class="hsum"><b>🆕 ${nNew}</b>・續 ${hot.length-nNew}・⬇ ${drop.length}</span>''','''<span class="hsum"><b>🆕${nNew}</b>・續${hot.length-nNew}・⬇${drop.length}</span>''')
rep('''<span style="opacity:.5">v1115d</span>''','''<span style="opacity:.5">v1115g</span>''')
if not prod:s=s.replace('<title>','<title>[beta] ',1)
open('index.html' if prod else 'beta.html','w',encoding='utf-8').write(s);print('ok')
