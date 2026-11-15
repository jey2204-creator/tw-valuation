#!/usr/bin/env python3
"""掃描頁「量比」排序鈕改成連點循環「量比·值·量」（任何名單都能照成交值／成交量排）（2026-11-15）
需先套過 patch_rketf.py（v1115p）。用法：python3 patch_volcyc.py scan.html beta_scan_vq.html
成交值＝最新那根的 收盤 × 成交張數（估算；官方成交金額是逐筆加總，會差幾個 %）。
"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()


def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:90])
    s = s.replace(old, new)


# 狀態：VQP＝r 量比／a 成交值／q 成交量
rep("let MISS=[],RANKED=false,CHGP='d',", "let VQP='r';const amtFmt=x=>x==null?'—':x>=10?Math.round(x)+'億':x>=1?x.toFixed(1)+'億':Math.round(x*1e4)+'萬',volFmt=x=>x==null?'—':x>=1e5?Math.round(x/1e4)+'萬':x>=1e4?(x/1e4).toFixed(1)+'萬':fmt(x);\nlet MISS=[],RANKED=false,CHGP='d',")
rep("try{const p=localStorage.getItem('scanChgP');if(['d','w','m'].includes(p))CHGP=p;",
    "try{const p=localStorage.getItem('scanChgP');if(['d','w','m'].includes(p))CHGP=p;const vq=localStorage.getItem('scanVqP');if(['r','a','q'].includes(vq))VQP=vq;")

# 按鈕：同「日·週·月」樣式
rep(".sb button[data-k=chg]{flex:1.7 1 0}",
    ".sb button[data-k=chg]{flex:1.7 1 0}\n.sb button[data-k=vr]{flex:2.2 1 0}\n"
    ".sb button[data-k=vr] i{font-style:normal;font-weight:400;opacity:.45;padding:0 2px}.sb button[data-k=chg] i{padding:0 2px}\n"
    ".sb button[data-k=chg],.sb button[data-k=vr]{display:flex;padding:0}.sb button[data-k=chg] i,.sb button[data-k=vr] i{flex:1 1 0;min-width:0;padding:0;text-align:center;height:100%}.sb button[data-k=vr] i:first-child{flex:1.35 1 0}\n"
    ".sb button[data-k=vr] i.on{font-weight:800;opacity:1;text-decoration:underline;text-underline-offset:2px}")
rep("  const cb=document.querySelector('#sortBar button[data-k=chg]');",
    "  {const vb=document.querySelector('#sortBar button[data-k=vr]');vb.innerHTML=[['r','量比'],['a','值'],['q','量']].map(([k,n])=>`<i data-p=\"${k}\" class=\"${k===VQP?'on':''}\">${n}</i>`).join('');vb.title='點字切換 量比／成交值／成交量 排序（成交值＝收盤×成交張數，估算）'}\n"
    "  const cb=document.querySelector('#sortBar button[data-k=chg]');")
rep("if(b.dataset.k==='chg'&&sortK==='chg')CHGP=CHGP==='d'?'w':CHGP==='w'?'m':'d';",
    "{const t=e.target.closest('i[data-p]');if(b.dataset.k==='chg'){if(t)CHGP=t.dataset.p;else if(sortK==='chg')CHGP=CHGP==='d'?'w':CHGP==='w'?'m':'d'}if(b.dataset.k==='vr'){if(t)VQP=t.dataset.p;else if(sortK==='vr')VQP=VQP==='r'?'a':VQP==='a'?'q':'r';try{localStorage.setItem('scanVqP',VQP)}catch(e){}}}")

# 指標：最新那根的成交張數與估算成交值（億）
rep("vr:v5?last.v/v5:null,", "vr:v5?last.v/v5:null,vol:last.v||null,amt:last.v&&last.c?last.c*last.v/1e5:null,")
rep("vr:r=>r.stale?-99:(r.vr??-9),", "vr:r=>r.stale?-99:((VQP==='a'?r.amt:VQP==='q'?r.vol:r.vr)??-9),")

# 小卡第二行：量比的位置跟著換
rep("<span class=\"vr${r.vr>=1.5?' hi':''}\">量${r.vr==null?'—':r.vr.toFixed(1)+'×'}</span>",
    "<span class=\"vr${r.vr>=1.5?' hi':''}\" title=\"量比 ${r.vr==null?'—':r.vr.toFixed(1)+'×'}（橘色＝量比 ≥1.5）\">${VQP==='a'?'值'+amtFmt(r.amt):VQP==='q'?'量'+volFmt(r.vol):'量'+(r.vr==null?'—':r.vr.toFixed(1)+'×')}</span>")

rep("量比＝今日量 ÷ 前 5 日均量；",
    "量比＝今日量 ÷ 前 5 日均量；「量比 值 量」「日 週 月」兩顆鈕點哪個字就選哪個；<b>量比 值 量</b>＝照量比／成交值／成交量排，小卡第二行同步顯示（值＝收盤×成交張數的估算，跟交易所成交金額差幾個 %；橘色仍代表量比 ≥1.5）；")
# 2026-11-15：iPhone 的「·」很寬，兩顆循環鈕會被切 → 拿掉分隔點改用小間距（日 週 月／量比 值 量）
rep("[['d','日'],['w','週'],['m','月']].map(([k,n])=>`<i class=\"${k===CHGP?'on':''}\">${n}</i>`).join('·')",
    "[['d','日'],['w','週'],['m','月']].map(([k,n])=>`<i data-p=\"${k}\" class=\"${k===CHGP?'on':''}\">${n}</i>`).join('')")
# 2026-11-15：兩顆都改成「點哪個字就選哪個」（整顆鈕切成三個觸控區）
rep("cb.title='連點切換 日→週→月漲幅", "cb.title='點字切換 日／週／月漲幅")
rep("v1115p", "v1115s")

if dst.startswith('beta') and s.count('<title>') == 1 and '[beta]' not in s:
    s = s.replace('<title>', '<title>[beta] ')
open(dst, 'w', encoding='utf-8').write(s)
print('ok')
