#!/usr/bin/env python3
"""2026-11-15 掃描頁橫列拿掉「證交所產業 ▾」下拉（「全部▾」面板已有）：平常隱藏；
只有目前選的是證交所產業時才顯示（反白、當作目前所在的標示，也可直接換別的產業）。
用法：python3 patch_indhide.py → beta_scan_ih.html；python3 patch_indhide.py prod → scan.html
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
s=open('scan.html',encoding='utf-8').read()
def rep(old,new,n=1):
    global s;assert s.count(old)==n,(s.count(old),old[:90]);s=s.replace(old,new)
rep('''<select class="ch" id="indSel">''','''<select class="ch" id="indSel" hidden>''')
rep('''const s=$('indSel');s.classList.toggle('on',sel.kind==='i');if(sel.kind!=='i')s.value='';''','''const s=$('indSel');s.classList.toggle('on',sel.kind==='i');s.hidden=sel.kind!=='i';if(sel.kind!=='i')s.value='';else{s.value=sel.id;s.scrollIntoView({inline:'center',block:'nearest'})}''')
rep('''<span style="opacity:.5">v1115j</span>''','''<span style="opacity:.5">v1115k</span>''')
if not prod:s=s.replace('<title>','<title>[beta] ',1)
open('scan.html' if prod else 'beta_scan_ih.html','w',encoding='utf-8').write(s);print('ok')
