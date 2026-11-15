#!/usr/bin/env python3
"""2026-11-15 編輯主題頁（#e）加「↕ 還原預設排序」鈕：只清 themeCfg.order，
隱藏設定、改過的成份股、自訂主題都保留（自訂主題排到內建主題後面）；按完可「復原」。
用法：python3 patch_oreset.py → beta.html；python3 patch_oreset.py prod → index.html
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
s=open('index.html',encoding='utf-8').read()
def rep(old,new):
    global s
    assert s.count(old)==1,(s.count(old),old[:60]);s=s.replace(old,new)
rep('<div class="ebar"><a class="ib pri" href="#e/new">＋ 新增主題</a></div>',
    '<div class="ebar"><a class="ib pri" href="#e/new">＋ 新增主題</a><button type="button" class="ib" id="oReset">↕ 還原預設排序</button></div>\n'
    '  <p class="foot" id="oMsg" role="status"></p>')
rep("let resetArm=0;",
    "let oUndo=null;\n"
    "$('oReset').addEventListener('click',()=>{const c=cfgGet();if(!c.order.length){$('oMsg').textContent='目前已經是預設排序';return}\n"
    "  oUndo=c.order.slice();c.order=[];cfgSave(c);renderOrder();\n"
    "  $('oMsg').innerHTML='已還原成預設排序（上游→下游），成份股與自訂主題沒動　<button type=\"button\" class=\"ib\" id=\"oUndo\">復原</button>'});\n"
    "$('oMsg').addEventListener('click',e=>{if(!e.target.closest('#oUndo')||!oUndo)return;const c=cfgGet();c.order=oUndo;oUndo=null;cfgSave(c);renderOrder();$('oMsg').textContent='已復原成原本的排序'});\n"
    "let resetArm=0;")
rep('<span style="opacity:.5">v1115n</span>','<span style="opacity:.5">v1115o</span>')
if not prod:s=s.replace('<title>','<title>[beta] ',1)
open('index.html' if prod else 'beta.html','w',encoding='utf-8').write(s);print('ok')
