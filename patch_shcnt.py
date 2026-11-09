#!/usr/bin/env python3
"""2026-11-09 放大卡 N／M 計數移到「財報・估值 →」同一列左側（可點＝下一檔），底部不再多一列。
估值卡：「20／21・下一檔 兆赫 ›」；K 線卡（同列還有 2／4／6月鈕）：「20／21・兆赫 ›」。最後一檔：「21／21・最後一檔」。
用法：python3 patch_shcnt.py beta_scan.html beta_scan.html
"""
import sys
src,dst=sys.argv[1],sys.argv[2];s=open(src,encoding='utf-8').read()
def rep(old,new,n=1):
    global s;assert s.count(old)==n,(s.count(old),old[:80]);s=s.replace(old,new)
rep('''.sh-seg a{margin-left:auto;background:var(--accent);border-color:var(--accent);color:#fff;font-weight:700}''',
    '''.sh-seg a{margin-left:auto;background:var(--accent);border-color:var(--accent);color:#fff;font-weight:700}
/* 2026-11-09 計數＋下一檔 放在按鈕列左側 */
.sh-seg .cnt2{display:inline-flex;align-items:center;gap:3px;height:26px;font:600 11.5px var(--f-num);color:var(--muted);white-space:nowrap;min-width:0;overflow:hidden;text-overflow:ellipsis;padding:0 2px}
.sh-seg .cnt2 button{height:26px;line-height:26px;padding:0 4px;border:0;border-radius:6px;color:var(--accent);font:700 12px var(--f-body)}
.sh-seg .cnt2 button:disabled{color:var(--muted);font-weight:600}''')
# 共用：產生計數片段
rep('''function fillSheet(){return MODE==='v'?fillSheetV():fillSheetK()}''',
    '''function fillSheet(){return MODE==='v'?fillSheetV():fillSheetK()}
function shCnt(long){const last=openI>=SHR.length-1;return `<span class="cnt2">${openI+1}／${SHR.length}・<button id="shNext2" ${last?'disabled':''}>${last?'最後一檔':(long?'下一檔 ':'')+esc(SHR[openI+1].n)+' ›'}</button></span>`}''')
# 估值卡：計數進按鈕列，拿掉底部 sh-nav
rep('''    <div class="sh-seg"><a href="index.html#${esc(r.c)}">財報・估值 →</a></div>
    <div class="sh-nav"><span>${openI+1}／${SHR.length}${openI<SHR.length-1?'・下一檔 '+esc(SHR[openI+1].n):''}</span></div>`;''',
    '''    <div class="sh-seg">${shCnt(true)}<a href="index.html#${esc(r.c)}">財報・估值 →</a></div>`;''')
# K 線卡
rep('''<a href="index.html#${esc(r.c)}">財報・估值 →</a></div>
    <div class="sh-nav"><span>${openI+1}／${SHR.length}${openI<SHR.length-1?'・下一檔 '+esc(SHR[openI+1].n):''}</span></div>`;''',
    '''${shCnt(false)}<a href="index.html#${esc(r.c)}">財報・估值 →</a></div>`;''')
# 下一檔鈕事件（兩處 shNext 綁定旁邊加）
rep('''$('shNext').onclick=()=>{openI++;fillSheet();$('sh').scrollTop=0};''',
    '''$('shNext').onclick=()=>{openI++;fillSheet();$('sh').scrollTop=0};const n2=$('shNext2');if(n2)n2.onclick=()=>{openI++;fillSheet();$('sh').scrollTop=0};''',2)
# K 線卡的 .sh-seg button 事件只綁有 data-n 的
rep('''$('sh').querySelectorAll('.sh-seg button').forEach(b=>b.onclick=''','''$('sh').querySelectorAll('.sh-seg button[data-n]').forEach(b=>b.onclick=''')
open(dst,'w',encoding='utf-8').write(s);print('ok',len(s))
