#!/usr/bin/env python3
"""2026-11-09 放大卡底邊貼 Safari 工具列上緣：遮罩高度改用 visualViewport（看得見的視窗）算，
top＝產業列底邊、bottom＝視窗底被工具列蓋掉的部分；卡片最後兩行（資料來源、N／M）不再被網址列蓋住。
工具列收放／轉向／捲動時重算。用法：python3 patch_shvv.py beta_scan.html beta_scan.html
"""
import sys
src,dst=sys.argv[1],sys.argv[2];s=open(src,encoding='utf-8').read()
def rep(old,new,n=1):
    global s;assert s.count(old)==n,(s.count(old),old[:80]);s=s.replace(old,new)
rep('''.ov{top:var(--ovtop,0)}.ov .sh{max-height:100%}''',
    '''.ov{top:var(--ovtop,0);bottom:var(--ovbot,0)}.ov .sh{max-height:100%;padding-bottom:calc(12px + env(safe-area-inset-bottom))}''')
rep('''function ovTop(){const hd=document.querySelector('.hd');if(!hd)return;const b=Math.max(0,Math.round(hd.getBoundingClientRect().bottom));document.documentElement.style.setProperty('--ovtop',b+'px')}
addEventListener('resize',()=>{if(openI>=0)ovTop()});if(window.visualViewport)visualViewport.addEventListener('resize',()=>{if(openI>=0)ovTop()});''',
    '''function ovTop(){const hd=document.querySelector('.hd');if(!hd)return;const b=Math.max(0,Math.round(hd.getBoundingClientRect().bottom));document.documentElement.style.setProperty('--ovtop',b+'px');
  // 底邊：layout 視窗高 − 看得見的視窗底（Safari 網址列撐開時 visualViewport 比 innerHeight 矮，差額就是被蓋住的高度）
  const vv=window.visualViewport,bot=vv?Math.max(0,Math.round(innerHeight-(vv.height+vv.offsetTop))):0;document.documentElement.style.setProperty('--ovbot',bot+'px')}
addEventListener('resize',()=>{if(openI>=0)ovTop()});if(window.visualViewport){visualViewport.addEventListener('resize',()=>{if(openI>=0)ovTop()});visualViewport.addEventListener('scroll',()=>{if(openI>=0)ovTop()})}''')
open(dst,'w',encoding='utf-8').write(s);print('ok',len(s))
