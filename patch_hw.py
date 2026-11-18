#!/usr/bin/env python3
"""2026-11-18 自動主題名稱的日期括號全形→半形：「投信買超前20（11/18）」→「投信買超前20 (11/18)」
（投信／外資／土洋前20、注意／快達處置／處置／快結束／剛結束），並讓「自動／自訂／已修改」標籤不拆字。
疊在 patch_tno.py（序號）之上。
用法：python3 patch_tno.py && python3 patch_hw.py → beta.html
      python3 patch_tno.py prod && python3 patch_hw.py prod → index.html
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
f='index.html' if prod else 'beta.html'
s=open(f,encoding='utf-8').read()
def rep(old,new,n=1):
    global s
    assert s.count(old)==n,(s.count(old),old[:60]);s=s.replace(old,new)
rep("name:`${name}（${md}）`,auto:true","name:`${name} (${md})`,auto:true",2)
# 主題頁標題去掉名單日（注意名單有日期選單時）：全形／半形都認
rep("t.name.replace(/（[^）]*）$/,'')","t.name.replace(/\\s*[（(][^）)]*[）)]$/,'')")
rep(".tag{font-size:10.5px;",".tag{white-space:nowrap;font-size:10.5px;")
rep('<span style="opacity:.5">v1118c</span>','<span style="opacity:.5">v1118d</span>')
open(f,'w',encoding='utf-8').write(s);print('ok',f)
