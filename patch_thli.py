#!/usr/bin/env python3
"""2026-11-15 掃描頁：細產業（主題／自選）也顯示「榜序」排序鈕＝照首頁主題表的成份股順序（含手機自訂順序）。
進細產業預設仍是日漲；在細產業點了榜序，換到別的細產業會沿用，從榜單（買超／注意／🔥）切回細產業則回日漲。
證交所產業（#i/）沒有主題順序，不顯示。K 線／估值兩種模式都適用。
用法：python3 patch_thli.py → beta_scan_li.html；python3 patch_thli.py prod → scan.html（只能套一次）
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
s=open('scan.html',encoding='utf-8').read()
def rep(old,new,n=1):
    global s;assert s.count(old)==n,(s.count(old),old[:90]);s=s.replace(old,new)

rep('''$('sortLi').hidden=!isN;if(isN&&!RANKED)sortK='li';else if(!isN&&sortK==='li')sortK=MODE==='v'?'peh':'chg';RANKED=isN;paintBar();''',
'''const isTh=sel.kind==='t'&&!isN;$('sortLi').hidden=!(isN||isTh);$('sortLi').title=isTh?'照首頁主題表的成份股順序':'照名單順序（第 1～20 名）';
  if(isN&&!RANKED)sortK='li';else if(!isN&&sortK==='li'&&(RANKED||!isTh))sortK=MODE==='v'?'peh':'chg';RANKED=isN;paintBar();''')
rep('''只在這些名單出現、進入時預設''','''這些名單進入時預設；細產業／自選也有「榜序」＝照首頁主題表的成份股順序，進入時預設仍是日漲''')
rep('''<span style="opacity:.5">v1115k</span>''','''<span style="opacity:.5">v1115m</span>''')
if not prod:s=s.replace('<title>','<title>[beta] ',1)
open('scan.html' if prod else 'beta_scan_li.html','w',encoding='utf-8').write(s);print('ok')
