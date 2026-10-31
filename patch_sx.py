#!/usr/bin/env python3
"""獲利驚喜（EPS vs 月營收推估）＋ 本季營收進度／兌現率：套到 index.html 或 beta.html
用法：python3 patch_sx.py index.html beta.html
"""
import sys, re
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()

def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:60])
    s = s.replace(old, new)

# ① CSS
rep('.ichk{margin-top:10px;',
    '.sx{display:flex;gap:5px;margin:6px 0 2px;overflow-x:auto;scrollbar-width:none}.sx::-webkit-scrollbar{display:none}\n'
    '.sx div{flex:1 1 0;min-width:0;border:1px solid var(--line);border-radius:9px;padding:3px 6px 4px;text-align:center}\n'
    '.sx span{display:block;font-size:10px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}\n'
    '.sx b{display:block;font-family:var(--f-num);font-size:14px;font-weight:600;line-height:1.25}\n'
    '.sx i{display:block;font-style:normal;font-family:var(--f-num);font-size:9.5px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}\n'
    '.sx .up b{color:var(--up)}.sx .dn b{color:var(--down)}.sx .fl{border-style:dashed}\n'
    '.ichk{margin-top:10px;')

# ② EPS 卡：take 下方加驚喜列＋腳註
rep('<p class="take" id="tEps"></p>\n  <div class="chart" id="cEps"></div>',
    '<p class="take" id="tEps"></p>\n  <div class="sx" id="epsSx" hidden></div>\n  <div class="chart" id="cEps"></div>\n  <p class="foot" id="fEps" hidden></p>')

# ③ 營收卡 take 後面加本季進度（直接寫進 tRev）
rep("$('tRev').innerHTML=`${mo} 月 <strong>${fmt(lv[1])} 億</strong>，年增 <strong>${lv[2]}%</strong>；1–${mo} 月累計年增 <strong>${ytdP?((ytd/ytdP-1)*100).toFixed(1):'—'}%</strong>`;",
    "$('tRev').innerHTML=`${mo} 月 <strong>${fmt(lv[1])} 億</strong>，年增 <strong>${lv[2]}%</strong>；1–${mo} 月累計年增 <strong>${ytdP?((ytd/ytdP-1)*100).toFixed(1):'—'}%</strong>`+revProg();")

# ④ header 末尾呼叫驚喜列
rep("  renderPeg();\n  {const {b,s,f}=pegViews()",
    "  renderPeg();renderSx();\n  {const {b,s,f}=pegViews()")

# ⑤ 函式
rep('// 三率圖右端數字避讓：', r'''// ---- 本季營收進度：下一季（財報還沒出）已公布幾個月、累計多少、若剩餘月份持平的季增／年增；以及上一季「財報營收 ÷ 月營收合計」兌現率 ----
const qMonths=l=>{const y=2000+ +l.slice(0,2),n=+l[3];return [1,2,3].map(i=>`${y}-${String((n-1)*3+i).padStart(2,'0')}`)};
const qPrevY=l=>String(+l.slice(0,2)-1).padStart(2,'0')+l.slice(2);
function revProg(){
  try{
    if(!Q||!Q.length||!V||!V.length)return '';
    const lq=Q[Q.length-1],nq=qNext(lq[0]),VM={};V.forEach(x=>VM[x[0]]=x[1]);
    const ms=qMonths(nq),known=ms.map(m=>VM[m]).filter(v=>v!=null),k=known.length;
    let out='';
    if(k){const cum=sum(known),proj=k<3?cum+(3-k)*cum/k:cum,ya=Q.find(x=>x[0]===qPrevY(nq)),
        qq=lq[1]>0?(proj/lq[1]-1)*100:null,yy=ya&&ya[1]>0?(proj/ya[1]-1)*100:null,G=v=>v==null?'—':`<strong class="${sign(v)}">${pct(v,1)}</strong>`;
      out+=`<br>${nq} 已公布 <strong>${k}/3</strong> 月，累計 <strong>${fmt(cum)} 億</strong>`+(k<3?`；剩餘月份若持平 → 季營收約 ${fmt(proj)} 億，`:`，3 個月已全公布：`)+`季增 ${G(qq)}・年增 ${G(yy)}${k===3?'，等財報看獲利率':''}`}
    // 兌現率：上一季財報營收 ÷ 該季 3 個月月營收合計（月營收公告時就知道，差 >3% 代表有退貨折讓或口徑不同）
    const pm=qMonths(lq[0]).map(m=>VM[m]);
    if(pm.every(v=>v!=null)&&lq[1]>0){const ms3=sum(pm),r=lq[1]/ms3*100,d=r-100;
      out+=`<br>${lq[0]} 月營收兌現率 <strong class="${Math.abs(d)>3?'dn':''}">${fmt(r,1)}%</strong>（財報 ${fmt(lq[1])} 億 ÷ 月營收合計 ${fmt(ms3)} 億）`+(Math.abs(d)>3?'<span class="pill">留意</span> 差 3% 以上：季報有退貨折讓、合併範圍或月營收口徑不同':'')}
    return out;
  }catch(e){return ''}
}
// ---- 獲利驚喜：財報公布前營收已知（月營收），真正的新資訊是獲利率。推估 EPS＝該季營收 × 前四季平均淨利率 ÷ 股數；驚喜％＝(實際 − 推估) ÷ |推估| ----
function sxCalc(){
  if(!Q||Q.length<5||!D.shares)return [];
  const N=Q.length,out=[];
  for(let i=Math.max(4,N-4);i<N;i++){const q=Q[i];if(q[1]==null||q[5]==null)continue;
    const w=Q.slice(i-4,i).map(x=>x[4]).filter(v=>v!=null);if(w.length<3)continue;
    const nm=sum(w)/w.length,est=q[1]*nm/100/D.shares,low=!(est>=0.5);   // 推估 ≤ 0 或太小（轉虧為盈、低基期）→ 百分比會爆衝，改看差幾元
    out.push({l:q[0],rev:q[1],eps:q[5],est,nm,anm:q[4],low,d:q[5]-est,s:low?null:(q[5]-est)/est*100,fl:q[0]===D.inj,abn:q[4]!=null&&q[3]!=null&&q[4]>q[3]+5})}
  return out;
}
const sxTxt=x=>x.low?(x.d>0?'+':'')+fmt(x.d,2)+' 元':x.s>300?'>+300%':x.s<-300?'<−300%':pct(x.s,0);
const sxCls=x=>sign(x.low?x.d:x.s);
function renderSx(){
  const X=sxCalc(),el=$('epsSx'),ft=$('fEps');el.hidden=ft.hidden=!X.length;if(!X.length)return;
  el.innerHTML=X.map(x=>`<div class="${sxCls(x)}${x.fl?' fl':''}" title="推估 ${fmt(x.est,2)}：營收 ${fmt(x.rev)} 億 × 淨利率 ${fmt(x.nm,1)}% ÷ ${fmt(D.shares,2)} 億股"><span>${x.l}${x.fl?(D.injSrc==='flash'?' 快訊':' 速報'):''}${x.abn?' ⚠':''}</span><b>${sxTxt(x)}</b><i>推估 ${fmt(x.est,2)}</i></div>`).join('');
  const r=X[X.length-1];
  const big=r.low?r.d>=0.5:r.s>=10,bad=r.low?r.d<=-0.5:r.s<=-10;
  $('tEps').innerHTML+=`<br>獲利驚喜 <strong class="${sxCls(r)}">${sxTxt(r)}</strong>：營收 × 前四季平均淨利率 ${fmt(r.nm,1)}% 推估 ${fmt(r.est,2)} 元，實際 ${fmt(r.eps,2)} 元（淨利率 ${r.anm==null?'—':fmt(r.anm,1)+'%'}）→ `+
    (big?'獲利率明顯<strong>優於</strong>過去一年':bad?'獲利率明顯<strong>低於</strong>過去一年':'獲利率與過去一年差不多，財報沒有太多新資訊')+(r.low?'（推估接近 0 或為負，看差幾元）':'')+(r.abn?'；<span class="pill">業外</span> 淨利率比營益率高 5 點以上，驚喜可能來自一次性業外':'');
  ft.textContent='獲利驚喜＝(實際 EPS − 推估 EPS) ÷ 推估；推估 < 0.5 元（轉虧為盈、低基期）時改顯示差幾元。推估 EPS＝該季營收（月營收加總，財報前就知道）× 前四季平均淨利率 ÷ 目前股數，不是法人預估。紅＝優於推估、綠＝低於推估；⚠＝該季淨利率比營益率高 5 點以上（可能含業外）。虛線框＝財報快訊／速報季。';
}
// 三率圖右端數字避讓：''')

open(dst, 'w', encoding='utf-8').write(s)
print('ok', dst, len(s))
