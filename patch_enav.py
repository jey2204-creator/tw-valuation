#!/usr/bin/env python3
"""2026-11-15 編輯主題頁（#e/<id>）加「‹ 3/12 ▾ ›」上下主題切換。
- 順序＝首頁產業主題順序（allThemes()，含已隱藏、灰色；自動主題不能編輯所以跳過），頭尾循環
- 有改動才自動儲存再切換（沒改不存，內建主題不會被標成「已修改」）；切換後標題下方顯示「已儲存 X〔復原〕」6 秒
- 點中間「3/12 ▾」展開主題清單直接跳；切換用 location.replace，不堆瀏覽紀錄
用法：python3 patch_enav.py → beta.html；python3 patch_enav.py prod → index.html
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
s=open('index.html',encoding='utf-8').read()
def rep(old,new):
    global s
    assert s.count(old)==1,(s.count(old),old[:60]);s=s.replace(old,new)

# 1) CSS
rep('.ebar{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}',
 '.ebar{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}\n'
 '.enav{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:6px}.enav h1{font-size:22px;margin:0;white-space:nowrap}\n'
 '.esw{display:flex;gap:6px;flex:none}.esw .ib{height:38px;min-width:42px;font-size:15px;white-space:nowrap}.esw .ib.arw{font-size:20px;line-height:1}.esw .ib.off{color:var(--muted)}\n'
 '#eNavList{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px}#eNavList[hidden]{display:none}\n'
 '#eNavList .ib{height:auto;min-height:38px;padding:6px 8px;justify-content:flex-start;text-align:left;white-space:normal;line-height:1.25;font-size:14px}\n'
 '#eNavList .ib.cur{background:var(--accent);border-color:var(--accent);color:var(--card);font-weight:700}#eNavList .ib.off{opacity:.5}#eNavList .ib small{margin-left:4px;font-size:11px;opacity:.8}\n'
 '#eToast{display:flex;align-items:center;gap:8px;margin-top:8px;padding:6px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card);font-size:13px}#eToast[hidden]{display:none}#eToast span{flex:1;min-width:0}')

# 2) HTML：標題列＋切換器＋清單＋復原提示
rep('  <h1 style="font-size:22px;margin:6px 0 0" id="eTitle">編輯主題</h1>',
 '  <div class="enav"><h1 id="eTitle">編輯主題</h1><div class="esw" id="eNav" hidden><button type="button" class="ib arw" id="ePrev" aria-label="上一個主題">‹</button><button type="button" class="ib" id="ePos" aria-expanded="false" aria-controls="eNavList"></button><button type="button" class="ib arw" id="eNext" aria-label="下一個主題">›</button></div></div>\n'
 '  <div id="eNavList" hidden></div>\n'
 '  <div id="eToast" role="status" hidden><span id="eToastT"></span><button type="button" class="ib" id="eUndo">復原</button></div>')

# 3) openEditor：畫切換器、記下開啟時的內容（判斷有沒有改）
rep("  drawStocks();if(isNew)setTimeout(()=>$('eName').focus(),50);\n}",
 "  drawStocks();if(isNew)setTimeout(()=>$('eName').focus(),50);\n"
 "  if(!isNew&&t.hidden)$('eKind').textContent+='・已隱藏';\n"
 "  ED.snap=edSnap();eNavPaint();if(!eNavKeep)eToastHide();eNavKeep=false;\n}\n"
 "// ---- 上下主題切換（‹ N/M ▾ ›）：順序＝首頁順序，含已隱藏；自動主題不能編輯，跳過 ----\n"
 "let eNavKeep=false,eUndoCfg,eToastTm=0;\n"
 "const eNavIds=()=>allThemes().filter(t=>!t.auto);\n"
 "const edSnap=()=>JSON.stringify([$('eName').value.trim(),$('eUS').value.toUpperCase().split(/[\\s,，、]+/).filter(Boolean),ED.stocks.map(([a,r])=>[a,(r||'').trim()])]);\n"
 "function eNavPaint(){\n"
 "  const A=eNavIds(),i=A.findIndex(t=>t.id===ED.id),ok=!ED.isNew&&i>=0&&A.length>1;\n"
 "  $('eNav').hidden=!ok;$('eNavList').hidden=true;$('ePos').setAttribute('aria-expanded','false');if(!ok)return;\n"
 "  $('ePos').textContent=`${i+1}/${A.length} ▾`;$('ePos').classList.toggle('off',!!A[i].hidden);\n"
 "  $('eNavList').innerHTML=A.map(t=>`<button type=\"button\" class=\"ib${t.id===ED.id?' cur':''}${t.hidden?' off':''}\" data-go=\"${t.id}\">${esc(t.name)}${t.hidden?'<small>已隱藏</small>':''}</button>`).join('');\n"
 "}\n"
 "function eToastHide(){clearTimeout(eToastTm);$('eToast').hidden=true;eUndoCfg=undefined}\n"
 "function eGo(id){\n"
 "  if(!ED||ED.isNew||id===ED.id)return;syncRoles();\n"
 "  if(edSnap()!==ED.snap){   // 有改才存\n"
 "    const prev=JSON.parse(JSON.stringify(store.get('themeCfg')||null)),nm=$('eName').value.trim();\n"
 "    if(!edCommit()){$('eNavList').hidden=true;return}\n"
 "    clearTimeout(eToastTm);eUndoCfg=prev;$('eToastT').textContent=`已儲存「${nm}」`;$('eUndo').hidden=false;$('eToast').hidden=false;\n"
 "    eToastTm=setTimeout(eToastHide,6000);eNavKeep=true;\n"
 "  }\n"
 "  location.replace('#e/'+id);\n"
 "}\n"
 "function eStep(d){const A=eNavIds(),i=A.findIndex(t=>t.id===ED.id);if(i<0||A.length<2)return;eGo(A[(i+d+A.length)%A.length].id)}\n"
 "$('ePrev').addEventListener('click',()=>eStep(-1));$('eNext').addEventListener('click',()=>eStep(1));\n"
 "$('ePos').addEventListener('click',()=>{const o=$('eNavList').hidden;$('eNavList').hidden=!o;$('ePos').setAttribute('aria-expanded',o?'true':'false')});\n"
 "$('eNavList').addEventListener('click',e=>{const b=e.target.closest('button[data-go]');if(!b)return;if(b.dataset.go===ED.id){$('eNavList').hidden=true;return}eGo(b.dataset.go)});\n"
 "$('eUndo').addEventListener('click',()=>{if(eUndoCfg===undefined)return;const c=eUndoCfg,cur=ED&&!ED.isNew&&edSnap()===ED.snap?ED.id:null;\n"
 "  if(c)cfgSave(c);else{try{localStorage.removeItem('themeCfg')}catch(e){}store.set('themeCfg',null);applyCfg()}\n"
 "  clearTimeout(eToastTm);eUndoCfg=undefined;$('eToastT').textContent='已復原，剛才的改動沒有存';$('eUndo').hidden=true;eToastTm=setTimeout(eToastHide,3000);\n"
 "  if(cur&&allThemes().some(t=>t.id===cur)){eNavKeep=true;openEditor(cur)}else eNavPaint()});")

# 4) 儲存邏輯抽成 edCommit()，「儲存」鈕與切換共用
rep("$('eSave').addEventListener('click',()=>{\n  syncRoles();const name=$('eName').value.trim();\n  if(!name){$('eMsg').textContent='請填主題名稱';$('eName').focus();return}\n  if(!ED.stocks.length){$('eMsg').textContent='請至少加入一檔股票';$('eQ').focus();return}",
 "function edCommit(){\n  syncRoles();const name=$('eName').value.trim();\n  if(!name){$('eMsg').textContent='請填主題名稱';$('eName').focus();return false}\n  if(!ED.stocks.length){$('eMsg').textContent='請至少加入一檔股票';$('eQ').focus();return false}")
rep("  if(ED.isNew)c.order=[...c.order.filter(i=>i!==ED.id),ED.id];\n  cfgSave(c);location.hash='t/'+ED.id;\n});",
 "  if(ED.isNew)c.order=[...c.order.filter(i=>i!==ED.id),ED.id];\n  cfgSave(c);return true;\n}\n$('eSave').addEventListener('click',()=>{if(edCommit())location.hash='t/'+ED.id});")

rep('<span style="opacity:.5">v1115k</span>','<span style="opacity:.5">v1115l</span>')
if not prod:s=s.replace('<title>','<title>[beta] ',1)
open('index.html' if prod else 'beta.html','w',encoding='utf-8').write(s);print('ok')
