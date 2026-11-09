#!/usr/bin/env python3
"""2026-11-09 放大卡頂到產業列底框（方案①）：遮罩從產業列底邊開始，卡片最高到那條線（內容短就維持短）；
Safari 工具列收放／轉向時重算；卡片開著時點產業列切主題會先關卡片。K 線與估值卡同套。
用法：python3 patch_shtop.py beta_scan.html beta_scan.html
"""
import sys
src,dst=sys.argv[1],sys.argv[2];s=open(src,encoding='utf-8').read()
def rep(old,new,n=1):
    global s;assert s.count(old)==n,(s.count(old),old[:80]);s=s.replace(old,new)
rep('''.ov{position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:20;display:flex;align-items:flex-end}''',
    '''.ov{position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:20;display:flex;align-items:flex-end}
/* 2026-11-09 放大卡頂到產業列：遮罩 top 由 JS 設為產業列底邊，卡片最高佔滿遮罩 */
.ov{top:var(--ovtop,0)}.ov .sh{max-height:100%}''')
rep('''function openSheet(R,i){SHR=R;openI=i;$('ov').hidden=false;document.body.style.overflow='hidden';fillSheet()}''',
    '''function ovTop(){const hd=document.querySelector('.hd');if(!hd)return;const b=Math.max(0,Math.round(hd.getBoundingClientRect().bottom));document.documentElement.style.setProperty('--ovtop',b+'px')}
addEventListener('resize',()=>{if(openI>=0)ovTop()});if(window.visualViewport)visualViewport.addEventListener('resize',()=>{if(openI>=0)ovTop()});
function openSheet(R,i){SHR=R;openI=i;ovTop();$('ov').hidden=false;document.body.style.overflow='hidden';fillSheet()}''')
# 卡片開著時切主題／產業 → 先關卡片（產業列在遮罩之上仍可點）
rep('''$('ov').addEventListener('click',e=>{if(e.target===$('ov'))closeSheet()});''',
    '''$('ov').addEventListener('click',e=>{if(e.target===$('ov'))closeSheet()});
document.querySelector('.hd').addEventListener('click',()=>{if(openI>=0)closeSheet()},true);''')
# 產業列要壓在遮罩之上才點得到：z-index 高於 .ov
rep('''.hd{position:sticky;top:0;z-index:5;''','''.hd{position:sticky;top:0;z-index:21;''')
open(dst,'w',encoding='utf-8').write(s);print('ok',len(s))
