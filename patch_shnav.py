#!/usr/bin/env python3
"""2026-11-09 放大卡導覽移到標題列（方案①）：‹ › 上下一檔鈕放在釘住的標題列，任何捲動位置都點得到；
底部「‹ 上一檔 N／M 下一檔 ›」改成只剩 N／M 計數（仍在最底）。K 線與估值兩種放大卡同步。左右滑換檔保留。
用法：python3 patch_shnav.py scan.html beta_scan.html
"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:90])
    s = s.replace(old, new)

rep('''.sh-h{display:flex;align-items:center;gap:8px;margin-bottom:2px}
.sh-h b{font-size:18px;font-weight:900}
.sh-h .cd{font:600 12px var(--f-num);color:var(--muted)}
.sh-h .px{margin-left:auto;font:600 20px var(--f-num)}
.sh-h .chg{font:600 13px var(--f-num)}
.sh-h .x{font-size:22px;line-height:1;color:var(--muted);padding:2px 4px}''',
'''.sh-h{display:flex;align-items:center;gap:6px;margin:-8px -10px 2px;padding:8px 6px 6px 4px;position:sticky;top:-8px;z-index:3;background:var(--card);border-bottom:1px solid var(--line)}
.sh-h b{font-size:17px;font-weight:900;white-space:nowrap}
.sh-h .cd{font:600 12px var(--f-num);color:var(--muted)}
.sh-h .px{margin-left:auto;font:600 18px var(--f-num)}
.sh-h .chg{font:600 12px var(--f-num)}
.sh-h .x{font-size:22px;line-height:1;color:var(--muted);padding:2px 4px}
/* 2026-11-09 標題列上下一檔鈕：44px 觸控區、釘在頂端 */
.sh-h .nv{flex:none;width:34px;height:36px;border-radius:9px;background:var(--chip);color:var(--accent);font:900 22px/1 var(--f-num);display:flex;align-items:center;justify-content:center}
.sh-h .nv:disabled{opacity:.25;color:var(--muted)}
.sh-h .ct{font:600 11px var(--f-num);color:var(--muted);white-space:nowrap}
.sh-h .mid{display:flex;align-items:baseline;gap:5px;min-width:0;overflow:hidden}
@media (max-width:380px){.sh-h .cd{display:none}.sh-h .chg{display:none}}
.sh-nav{justify-content:center}''')

HDR_OLD_V = '''  $('sh').innerHTML=`<div class="sh-h"><b>${esc(r.n)}</b><span class="cd">${esc(r.c)}</span>${v&&v.cyc?'<span class="ntag" style="background:var(--warm)">循環股</span>':''}<span class="px ${cls(r.chg)}">${pxFmt(v?v.px:r.px)}</span><span class="chg ${cls(r.chg)}">${pct(r.chg,2)}</span><button class="x" id="shX" aria-label="關閉">×</button></div>'''
HDR_NEW_V = '''  $('sh').innerHTML=`<div class="sh-h"><button class="nv" id="shPrev" ${openI<=0?'disabled':''} aria-label="上一檔">‹</button><span class="mid"><b>${esc(r.n)}</b><span class="cd">${esc(r.c)}</span></span>${v&&v.cyc?'<span class="ntag" style="background:var(--warm)">循環股</span>':''}<span class="px ${cls(r.chg)}">${pxFmt(v?v.px:r.px)}</span><span class="chg ${cls(r.chg)}">${pct(r.chg,2)}</span><button class="nv" id="shNext" ${openI>=SHR.length-1?'disabled':''} aria-label="下一檔">›</button><button class="x" id="shX" aria-label="關閉">×</button></div>'''
rep(HDR_OLD_V, HDR_NEW_V)
HDR_OLD_K = '''  $('sh').innerHTML=`<div class="sh-h"><b>${esc(r.n)}</b><span class="cd">${esc(r.c)}</span>${ntag}${lvh}<span class="px ${cls(r.chg)}">${pxFmt(r.px)}</span><span class="chg ${cls(r.chg)}">${pct(r.chg,2)}</span><button class="x" id="shX" aria-label="關閉">×</button></div>'''
HDR_NEW_K = '''  $('sh').innerHTML=`<div class="sh-h"><button class="nv" id="shPrev" ${openI<=0?'disabled':''} aria-label="上一檔">‹</button><span class="mid"><b>${esc(r.n)}</b><span class="cd">${esc(r.c)}</span></span>${ntag}${lvh}<span class="px ${cls(r.chg)}">${pxFmt(r.px)}</span><span class="chg ${cls(r.chg)}">${pct(r.chg,2)}</span><button class="nv" id="shNext" ${openI>=SHR.length-1?'disabled':''} aria-label="下一檔">›</button><button class="x" id="shX" aria-label="關閉">×</button></div>'''
rep(HDR_OLD_K, HDR_NEW_K)
# 底部導覽改成只剩計數（兩處）
rep('''<div class="sh-nav"><button id="shPrev" ${openI<=0?'disabled style="visibility:hidden"':''}>‹ ${openI>0?esc(SHR[openI-1].n):''}</button><span>${openI+1}／${SHR.length}</span><button id="shNext" ${openI>=SHR.length-1?'disabled style="visibility:hidden"':''}>${openI<SHR.length-1?esc(SHR[openI+1].n):''} ›</button></div>''',
    '''<div class="sh-nav"><span>${openI+1}／${SHR.length}${openI<SHR.length-1?'・下一檔 '+esc(SHR[openI+1].n):''}</span></div>''', 2)
# 換檔後捲回頂端
rep('''$('shPrev').onclick=()=>{openI--;fillSheet()};$('shNext').onclick=()=>{openI++;fillSheet()};''',
    '''$('shPrev').onclick=()=>{openI--;fillSheet();$('sh').scrollTop=0};$('shNext').onclick=()=>{openI++;fillSheet();$('sh').scrollTop=0};''', 2)
open(dst, 'w', encoding='utf-8').write(s)
print('ok', len(s))
