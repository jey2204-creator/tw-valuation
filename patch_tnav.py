#!/usr/bin/env python3
"""2026-11-15 主題瀏覽頁（#t/<id>）頂列中間加「‹ 9/14 ▾ ›」上下主題切換。
- 範圍＝首頁看得到的主題（THEMES：含注意／處置等自動主題、不含已隱藏），順序同首頁，頭尾循環
- 「✏️ 編輯這個主題」縮成「✏️ 編輯」讓位；點中間展開兩欄主題清單直接跳
- 切換後保留目前排序欄位（TKEEP）與模式；用 location.replace，不堆瀏覽紀錄
用法：python3 patch_tnav.py → beta.html；python3 patch_tnav.py prod → index.html
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
s=open('index.html',encoding='utf-8').read()
def rep(old,new):
    global s
    assert s.count(old)==1,(s.count(old),old[:60]);s=s.replace(old,new)

rep('#eNavList{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px}#eNavList[hidden]{display:none}\n',
    '#eNavList,#tNavList{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px}#eNavList[hidden],#tNavList[hidden]{display:none}\n'
    '.tsw{display:flex;gap:5px;flex:none;margin-left:auto}.tsw .ib{height:32px;min-width:36px;padding:0 8px;font-size:14px;white-space:nowrap}.tsw .ib.arw{font-size:19px;line-height:1}#tEdit{margin-left:10px;white-space:nowrap}\n'
    '#tNavList .ib{height:auto;min-height:38px;padding:6px 8px;justify-content:flex-start;text-align:left;white-space:normal;line-height:1.25;font-size:14px}\n'
    '#tNavList .ib.cur{background:var(--accent);border-color:var(--accent);color:var(--card);font-weight:700}\n')
rep('<a href="#">← 全部主題</a><a id="tEdit" href="#">✏️ 編輯這個主題</a></div>',
    '<a href="#" style="white-space:nowrap">← 全部主題</a><span class="tsw" id="tNav" hidden><button type="button" class="ib arw" id="tPrev" aria-label="上一個主題">‹</button><button type="button" class="ib" id="tPos" aria-expanded="false" aria-controls="tNavList"></button><button type="button" class="ib arw" id="tNext" aria-label="下一個主題">›</button></span><a id="tEdit" href="#" aria-label="編輯這個主題">✏️ 編輯</a></div>\n'
    '  <div id="tNavList" hidden></div>')
rep("$('tTbl').dataset.sort='';$('tTbl').dataset.note=t.auto?'1':'';","$('tTbl').dataset.sort=TKEEP||'';TKEEP='';$('tTbl').dataset.note=t.auto?'1':'';")
rep("function stockExtras(id){",
 "// ---- 主題頁上下主題切換（‹ N/M ▾ ›）：首頁看得到的主題、同首頁順序；切換保留排序 ----\n"
 "var TKEEP='';\n"
 "{const _st=showTheme;showTheme=function(tid){_st(tid);const i=THEMES.findIndex(t=>t.id===tid),ok=i>=0&&THEMES.length>1;\n"
 "  $('tNav').hidden=!ok;$('tNavList').hidden=true;$('tPos').setAttribute('aria-expanded','false');if(!ok)return;$('tNav').dataset.id=tid;\n"
 "  $('tPos').textContent=`${i+1}/${THEMES.length} ▾`;\n"
 "  $('tNavList').innerHTML=THEMES.map(t=>`<button type=\"button\" class=\"ib${t.id===tid?' cur':''}\" data-go=\"${t.id}\">${esc(t.name)}</button>`).join('')}}\n"
 "function tGo(id){if(id===$('tNav').dataset.id){$('tNavList').hidden=true;return}TKEEP=$('tTbl').dataset.sort||'';location.replace('#t/'+id)}\n"
 "function tStep(d){const i=THEMES.findIndex(t=>t.id===$('tNav').dataset.id);if(i<0)return;tGo(THEMES[(i+d+THEMES.length)%THEMES.length].id)}\n"
 "$('tPrev').addEventListener('click',()=>tStep(-1));$('tNext').addEventListener('click',()=>tStep(1));\n"
 "$('tPos').addEventListener('click',()=>{const o=$('tNavList').hidden;$('tNavList').hidden=!o;$('tPos').setAttribute('aria-expanded',o?'true':'false')});\n"
 "$('tNavList').addEventListener('click',e=>{const b=e.target.closest('button[data-go]');if(b)tGo(b.dataset.go)});\n"
 "function stockExtras(id){")
rep('<span style="opacity:.5">v1115l</span>','<span style="opacity:.5">v1115m</span>')
if not prod:s=s.replace('<title>','<title>[beta] ',1)
open('index.html' if prod else 'beta.html','w',encoding='utf-8').write(s);print('ok')
