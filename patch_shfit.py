#!/usr/bin/env python3
"""2026-11-09 估值放大卡兩張河流圖高度自動算：可視高度 − 其他內容高度，平分給兩張（110～210px），不用捲就一屏看完；
轉向／工具列收放重算。其他內容不變。用法：python3 patch_shfit.py beta_scan.html beta_scan.html
"""
import sys
src,dst=sys.argv[1],sys.argv[2];s=open(src,encoding='utf-8').read()
def rep(old,new,n=1):
    global s;assert s.count(old)==n,(s.count(old),old[:80]);s=s.replace(old,new)
rep('''.sh-cv.rv{height:210px}''','''.sh-cv.rv{height:var(--rvh,210px)}''')
rep('''  if(v){drawRiver($('shPe'),v,{kind:'pe'});drawRiver($('shPb'),v,{kind:'pb'});$('cycBtn').onclick=()=>cycToggle(r.c)}''',
    '''  if(v){fitRiv();drawRiver($('shPe'),v,{kind:'pe'});drawRiver($('shPb'),v,{kind:'pb'});$('cycBtn').onclick=()=>cycToggle(r.c)}''')
rep('''function fillSheetV(){''','''// 兩張河流圖的高度＝卡片可視高 − 其他內容高，平分，夾在 110～210px
function fitRiv(){const sh=$('sh'),a=$('shPe'),b=$('shPb');if(!a||!b)return;document.documentElement.style.setProperty('--rvh','0px');
  const pad=parseFloat(getComputedStyle(sh).paddingTop)+parseFloat(getComputedStyle(sh).paddingBottom),sp=parseFloat(getComputedStyle(sh,'::after').height)||0,avail=$('ov').clientHeight-pad,used=sh.scrollHeight-pad-sp;
  const h=Math.max(110,Math.min(210,Math.floor((avail-used-6)/2)));document.documentElement.style.setProperty('--rvh',h+'px')}
addEventListener('resize',()=>{if(openI>=0&&MODE==='v'&&$('shPe')){const v=VAL[SHR[openI].c];if(v){fitRiv();drawRiver($('shPe'),v,{kind:'pe'});drawRiver($('shPb'),v,{kind:'pb'})}}});
function fillSheetV(){''')
open(dst,'w',encoding='utf-8').write(s);print('ok',len(s))
