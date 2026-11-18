#!/usr/bin/env python3
"""2026-11-18 首頁「產業主題」排行表加序號（灰色小字、主題名稱左側、跟著目前顯示順序／欄位排序重編），
編輯主題頁（#e）排序清單同步顯示同一組序號（已隱藏的主題顯示「–」，不佔號）。
用法：python3 patch_tno.py → beta.html；python3 patch_tno.py prod → index.html
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
s=open('index.html',encoding='utf-8').read()
def rep(old,new):
    global s
    assert s.count(old)==1,(s.count(old),old[:60]);s=s.replace(old,new)
# CSS
rep(".tlt td:first-child{white-space:normal;font-family:var(--f-body);max-width:108px}",
    ".tlt td:first-child{white-space:normal;font-family:var(--f-body);max-width:none}\n"
    ".tbl.tlw{margin-left:-11px}\n"
    ".tlt .tc{display:grid;grid-template-columns:var(--tnw,13px) 104px;column-gap:3px}\n"
    ".tlt .tno{font-family:var(--f-num);font-size:10.5px;color:var(--muted);text-align:right;line-height:1.65;opacity:.85;font-variant-numeric:tabular-nums;letter-spacing:-.3px}\n"
    ".tlt th:first-child{padding-left:calc(var(--tnw,13px) + 6px)}\n"
    "#olist .ono{flex:0 0 15px;margin-left:-8px;font-family:var(--f-num);font-size:11px;color:var(--muted);text-align:right;font-variant-numeric:tabular-nums;letter-spacing:-.3px}")
# 首頁排行表：序號＝目前顯示位次
rep("""<div class="panel"><div class="tbl"><table class="lst tlt"><thead>""","""<div class="panel"><div class="tbl tlw"><table class="lst tlt" style="--tnw:${rows.length>99?19:13}px"><thead>""")
rep("""'')+'</tbody></table></div></div>';
  el.onclick=e=>{const h=e.target.closest('th[data-tk]')""","""'')+'</tbody></table></div></div>';
  el.querySelectorAll('.tno').forEach((x,i)=>x.textContent=i+1);
  el.onclick=e=>{const h=e.target.closest('th[data-tk]')""")
rep("""<tr data-t="${t.id}"><td><span class="tn">${dm?dm[1]:nm}</span><span class="tm">${dm?`${dm[2]}・`:''}${meta}</span></td>""",
    """<tr data-t="${t.id}"><td><div class="tc"><span class="tno"></span><div><span class="tn">${dm?dm[1]:nm}</span><span class="tm">${dm?`${dm[2]}・`:''}${meta}</span></div></div></td>""")
# 編輯主題頁：同一組序號（隱藏的不佔號）
rep("""  const A=allThemes();
  $('olist').innerHTML=A.map((t,i)=>`<div class="erow ${t.hidden?'off':''}" data-id="${t.id}">
    <a class="grow\"""","""  const A=allThemes();let ono=0;
  $('olist').innerHTML=A.map((t,i)=>`<div class="erow ${t.hidden?'off':''}" data-id="${t.id}">
    <span class="ono">${t.hidden?'–':++ono}</span><a class="grow\"""")
rep('<span style="opacity:.5">v1117c</span>','<span style="opacity:.5">v1118c</span>')
if not prod:s=s.replace('<title>','<title>[beta] ',1)
open('index.html' if prod else 'beta.html','w',encoding='utf-8').write(s);print('ok')
