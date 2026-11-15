#!/usr/bin/env python3
"""2026-11-15 編輯主題頁（#e/<id>）成份股列改「單行式」：每檔約 73pt → 43pt。
- 一列＝［名稱／代號（上下疊，固定 76px）］［角色備註輸入框］［✕］［⠿］
- 備註框字級 14 → 16px（iPhone Safari 點進去不會自動放大畫面），靠縮上下留白省高度
- 名稱太長（6 字以上）自動縮字、最多折兩行，不切成「…」
- 只動 #eStocks 這張表；自選、主題排序那兩張 .erow 不變
用法：python3 patch_erow.py → beta.html；python3 patch_erow.py prod → index.html
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
s=open('index.html',encoding='utf-8').read()
def rep(old,new):
    global s
    assert s.count(old)==1,(s.count(old),old[:60]);s=s.replace(old,new)

# 1) CSS
rep(".erow .cd{font-family:var(--f-num);font-size:11.5px;color:var(--muted);font-weight:400}",
 ".erow .cd{font-family:var(--f-num);font-size:11.5px;color:var(--muted);font-weight:400}\n"
 "/* 編輯主題成份股：單行式（2026-11-15） */\n"
 "#eStocks .erow{padding:4px 0}\n"
 "#eStocks .nm{flex:none;width:76px;min-width:0;display:flex;flex-direction:column;line-height:1.2}\n"
 "#eStocks .nm b{font-size:14.5px;overflow-wrap:anywhere}#eStocks .nm b.s{font-size:12.5px}#eStocks .nm b.xs{font-size:11.5px}\n"
 "#eStocks .erow input{flex:1;width:auto;font-size:16px;line-height:20px;height:32px;padding:5px 7px}\n"
 "#eStocks .drag{width:34px;height:34px;margin-left:2px}")

# 2) 列的 HTML
rep("""    <div class="grow"><b>${esc(nameOf(c))} <span class="cd">${c}</span></b><input data-i="${i}" id="role-${c}" value="${esc(r)}" placeholder="角色備註（選填）" aria-label="${esc(nameOf(c))} 角色備註"></div>""",
 """    <div class="nm"><b class="${eNmCls(nameOf(c))}">${esc(nameOf(c))}</b><span class="cd">${c}</span></div><input data-i="${i}" id="role-${c}" value="${esc(r)}" placeholder="角色備註" aria-label="${esc(nameOf(c))} 角色備註">""")
rep("function drawStocks(){",
 "function eNmCls(n){let w=0;for(const ch of String(n))w+=ch.charCodeAt(0)>255?1:.55;return w<=5?'':w<=6?'s':'xs'}\n"
 "function drawStocks(){")

rep('<span style="opacity:.5">v1115m</span>','<span style="opacity:.5">v1115n</span>')
if not prod:s=s.replace('<title>','<title>[beta] ',1)
open('index.html' if prod else 'beta.html','w',encoding='utf-8').write(s);print('ok')
