#!/usr/bin/env python3
"""掃描頁成交值／成交量排行加「ETF 含·不含」開關（2026-11-15）
需先套過 patch_tvrank.py（v1115o）。用法：python3 patch_rketf.py scan.html beta_scan_etf.html
資料：rank.json 每天每個市場多存 vs／qs（不含 ETF 的前 50，fetch_rank.py）；舊資料沒有時退回「把含 ETF 的前 50 濾掉 ETF」（檔數會不足 50）。
"""
import sys, re
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()


def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:90])
    s = s.replace(old, new)


rep("let RK=null,RDAYS=[],RKM='a',RSETS={};", "let RK=null,RDAYS=[],RKM='a',RKE=true,RSETS={};")
rep("function rkList(k,D){const h=RK&&RK.hist[D];if(!h)return [];const L=(h.L&&h.L[k])||[],O=(h.O&&h.O[k])||[];",
    "function rkList(k,D){const h=RK&&RK.hist[D];if(!h)return [];const g=m=>{const o=h[m]||{};return RKE?(o[k]||[]):(o[k+'s']||(o[k]||[]).filter(x=>!/^00/.test(x[0])))},L=g('L'),O=g('O');")
rep("function rkSet(k,D){const key=k+RKM+D;", "function rkSet(k,D){const key=k+RKM+(RKE?1:0)+D;")
rep("連續 ${n} 天上榜${/^00/.test(c)?'・ETF':''}`", "連續 ${n} 天上榜${/^00/.test(c)?'・ETF':''}${RKE?'':'（不含 ETF 的排名）'}`")
rep("try{const m=localStorage.getItem('scanRkM');if(m==='L'||m==='O')RKM=m}catch(e){}",
    "try{const m=localStorage.getItem('scanRkM');if(m==='L'||m==='O')RKM=m;RKE=localStorage.getItem('scanRkE')!=='0'}catch(e){}")
rep("  rkPaint();\n  $('themes').innerHTML=",
    "  rkPaint();\n  $('cnt').addEventListener('click',e=>{if(e.target.closest('#rkE')){RKE=!RKE;try{localStorage.setItem('scanRkE',RKE?'1':'0')}catch(x){}pick(cur)}});\n  $('themes').innerHTML=")

# 統計列：改成共用函式 rkZ()（K 線、估值模式都顯示），中間放「ETF 含·不含」開關
m = re.search(r"  const rz=PMAP&&\(TOPK==='v'\|\|TOPK==='q'\)\?.*?\(Object\.values\(PMAP\)\):'';\n", s, re.S)
assert m and s.count(m.group(0)) == 1
s = s.replace(m.group(0), "  const rz=rkZ();\n")
rep("function valCnt(){",
    "// 2026-11-15：排行名單統計列第一行（含「ETF 含·不含」開關）\n"
    "function rkZ(){if(!(PMAP&&(TOPK==='v'||TOPK==='q')))return '';const v=Object.values(PMAP),e=v.filter(x=>/^00/.test(x.c)).length,o=v.filter(x=>MKT[x.c]==='上櫃').length,nw=v.filter(x=>x.n===1).length;\n"
    "  return `${TOPK==='v'?'💰':'📊'} 前${v.length}・<b>${RMN[RKM]}</b>（市${v.length-o}・櫃${o}）<button id=\"rkE\" title=\"排行要不要含 ETF（點一下切換）\">ETF <i class=\"${RKE?'on':''}\">含</i>·<i class=\"${RKE?'':'on'}\">不含</i></button>${RKE?`<b>${e}</b> 檔・`:''}<span title=\"前一個交易日不在榜上\">🆕 新上榜 <b>${nw}</b></span><br>`}\n"
    "function valCnt(){")
rep("  $('cnt').innerHTML=all?`<b>${rows().length}</b>／${all} 檔${wait?", "  $('cnt').innerHTML=all?rkZ()+`<b>${rows().length}</b>／${all} 檔${wait?")

rep(".sb button#rkM.sm i{padding:0 3px}",
    ".sb button#rkM.sm i{padding:0 3px}\n"
    ".cnt button#rkE{display:inline-block;height:22px;line-height:20px;padding:0 8px;margin:0 4px 0 2px;border:1px solid var(--line);border-radius:11px;background:var(--card);color:var(--fg);font-weight:400;font-size:11.5px;vertical-align:middle;white-space:nowrap}\n"
    ".cnt button#rkE i{font-style:normal;opacity:.45}.cnt button#rkE i.on{font-weight:800;opacity:1;text-decoration:underline;text-underline-offset:2px}")
rep("第 3 行可切 <b>合併·上市·上櫃</b>；", "第 3 行可切 <b>合併·上市·上櫃</b>，統計列的 <b>ETF 含·不含</b> 可把 ETF 拿掉重排（不含時是純股票的前 50）；")
rep("v1115o", "v1115p")

if dst.startswith('beta') and s.count('<title>') == 1 and '[beta]' not in s:
    s = s.replace('<title>', '<title>[beta] ')
open(dst, 'w', encoding='utf-8').write(s)
print('ok')
