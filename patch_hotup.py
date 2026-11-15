#!/usr/bin/env python3
"""2026-11-15 首頁入口清單：🔥 主力訊號搬到第 2 列（K 線掃描下面、注意／處置股上面）。純調順序。
用法：python3 patch_hotup.py → beta.html；python3 patch_hotup.py prod → index.html
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
s=open('index.html',encoding='utf-8').read()
a=s.index('  <details class="ind hot" id="hotBox">');b=s.index('  <details class="ind" id="aiBox" hidden>')
blk=s[a:b];assert blk.count('<details')==1 and blk.rstrip().endswith('</details>'),blk[-80:]
s=s[:a]+s[b:]
k='<a class="srlink" href="notice.html"><b>📢 注意／處置股</b>';assert s.count(k)==1
s=s.replace(k,'\n'+blk.rstrip()+'\n  '+k)
old='<span style="opacity:.5">v1115h</span>';assert s.count(old)==1;s=s.replace(old,'<span style="opacity:.5">v1115i</span>')
if not prod:s=s.replace('<title>','<title>[beta] ',1)
open('index.html' if prod else 'beta.html','w',encoding='utf-8').write(s);print('ok')
