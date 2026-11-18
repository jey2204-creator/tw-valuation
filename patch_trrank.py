#!/usr/bin/env python3
"""掃描頁加「🔄 週轉率前50」名單（2026-11-19）
需先套過 patch_fit.py（v1118g）。用法：python3 patch_trrank.py scan.html beta_scan_tr.html
資料：rank.json 的 hist[日期][L|O].t（fetch_rank.py turnover()；成交值 ≥ 1 億、不含 ETF、單日週轉率%）。
沿用成交值／成交量排行那一套（日期選單、合併 上市 上櫃、🆕 新上榜、連 N 天、K 棒標上榜日）；
多的：小卡標籤前面帶 🔥（當天有主力訊號）／注・快・處（注意／處置）、>100% 標「?」、統計列列出這幾種各幾檔。
"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()


def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:90])
    s = s.replace(old, new)


PURPLE = '#8a63d2'
rep("const RKEY={vtop:'v',qtop:'q'},", "const RKEY={vtop:'v',qtop:'q',ttop:'t'},")
# 名單鈕：rank.json 有 t 才加
rep("stocks:rkList('q',RDAYS[0]).map(x=>[x[0],''])})}}",
    "stocks:rkList('q',RDAYS[0]).map(x=>[x[0],''])});\n"
    "    if(rkList('t',RDAYS[0]).length)THEMES.splice(at+2,0,{id:'ttop',name:`🔄 週轉率前50 (${md(RDAYS[0])})`,stocks:rkList('t',RDAYS[0]).map(x=>[x[0],''])})}}")
rep("v:'💰 成交值前50',q:'📊 成交量前50'}", "v:'💰 成交值前50',q:'📊 成交量前50',t:'🔄 週轉率前50'}")
rep("v:'var(--warm)',q:'var(--accent)'}", f"v:'var(--warm)',q:'var(--accent)',t:'{PURPLE}'}}")
# 週轉率榜本來就不含 ETF → 不看 ETF 開關
rep("return RKE?(o[k]||[]):(o[k+'s']", "return RKE||k==='t'?(o[k]||[]):(o[k+'s']")
rep("const rkFmt=(k,x)=>k==='v'?", "const rkFmt=(k,x)=>k==='t'?(x>=10?Math.round(x):x.toFixed(1))+'%'+(x>100?'?':''):k==='v'?")
# 名單每一列：週轉率榜多帶 fi（當天有 🔥）、nt（注意 y／快達 o／處置 r／剛結束 g）
rep("  return rkList(k,D).map(([c,x],i)=>{const n=stk(c);return {c,k,n,rank:i+1,val:rkFmt(k,x),r:`${md(D)} ${RMN[RKM]}${k==='v'?'成交值':'成交量'}第 ${i+1} 名・${k==='v'?fmt(x,x>=100?0:1)+' 億元':fmt(x)+' 張'}・連續 ${n} 天上榜",
    "  if(k==='t'){const fd=(FH&&FH.d[D])||{},att=D===RDAYS[0]?null:new Set((HIST&&HIST[D]&&HIST[D].att)||[]),NTL={y:'注意股',o:'快達處置',r:'處置中',g:'處置剛結束'};\n"
    "    return rkList(k,D).map(([c,x],i)=>{const n=stk(c),fi=fd[c]?1:0,nt=att?(att.has(c)?'y':''):((NMAP[c]||{}).k||'');\n"
    "      return {c,k,n,rank:i+1,x,fi,nt,val:rkFmt(k,x),r:`${md(D)} ${RMN[RKM]}週轉率第 ${i+1} 名・${x.toFixed(1)}% (成交股數÷已發行股數)・連續 ${n} 天上榜${fi?'・當天有 🔥 主力訊號':''}${nt?'・'+NTL[nt]:''}${x>100?'・超過 100%：極端當沖或股數資料有誤':''}`}})}\n"
    "  return rkList(k,D).map(([c,x],i)=>{const n=stk(c);return {c,k,n,rank:i+1,val:rkFmt(k,x),r:`${md(D)} ${RMN[RKM]}${k==='v'?'成交值':'成交量'}第 ${i+1} 名・${k==='v'?fmt(x,x>=100?0:1)+' 億元':fmt(x)+' 張'}・連續 ${n} 天上榜")
rep("if(RK&&(TOPK==='v'||TOPK==='q'))RDAYS.forEach", "if(RK&&(TOPK==='v'||TOPK==='q'||TOPK==='t'))RDAYS.forEach")
rep("css(k==='it'?'--ma20':k==='fi'||k==='q'?'--accent':'--warm')", f"(k==='t'?'{PURPLE}':css(k==='it'?'--ma20':k==='fi'||k==='q'?'--accent':'--warm'))")
# 小卡標籤、放大卡標籤
NTC = "({y:'注',o:'快',r:'處',g:'畢'}[m.nt]||'')"
rep("title=\"${esc(m.r)}\">${m.val||'榜'+m.n}</span>", "title=\"${esc(m.r)}\">${m.k==='t'?(m.fi?'🔥':'')+" + NTC + ":''}${m.val||'榜'+m.n}</span>")
rep("'第 '+nm.rank+' 名'+(nm.val?'・'+nm.val:'')+'・連 '+nm.n+' 天上榜'",
    "'第 '+nm.rank+' 名'+(nm.val?'・'+nm.val:'')+'・連 '+nm.n+' 天上榜'+(nm.fi?'・🔥':'')+(nm.nt?'・'+({y:'注意',o:'快達',r:'處置',g:'剛結束'}[nm.nt]||''):'')")
# 統計列
rep("function rkZ(){if(!(PMAP&&(TOPK==='v'||TOPK==='q')))return '';",
    "function rkZ(){if(PMAP&&TOPK==='t'){const v=Object.values(PMAP),o=v.filter(x=>MKT[x.c]==='上櫃').length,big=v.filter(x=>x.x>100);\n"
    "    return `🔄 前${v.length}・<b>${RMN[RKM]}</b> (市${v.length-o}・櫃${o})・🆕 新上榜 <b>${v.filter(x=>x.n===1).length}</b>・🔥 <b>${v.filter(x=>x.fi).length}</b>・注意/處置 <b>${v.filter(x=>x.nt).length}</b>${big.length?`・<span class=\"miss\">&gt;100%：${big.map(x=>esc(NAME[x.c]||x.c)).join('、')}</span>`:''}<br>`}\n"
    "  if(!(PMAP&&(TOPK==='v'||TOPK==='q')))return '';")
rep("<b>💰 成交值前50/📊 成交量前50</b>＝",
    "<b>🔄 週轉率前50</b>＝當天成交股數÷已發行普通股數最高的 50 檔 (成交值 ≥ 1 億才入榜、不含 ETF；股數用目前的值，>100% 標「?」＝極端當沖或股數資料有誤)，小卡標籤是週轉率，前面的 🔥＝當天有主力訊號、注/快/處＝注意/快達處置/處置中；高週轉是熱度不是買進訊號，低檔換手和高檔出貨數字長得一樣。<b>💰 成交值前50/📊 成交量前50</b>＝")
rep("v1118g", "v1119a")

if dst.startswith('beta') and s.count('<title>') == 1 and '[beta]' not in s:
    s = s.replace('<title>', '<title>[beta] ')
open(dst, 'w', encoding='utf-8').write(s)
print('ok')
