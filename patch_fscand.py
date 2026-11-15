#!/usr/bin/env python3
"""2026-11-15 掃描頁 🔥 名單可由網址帶日期：scan.html?d=YYYYMMDD#fire（首頁主力訊號「K線 ›」選了舊日期時用）。
帶進來後把 ?d= 從網址拿掉（之後在頁內換日期、重新整理不會被拉回去）。
用法：python3 patch_fscand.py → beta_scan_fd.html；python3 patch_fscand.py prod → scan.html
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
s=open('scan.html',encoding='utf-8').read()
def rep(old,new,n=1):
    global s;assert s.count(old)==n,(s.count(old),old[:90]);s=s.replace(old,new)
rep('''  pick(first);
}''','''  // 2026-11-15：?d=YYYYMMDD ＋ #fire → 直接開那一天的 🔥 名單（首頁主力訊號「K線 ›」帶過來）
  {const qd=(location.search.match(/[?&]d=(\\d{8})/)||[])[1];if(qd){if(first.kind==='t'&&first.id==='fire'&&FH&&FH.d[qd])NDATE=qd;
    try{const q=location.search.replace(/([?&])d=\\d{8}&?/,'$1').replace(/[?&]$/,'');history.replaceState(null,'',location.pathname+q+location.hash)}catch(e){}}}
  pick(first);
}''')
rep('''<span style="opacity:.5">v1115f</span>''','''<span style="opacity:.5">v1115h</span>''')
if not prod:s=s.replace('<title>','<title>[beta] ',1)
open('scan.html' if prod else 'beta_scan_fd.html','w',encoding='utf-8').write(s);print('ok')
