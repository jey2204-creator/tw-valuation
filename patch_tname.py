#!/usr/bin/env python3
"""2026-11-22 batch20 美股首頁主題排行表：主題欄 92→74px、表格內主題名只顯示「/」前面（完整名稱放 title、主題頁照舊）
目的：營收欄往左移 18px，393px 寬手機（使用者 iPhone）最右「美−台」欄不再被切
用法：python3 patch_tname.py → us/index_test.html；python3 patch_tname.py prod → us/index.html
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
s=open('us/index.html',encoding='utf-8').read()
def rep(a,b):
    global s
    assert s.count(a)==1,(s.count(a),a[:70]);s=s.replace(a,b)
rep(".tlt td:first-child{max-width:92px}",".tlt td:first-child{max-width:74px}")
rep('return `<tr data-t="${t.id}"><td><span class="tn">${esc(t.name.replace(/^\\p{Extended_Pictographic}\\uFE0F?\\s*/u,\'\'))}</span>',
    # 表格窄：「資訊服務/軟體」只顯示「資訊服務」，完整名稱長按看（主題頁照舊顯示全名）
    'const fn=t.name.replace(/^\\p{Extended_Pictographic}\\uFE0F?\\s*/u,\'\'),sn=fn.split(\'/\')[0].trim()||fn;\n'
    '    return `<tr data-t="${t.id}"><td title="${esc(fn)}"><span class="tn">${esc(sn)}</span>')
if prod:open('us/index.html','w',encoding='utf-8').write(s);print('prod ok');sys.exit()
open('us/index_test.html','w',encoding='utf-8').write(s.replace('<title>','<title>[測試] ',1));print('test ok')
