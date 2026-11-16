#!/usr/bin/env python3
"""2026-11-17 編輯自選頁（#f）加搜尋框：輸入代號或名稱 → 點一下加入自選（可連續加），不用進個股頁按 ☆。
疊在 patch_favt.py（⭐ 自選股主題）之上。
用法：python3 patch_favt.py && python3 patch_fadd.py → beta.html
      python3 patch_favt.py prod && python3 patch_fadd.py prod → index.html
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
src='index.html' if prod else 'beta.html'
s=open(src,encoding='utf-8').read()
assert "const FAVT='_fav'" in s,'先跑 patch_favt.py'
def rep(old,new,n=1):
    global s
    assert s.count(old)==n,(s.count(old),old[:60]);s=s.replace(old,new)

# 1) 版面：標題加檔數、搜尋框放在清單上方（鍵盤彈出時結果不會被擋住）
rep('''  <h1 style="font-size:22px;margin:6px 0 0">編輯自選</h1>
  <p class="take">按住右邊 ⠿ 拖曳調整順序；按 ✕ 移除。新加入的自選會排在最後面。</p>
  <div class="panel" style="margin-top:12px" id="fRows"></div>''',
'''  <h1 style="font-size:22px;margin:6px 0 0">編輯自選 <small id="fCnt" style="font-size:14px;font-weight:400;color:var(--muted)"></small></h1>
  <p class="take">搜尋加入股票（排在最後面）；按住右邊 ⠿ 拖曳調整順序；按 ✕ 移除。</p>
  <div class="search" role="search" style="margin-top:10px">
    <svg viewBox="0 0 24 24" fill="none" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
    <input id="fQ" type="search" inputmode="search" autocomplete="off" placeholder="加入自選：輸入代號或名稱" aria-label="加入自選">
    <div class="results" id="fRes" hidden></div>
  </div>
  <p class="foot" id="fAddMsg" role="status" style="margin:6px 0 0"></p>
  <div class="panel" style="margin-top:8px" id="fRows"></div>''')

# 2) 清單：檔數、空清單提示
rep("  const f=store.get('fav')||[];\n  $('fRows').innerHTML=","  const f=store.get('fav')||[];$('fCnt').textContent=`${f.length}／30 檔`;\n  $('fRows').innerHTML=")
rep("還沒有自選。在個股頁點「☆ 加入自選」。</p>'","還沒有自選。在上面的搜尋框輸入代號或名稱加入。</p>'")

# 3) 搜尋加入
rep("$('eQ').addEventListener('input',eSearch);",
"""// ---- 編輯自選頁搜尋加入（2026-11-17）：加在最後、可連續加；滿 30 檔要先移除 ----
function fSearch(){
  const v=$('fQ').value.trim(),box=$('fRes');if(!v){box.hidden=true;return}
  const lv=v.toLowerCase(),has=new Set(store.get('fav')||[]);
  const hit=LIST.filter(s=>s[0].startsWith(v)||s[1].toLowerCase().includes(lv)).sort((a,b)=>(b[0].startsWith(v)-a[0].startsWith(v))||a[0].localeCompare(b[0])).slice(0,12);
  box.innerHTML=hit.length?hit.map(s=>has.has(s[0])?row(s).replace('<button','<button disabled').replace('</button>','<span class="rmeta">已在自選</span></button>'):row(s)).join(''):'<div class="rhead">找不到符合的股票</div>';box.hidden=false;
}
$('fQ').addEventListener('input',fSearch);
$('fQ').addEventListener('keydown',e=>{if(e.key==='Enter'){const b=$('fRes').querySelector('button:not([disabled])');if(b)b.click()}if(e.key==='Escape'){$('fRes').hidden=true}});
$('fRes').addEventListener('mousedown',e=>e.preventDefault());
$('fRes').addEventListener('click',e=>{const b=e.target.closest('button');if(!b||b.disabled)return;
  const id=b.dataset.id,f=store.get('fav')||[];if(f.includes(id))return;
  if(f.length>=30){$('fRes').hidden=true;$('fAddMsg').textContent='自選已滿 30 檔，先按 ✕ 移除不看的再加';return}
  store.set('fav',[...f,id]);applyCfg();$('fQ').value='';$('fRes').hidden=true;renderFav();$('fMsg').textContent='';
  $('fAddMsg').textContent=`已加入 ${nameOf(id)}（${f.length+1}／30），可以繼續輸入下一檔`;$('fQ').focus()});
$('eQ').addEventListener('input',eSearch);""")
rep("document.title='編輯自選';renderFav();","document.title='編輯自選';$('fQ').value='';$('fRes').hidden=true;$('fAddMsg').textContent='';$('fMsg').textContent='';renderFav();")

# 4) 自選股主題頁的說明跟著改
rep("在個股頁按「☆ 加入自選」就會進來；按右上「✏️ 編輯」可拖曳排序、移除。","按右上「✏️ 編輯」可搜尋加入、拖曳排序、移除；個股頁按 ☆ 也會進來。")
rep("還沒有自選：搜尋股票進個股頁，按「☆ 加入自選」就會出現在這裡。","還沒有自選：按右上「✏️ 編輯」搜尋加入，或在個股頁按「☆ 加入自選」。")

rep('<span style="opacity:.5">v1117a</span>','<span style="opacity:.5">v1117b</span>')
open(src,'w',encoding='utf-8').write(s);print('ok',src)
