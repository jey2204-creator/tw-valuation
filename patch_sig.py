#!/usr/bin/env python3
"""2026-11-22 batch19 台股站主題表的 🇺🇸 改成「美股財報動能燈號」（方案 B）
資料：us/data/sig.json（us/build_sig.py，每檔 [營收加速, EPS 驚喜, 首日反應, 近一月, 財報日]）
台股首頁主題表第二行：美🟢／美🟡／美🔴／美⚪（點了開美股同主題；title 有三項明細＋美股近一月）；資料還沒讀到時先顯示 🇺🇸
卡片模式主題名後同樣顯示；台股主題頁「對應美股」下面多一行：美股財報動能＋美股近一月 vs 台股本主題近一月（美−台）
燈號算法跟美股站 sigOf() 一樣，用台股主題（含手機上改過的）自己的 us 清單算
用法：python3 patch_sig.py → beta_sig.html；python3 patch_sig.py prod → index.html
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
s=open('index.html',encoding='utf-8').read()
def rep(a,b):
    global s
    assert s.count(a)==1,(s.count(a),a[:70]);s=s.replace(a,b)
rep("const median=a=>{a=a.filter(x=>x!=null).sort((x,y)=>x-y);if(!a.length)return null;const m=a.length>>1;return a.length%2?a[m]:(a[m-1]+a[m])/2};",
"""const median=a=>{a=a.filter(x=>x!=null).sort((x,y)=>x-y);if(!a.length)return null;const m=a.length>>1;return a.length%2?a[m]:(a[m-1]+a[m])/2};
// ---- 美股財報動能燈號（batch19）：us/data/sig.json 每檔 [營收加速(點), EPS 驚喜%, 首日反應%, 近一月%, 財報日]；跟美股站 sigOf() 同算法 ----
// 三項各取主題中位數（不到一半檔數有值不算）：可算的全正 🟢、全負 🔴、其他 🟡、可算不到 2 項 ⚪。只描述美股這季財報動能，不是買賣訊號
let USIG=null,USIG_P=null;
function loadUsig(){return USIG_P||(USIG_P=fetch('us/data/sig.json?d='+new Date().toISOString().slice(0,10)).then(r=>r.ok?r.json():null).then(j=>{if(j&&j.d){USIG=j;
  try{if(!$('home').hidden)renderHome()}catch(e){}try{const el=$('tUSsig');if(el&&el.dataset.t){const t=THEMES.find(x=>x.id===el.dataset.t);if(t)el.innerHTML=usSigLine(t)}}catch(e){}}}).catch(()=>null))}
function usSig(us){if(!USIG||!us||!us.length)return null;const N=us.length,D=USIG.d;
  const mk=(lb,i,f)=>{const v=us.map(u=>(D[u]||[])[i]).filter(x=>x!=null&&isFinite(x));return{lb,v:v.length&&v.length*2>=N?median(v):null,f}};
  const c=[mk('營收加速',0,v=>(v>0?'+':'')+fmt(v,0)+' 點'),mk('EPS 驚喜',1,v=>pct(v,1)),mk('首日反應',2,v=>pct(v,1))];
  const av=c.filter(x=>x.v!=null),pos=av.filter(x=>x.v>0).length,m=us.map(u=>(D[u]||[])[3]).filter(x=>x!=null);
  return{lt:av.length<2?'⚪':pos===av.length?'🟢':pos===0?'🔴':'🟡',c,tip:c.map(x=>`${x.lb} ${x.v==null?'—':(x.v>0?'✓ ':'✗ ')+x.f(x.v)}`).join('・'),m1:m.length*2>=N?median(m):null}}
function usBadge(t,link){const us=t.us||[];if(!us.length)return '';const g=usSig(us);
  const tip=g?`美股財報動能 ${g.lt}：${g.tip}${g.m1!=null?'・美股近一月 '+pct(g.m1,0):''}`:'美股站也有這個主題';
  return link?`<a class="usf" href="us/index.html#t/${t.id}" title="${tip}（點了開美股同主題）" aria-label="美股同主題">${g?'美'+g.lt:'🇺🇸'}</a>`:`<span class="usf" title="${tip}">${g?'美'+g.lt:'🇺🇸'}</span>`}
function usSigLine(t){const g=usSig(t.us||[]);if(!g)return '';const tw=median(t.stocks.map(x=>mv(x[0],'m')));
  return `美股財報動能 <b>${g.lt}</b>：${g.c.map(x=>`${x.lb} ${x.v==null?'—':`<span class="${x.v>0?'up':'dn'}">${x.v>0?'✓':'✗'} ${x.f(x.v)}</span>`}`).join('・')}`+
    (g.m1!=null?`<br>近一月：美股 <span class="${sign(g.m1)}">${pct(g.m1,0)}</span>${tw!=null?`・台股 <span class="${sign(tw)}">${pct(tw,0)}</span>・美−台 <b>${(g.m1-tw>0?'+':'')+fmt(g.m1-tw,0)}</b> 點`:''}`:'')+
    `<br><span style="font-size:11px">燈號只描述美股這季財報動能，台股可能落後或不跟，不是買進訊號</span>`}""")
# 首頁主題表、卡片：🇺🇸 → 美燈號
rep("${(t.us||[]).length?`<a class=\"usf\" href=\"us/index.html#t/${t.id}\" title=\"美股站也有這個主題（${t.us.length} 檔對應美股），點了開美股同主題\" aria-label=\"美股同主題\">🇺🇸</a>`:''}`;",
    "${usBadge(t,true)}`;")
rep("${(t.us||[]).length?'<span class=\"usf\" title=\"美股站也有這個主題\">🇺🇸</span>':''}","${usBadge(t,false)}")
rep("function renderHome(){","function renderHome(){loadUsig();")
# 主題頁：對應美股下面一行
rep("   $('tUS').innerHTML=(t.us&&t.us.length?'對應美股 '+t.us.map(u=>`<a href=\"us/#${u}\">${u}</a>`).join(''):'')+",
    "   $('tUS').innerHTML=(t.us&&t.us.length?'對應美股 '+t.us.map(u=>`<a href=\"us/#${u}\">${u}</a>`).join('')+`<span class=\"ussig\" id=\"tUSsig\" data-t=\"${t.id}\">${usSigLine(t)}</span>`:'')+")
rep(".uslink{display:flex;",".ussig{flex-basis:100%;font-size:12px;line-height:1.6;color:var(--muted)}.ussig:empty{display:none}.ussig b{color:var(--fg)}\n.uslink{display:flex;")
# 主題頁直接開（沒經過首頁）也要讀
rep("   $('tUS').innerHTML=","   loadUsig();$('tUS').innerHTML=")
if prod:open('index.html','w',encoding='utf-8').write(s);print('prod ok');sys.exit()
open('beta_sig.html','w',encoding='utf-8').write(s.replace('<title>','<title>[測試] ',1));print('test ok')
