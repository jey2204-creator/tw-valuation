#!/usr/bin/env python3
"""2026-11-24 12:17 熱力圖加「固定 / 相對」色階切換（世杰：「加依當天強弱自動分色的切換，做給我看」）。
相對＝跟同畫面其他格比排名（百分位）：前10% 最深紅、10～25% 中紅、25～40% 淺紅、中間 40～60% 灰、
後 40～25% 淺綠、25～10% 中綠、後 10% 最深綠。數字不變，只換顏色；展開的成份股也在該主題內比排名。
切換鈕放在控制列最右（固定 相對），記在手機 localStorage hmC。
用法：python3 patch_hmrel.py → beta.html；python3 patch_hmrel.py prod → index.html（只能對沒有 HMLV 的 index 跑一次）。
"""
import sys, re
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
s = open('index.html', encoding='utf-8').read()
assert 'HMLV' not in s
E = [
 ('.hmseg button{border:0;background:none;color:var(--muted);font:500 13px/28px var(--f-body);padding:0 11px;',
  '.hmseg button{border:0;background:none;color:var(--muted);font:500 13px/28px var(--f-body);padding:0 9px;'),
 ('<button data-s="o">順序</button><button data-s="v">漲幅</button></div>',
  '<button data-s="o">順序</button><button data-s="v">漲幅</button></div><div class="hmseg" id="hmC" title="顏色：固定幅度／跟其他格比排名"><button data-c="f">固定</button><button data-c="r">相對</button></div>'),
 ("function hmTile(lab,v,sub,attrs,sz){const l=hmLv(v,HMP);",
  "let HMC=store.get('hmC')==='r'?'r':'f',HMLV=null;\n"
  "// 相對色階：跟同一批值比百分位（同值取平均名次）\n"
  "function hmRel(vals){const k=HMP==='d'?100:10,rd=v=>Math.round(v*k)/k;   // 用畫面上顯示的位數比，同樣數字＝同色\n"
  "const a=vals.filter(v=>v!=null).map(rd).sort((x,y)=>x-y),n=a.length;if(n<3)return null;"
  "return v=>{if(v==null)return null;v=rd(v);let lo=0,eq=0;for(const x of a){if(x<v)lo++;else if(x===v)eq++}const p=(lo+eq/2)/n;"
  "return p<.1?-3:p<.25?-2:p<.4?-1:p<=.6?0:p<=.75?1:p<=.9?2:3}}\n"
  "function hmTile(lab,v,sub,attrs,sz){const l=HMLV?HMLV(v):hmLv(v,HMP);"),
 ("  $('hmS').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.s===HMS));",
  "  $('hmS').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.s===HMS));\n"
  "  $('hmC').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.c===HMC));"),
 ("  $('hmG').innerHTML=R.map(",
  "  HMLV=HMC==='r'?hmRel(R.map(r=>r.m)):null;\n  $('hmG').innerHTML=R.map("),
 ("const T=HMTH[HMP];$('hmLg').innerHTML=`<span style=\"margin-right:3px\">跌</span>`+[-3,-2,-1,0,1,2,3].map(l=>`<i class=\"hmt l${l}\" style=\"padding:0\">${l===0?'0':(l<0?'−':'+')+T[Math.abs(l)-1]}</i>`).join('')+`<span style=\"margin-left:3px\">漲</span>`;",
  "const T=HMTH[HMP];$('hmLg').innerHTML=HMLV?`<span style=\"margin-right:3px\">弱</span>`+[['-3','後10%'],['-2','後25%'],['-1','後40%'],['0','中間'],['1','前40%'],['2','前25%'],['3','前10%']].map(([l,t])=>`<i class=\"hmt l${l}\" style=\"padding:0\">${t}</i>`).join('')+`<span style=\"margin-left:3px\">強</span>`:`<span style=\"margin-right:3px\">跌</span>`+[-3,-2,-1,0,1,2,3].map(l=>`<i class=\"hmt l${l}\" style=\"padding:0\">${l===0?'0':(l<0?'−':'+')+T[Math.abs(l)-1]}</i>`).join('')+`<span style=\"margin-left:3px\">漲</span>`;"),
 ("  const r=hmStat(t),ids=[...r.ids].sort((a,b)=>hmCap(b)-hmCap(a));",
  "  const r=hmStat(t),ids=[...r.ids].sort((a,b)=>hmCap(b)-hmCap(a));HMLV=HMC==='r'?hmRel(ids.map(i=>hmV(i,HMP))):null;"),
 ("  const p=e.target.closest('#hmP button'),s=e.target.closest('#hmS button'),",
  "  {const c=e.target.closest('#hmC button');if(c){HMC=c.dataset.c;store.set('hmC',HMC);renderHmap();return}}\n  const p=e.target.closest('#hmP button'),s=e.target.closest('#hmS button'),"),
 ("$('hmFoot').innerHTML=`<b>盤中即時</b>",
  "$('hmFoot').innerHTML=`<b>顏色「固定 / 相對」</b>：固定＝照漲跌幅度上色 (下面說明的七階)；相對＝跟同畫面其他格比名次，前 10% 最深紅、後 10% 最深綠、中間 40～60% 灰色，數字不變，適合全市場一起大漲或大跌、顏色全部一樣深的日子找出相對強弱；展開的成份股則是在該主題內比。<br><b>盤中即時</b>"),
]
for a, b in E:
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)
# 相對模式時摘要列加一句
a = "+(ok.length?`<b>${HML[HMP]}</b>漲跌"
assert s.count(a) == 1
s = s.replace(a, "+(HMC==='r'&&ok.length?`<span style=\"color:var(--accent)\">🎨 相對色：跟 ${ok.length} 個主題比名次 (中位 ${pct(median(ok.map(r=>r.m)),HMP==='d'?2:1)})</span><br>`:'')+(ok.length?`<b>${HML[HMP]}</b>漲跌")
assert len(re.findall(r'opacity:\.5">v11\d\d[a-z]+</span>', s)) == 1
s = re.sub(r'opacity:\.5">v11\d\d[a-z]+</span>', 'opacity:.5">v1124e</span>', s)
if not prod: s = s.replace('<title>', '<title>[beta] ', 1)
dst = 'index.html' if prod else 'beta.html'
open(dst, 'w', encoding='utf-8').write(s); print('ok', dst)
