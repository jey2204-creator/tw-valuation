#!/usr/bin/env python3
"""2026-11-17 掃描頁：主題最前面加「🌏 海外龍頭」小卡（對應日股／韓股的日 K）

用法：python3 patch_ovs.py            → 讀 scan.html，輸出 beta_scan_ovs.html
      python3 patch_ovs.py prod       → 直接改 scan.html（已套用過會因 assert 中止）

起因：世杰看被動元件時想同時看龍頭村田（6981）的 K 線。選方案①。
做法：
  1. 名單＝themes.json 該主題的 jp／kr 欄位（手機改過的主題沒有這兩欄就沿用內建主題的）。
  2. 日 K 來自 data/ovs.json（fetch_ovs.py，Yahoo，平日台北 14:50／17:40 更新；非即時）。只有主題有對應股時才載入。
  3. 小卡跟台股同款（K 棒＋20／60 日線＋前 20 日高），右上標「日／韓」，第二行＝日漲、量比、資料日；
     沒有投信／外資，底下改畫成交量。點小卡放大（週月漲幅、均線位置、連到日股／韓股站）。
  4. 標題列可點收合（記在手機）；估值模式、非主題名單不顯示。
"""
import sys

PROD = len(sys.argv) > 1 and sys.argv[1] == 'prod'
SRC = 'scan.html'
OUT = 'scan.html' if PROD else 'beta_scan_ovs.html'
VER = 'v1117f'

s = open(SRC, encoding='utf-8').read()
assert 'ovPaint' not in s, '已套用過'


def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (s.count(old), old[:80])
    s = s.replace(old, new)


# ---- CSS ----
rep('.km-cv{display:block;width:100%;height:92px;margin-top:1px}',
    '/* 2026-11-17 海外龍頭小卡 */\n'
    '.ovs[hidden]{display:none}\n'
    '.ovs-t{display:flex;align-items:center;gap:5px;width:100%;margin:0;padding:3px 9px 0;border:0;background:none;color:var(--fg);font:700 12px/20px var(--f-body);text-align:left;white-space:nowrap;overflow:hidden;-webkit-tap-highlight-color:transparent}\n'
    '.ovs-t small{font-weight:400;font-size:10.5px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;min-width:0}\n'
    '.ovs-t i{margin-left:auto;font-style:normal;color:var(--muted);flex:none}\n'
    '.ovs .grid{padding:3px 5px 2px}\n'
    '.ovs .km{background:color-mix(in srgb,var(--accent) 6%,var(--card))}\n'
    '.tg.fx{background:var(--accent)}\n'
    '.km-s .od{color:var(--muted);font-weight:400;margin-left:auto}\n'
    '.km-cv{display:block;width:100%;height:92px;margin-top:1px}')

# ---- HTML ----
rep('<div class="grid" id="grid">', '<div class="ovs" id="ovs" hidden></div>\n<div class="grid" id="grid">')

# ---- render()：每次重畫時順便檢查海外小卡（鍵值沒變就不重畫）----
rep('function render(){', 'function render(){ovPaint();')

# ---- drawK：海外股沒有投信／外資 → 小卡底下改畫成交量 ----
rep("const volH=mini?0:Math.round(Hh*0.14),instH=mini?8:Math.round(Hh*0.12),gap=mini?2:5;",
    "const ov=!!r.ov,volH=mini?(ov?16:0):Math.round(Hh*0.14),instH=ov?0:mini?8:Math.round(Hh*0.12),gap=mini?2:5;")
rep("const priceH=Hh-top-volH-(volH?gap:0)-(instH+gap)*2-axisH;",
    "const priceH=Hh-top-volH-(volH?gap:0)-(ov?(mini?2:0):(instH+gap)*2)-axisH;")
rep("g.fillStyle=mu;g.font='9px '+css('--f-body');g.textAlign='left';g.textBaseline='top';g.fillText('量(張)',padL+2,yCur+gap);g.font='10px '+css('--f-num');g.textBaseline='middle';g.fillText(fmt(vmax),W-padR+4,yCur+gap+6);yCur=vY0}",
    "if(!mini){g.fillStyle=mu;g.font='9px '+css('--f-body');g.textAlign='left';g.textBaseline='top';g.fillText(ov?'量(股)':'量(張)',padL+2,yCur+gap);g.font='10px '+css('--f-num');g.textBaseline='middle';g.fillText(ov?ovVol(vmax):fmt(vmax),W-padR+4,yCur+gap+6)}yCur=vY0}")
rep("[['t','投'],['f','外']].forEach(([k,lab],i)=>{", "(ov?[]:[['t','投'],['f','外']]).forEach(([k,lab],i)=>{")

# ---- 放大卡：海外股不顯示投信／外資，量用「股」，連結改到日股／韓股站 ----
rep('<span class="mid"><b>${esc(r.n)}</b><span class="cd">${esc(r.c)}</span></span>${ntag}${lvh}',
    '<span class="mid"><b>${esc(r.n)}</b><span class="cd">${esc(r.cd||r.c)}</span></span>${r.ov?`<span class="ntag" style="background:var(--accent)">${r.mk}股・收盤</span>`:\'\'}${ntag}${lvh}')
rep('<span>量 <b>${fmt(last.v)}</b>張（', '<span>量 <b>${r.ov?ovVol(last.v):fmt(last.v)}</b>${r.ov?\'股\':\'張\'}（')
a = s.index('<span>投信 5日<b class="${cls(r.t5)}">')
b = s.index('\n', a)
line = s[a:b]
assert line.count('<span>') == 2 and line.endswith('</span>'), line[:200]
s = s[:a] + '${r.ov?\'\':`' + line + '`}' + s[b:]
rep('${shCnt(false)}${askA(r)}<a href="index.html#${esc(r.c)}">財報・估值 →</a></div>`;',
    '${shCnt(false)}${askA(r)}${r.ov?`<a href="${r.m}/#${esc(r.cd)}">${r.mk}股站 →</a>`:`<a href="index.html#${esc(r.c)}">財報・估值 →</a>`}</div>`;')
rep("function askA(r){return `", "function askA(r){if(r.ov)return ovAsk(r);return `")
# 即時重畫時，海外股的放大卡不要被換成台股名單
rep("if(openI>=0){SHR=rows();fillSheet()}}", "if(openI>=0){if(!SHR.ov)SHR=rows();fillSheet()}}")

# ---- JS：載入、算指標、畫小卡 ----
rep("// ---- 畫 K：mini（小卡）與 full（放大卡） ----", r'''// ---- 2026-11-17：🌏 海外龍頭小卡（themes.json 的 jp／kr 對應股；日 K 來自 data/ovs.json，Yahoo 收盤價、非即時） ----
let OVS,OVR=[],OVK='',OVC=!!store.get('scanOvC'),OVB=null;
const ovVol=v=>v==null?'—':v>=1e8?(v/1e8).toFixed(1)+'億':v>=1e4?Math.round(v/1e4)+'萬':fmt(v);
function ovLoad(){if(OVS!==undefined)return;OVS=null;fetch('data/ovs.json?t='+Math.floor(Date.now()/6e5)).then(r=>r.ok?r.json():null).catch(()=>null).then(j=>{OVS=j&&j.s?j:null;if(OVS)ovPaint()})}
function ovIds(sel){if(!sel||sel.kind!=='t'||MODE==='v')return [];const t=THEMES.find(x=>x.id===sel.id)||{},b=(OVB||{})[sel.id]||{};
  return [...(t.jp||b.jp||[]).map(x=>['jp'+x[0],x[1]]),...(t.kr||b.kr||[]).map(x=>['kr'+x[0],x[1]])]}
function ovBuild(k,nm){const o=OVS&&OVS.s[k];if(!o||!o.b||o.b.length<6)return null;
  const bars=o.b.map(x=>({d:x[0],o:x[1],h:x[2],l:x[3],c:x[4],v:x[5]||0,f:null,t:null,m240:x[6]??null}));
  const n=bars.length,last=bars[n-1],prev=bars[n-2],ma=w=>n<w?null:bars.slice(n-w).reduce((a,x)=>a+x.c,0)/w;
  const ma5=ma(5),ma20=ma(20),ma60=ma(60),v5=bars.slice(-6,-1).reduce((a,x)=>a+x.v,0)/5,hi20=Math.max(...bars.slice(-21,-1).map(x=>x.h));
  const w60=bars.slice(-60),lo60=Math.min(...w60.map(x=>x.l)),hi60=Math.max(...w60.map(x=>x.h)),b5=bars[n-6];
  return {ov:1,m:o.m,mk:o.m==='jp'?'日':'韓',c:k,cd:o.c,n:nm||o.n,bars,nd:{},fd:{},dp:[],fsince:null,d:last.d,live:false,px:last.c,
    chg:prev.c?last.c/prev.c-1:null,chg5:b5&&b5.c?last.c/b5.c-1:null,chg20:calM(bars),vr:v5?last.v/v5:null,vol:last.v||null,amt:null,ts:0,fs:0,t5:null,f5:null,t20:null,f20:null,
    split:false,ma5,ma20,ma60,m240:last.m240,d20:ma20?last.c/ma20-1:null,d60:ma60?last.c/ma60-1:null,d240:last.m240?last.c/last.m240-1:null,hi20,brk:last.h>=hi20,pos60:hi60>lo60?(last.c-lo60)/(hi60-lo60):null,
    arr:ma5!=null&&ma20!=null&&ma60!=null?(ma5>ma20&&ma20>ma60?'多頭排列':ma5<ma20&&ma20<ma60?'空頭排列':'糾結'):'—'}}
function ovAsk(r){const a=r.chg==null?0:Math.abs(r.chg*100),w=a<0.5?'近期股價漲跌的原因？':`${md(r.d)} ${a>=5?'大':r.chg>0?'上':'下'}${r.chg>0?'漲':'跌'} ${a.toFixed(2)}% 的原因？`;
  return `<a class="askai" target="_blank" rel="noopener" aria-label="問 Google AI 漲跌原因" href="${esc('https://www.google.com/search?udm=50&hl=zh-TW&q='+encodeURIComponent(`${r.mk}股 ${r.n} ${r.cd} ${w}請列出新聞來源，以及對台股同業的影響`))}">🔍AI</a>`}
function ovPaint(){const el=$('ovs');if(!el)return;const ids=ovIds(cur);if(!ids.length){el.hidden=true;OVK='';return}
  if(OVS===undefined)ovLoad();if(!OVS){el.hidden=true;OVK='';return}
  const key=[cur.id,N,CHGP,OVC,OVS.updated,innerWidth].join('|');if(key===OVK&&!el.hidden)return;OVK=key;
  const R=ids.map(([k,n])=>ovBuild(k,n)).filter(Boolean);R.ov=true;OVR=R;if(!R.length){el.hidden=true;return}
  const dd=m=>{const v=R.filter(r=>r.m===m).map(r=>r.d).sort().pop();return v?(m==='jp'?'日 ':'韓 ')+md(v):''};
  el.hidden=false;
  el.innerHTML=`<button class="ovs-t" aria-expanded="${!OVC}">🌏 海外龍頭 ${R.length}<small>${[dd('jp'),dd('kr')].filter(Boolean).join('・')} 收盤・非即時</small><i>${OVC?'展開 ▸':'收合 ▾'}</i></button>`+(OVC?'':`<div class="grid">${R.map((r,i)=>`<article class="km${r.brk&&r.chg>0?' hot':''}" data-i="${i}" role="button" tabindex="0">
    <div class="km-h">${nmB(r.n)}<span class="cd">${esc(r.cd)}</span><span class="tg fx" title="${r.mk}股">${r.mk}</span></div>
    <div class="km-s"><span class="${cls(r.chg)}">${pct(r.chg)}</span>${CHGP!=='d'?`<span class="${cls(r[CHGK()])}">${CHGP==='w'?'週':'月'}${pct(r[CHGK()])}</span>`:''}<span class="vr${r.vr>=1.5?' hi':''}">量${r.vr==null?'—':r.vr.toFixed(1)+'×'}</span><span class="od">${md(r.d)}</span></div>
    <canvas class="km-cv"></canvas></article>`).join('')}</div>`);
  el.querySelector('.ovs-t').onclick=()=>{OVC=!OVC;store.set('scanOvC',OVC);ovPaint()};
  el.querySelectorAll('.km').forEach(k=>{const i=+k.dataset.i;drawK(k.querySelector('canvas'),R[i],N,{mini:true});k.onclick=()=>openSheet(R,i);k.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();openSheet(R,i)}}})}
// ---- 畫 K：mini（小卡）與 full（放大卡） ----''')

# 內建主題的 jp／kr（手機改過成份股的主題沿用）
rep("  THEMES=themesAll(T.themes||[]);", "  OVB=Object.fromEntries((T.themes||[]).map(t=>[t.id,t]));THEMES=themesAll(T.themes||[]);")

# ---- 版本、頁尾說明 ----
rep('<span style="opacity:.5">v1117e</span>',
    '<b>🌏 海外龍頭</b>＝這個主題對應的日股／韓股（跟首頁主題頁的「對應日股／韓股」同一份名單），Yahoo 收盤價、平日約 15:00 與 17:40 更新、<b>非即時</b>；價位為當地貨幣、已還原分割；沒有投信／外資，底下灰紅綠柱＝成交量；休市日不同，最右邊那根不一定跟台股同一天（小卡第二行最右＝資料日）。 <span style="opacity:.5">' + VER + '</span>')

if not PROD:
    s = s.replace('<title>', '<title>β ', 1)
open(OUT, 'w', encoding='utf-8').write(s)
print('wrote', OUT, len(s))
