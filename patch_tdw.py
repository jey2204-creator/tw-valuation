#!/usr/bin/env python3
"""第三批①：個股頁「大戶持股」卡（集保週資料，手機直接向 FinMind 抓 TaiwanStockHoldingSharesPer）
用法：python3 patch_tdw.py index.html beta.html
"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:70])
    s = s.replace(old, new)

# ① 導覽列
rep('<a href="#chip">籌碼</a><a href="#margin">三率</a>', '<a href="#chip">籌碼</a><a href="#tdw">大戶</a><a href="#margin">三率</a>')

# ② 卡片（逐日籌碼之後、三率之前）
rep('<section class="card" id="margin">', '''<section class="card" id="tdw">
  <h2 style="display:flex;align-items:center;gap:8px;white-space:nowrap">大戶持股 <small>週｜集保</small><span class="segm" id="tdwSeg" style="margin-left:auto"><button type="button" aria-pressed="true" data-n="52">1年</button><button type="button" aria-pressed="false" data-n="156">3年</button></span></h2>
  <p class="take tight" id="tTdw"></p>
  <div class="sx" id="tdwK" hidden></div>
  <div class="chart" id="cTdw" hidden style="height:180px"></div>
  <p class="foot" id="fTdw"></p>
  <p class="foot" id="fTdw2" hidden></p>
</section>
<style>#tdwK i.tdwx{white-space:normal;line-height:1.3;margin-top:2px;border-top:1px dashed var(--line);padding-top:2px}#tdw .take.tight{margin-bottom:4px}</style>
<section class="card" id="margin">''')

# ③ render() 後面叫 tdwInit
rep("renderKl();renderChip();renderGuide();", "renderKl();renderChip();tdwInit(D.id);renderGuide();")

# ④ 程式
rep("// ---- 逐日籌碼（chip.json）", r'''// ---- 大戶持股（集保週資料）：讀本站 data/tdcc_s/<前兩碼>.json 分片（fetch_tdcc.py 每天產生；FinMind 集保分級是付費資料集，瀏覽器抓不到） ----
let TDW=null,TDWID=null,TDWIO=null,TDWL=null,TDWN=(()=>{try{return +localStorage.getItem('tdwN')||52}catch(e){return 52}})();
async function loadTdw(id){
  if(TDWL===id)return;TDWL=id;
  $('tTdw').innerHTML='<div class="y10msg">⏳ 載入集保週資料…</div>';
  try{
    const g=String(id).slice(0,2);let v=null;
    if(/^\d\d$/.test(g)){const r=await fetch(`data/tdcc_s/${g}.json?t=${Math.floor(Date.now()/3e5)}`);if(r.ok){const j=await r.json(),h=j.d&&j.d[id];
      if(h){v=j.weeks.map((w,i)=>h[i]?{d:`${w.slice(0,4)}-${w.slice(4,6)}-${w.slice(6)}`,b4:h[i][0],b10:h[i][1],ppl:h[i][2]}:null).filter(Boolean);if(v.length<2)v=null}}}
    if(TDWID!==id)return;TDWL=null;
    if(!v){$('tTdw').innerHTML='<div class="y10msg">這檔還沒有集保分級資料（新上市、ETF，或資料回補中）</div>';return}
    TDW=v;renderTdw();
  }catch(e){TDWL=null;if(TDWID!==id)return;$('tTdw').innerHTML=`<div class="y10msg">⚠️ ${e.message}<br><button type="button" id="tdwRe">重試</button></div>`;$('tdwRe').onclick=()=>loadTdw(id)}
}
function tdwInit(id){
  if(TDWID===id&&(TDW||TDWL===id)){if(TDW)renderTdw();return}
  TDWID=id;TDW=null;TDWL=null;$('tdwK').hidden=true;$('tdwK').innerHTML='';$('fTdw').textContent='';$('cTdw').hidden=true;
  $('tTdw').innerHTML='<div class="y10msg">滑到這裡會自動載入</div>';
  if(TDWIO)TDWIO.disconnect();
  if(!('IntersectionObserver' in window)){loadTdw(id);return}
  TDWIO=new IntersectionObserver(es=>{if(es.some(e=>e.isIntersecting)){TDWIO.disconnect();loadTdw(id)}},{rootMargin:'600px 0px'});
  TDWIO.observe($('tdw'));
}
function renderTdw(){
  if(!TDW)return;
  const A=TDW,R=A.slice(-TDWN),L=A.length-1,r=A[L],at=n=>A[L-n]||null,w1=at(1),w4=at(4),w13=at(13),w52=at(52);
  const acc=css('--accent'),acc2=css('--accent2'),warm=css('--warm'),mu=css('--muted');
  const d=(a,b,k)=>a&&b&&a[k]!=null&&b[k]!=null?a[k]-b[k]:null,pp=(a,b)=>a&&b&&a.ppl&&b.ppl?(a.ppl/b.ppl-1)*100:null;
  const c4=d(r,w4,'b4'),p4=pp(r,w4),c1=d(r,w1,'b4'),c13=d(r,w13,'b4'),c52=d(r,w52,'b4');
  // 連續週數（大戶比同方向）
  let st=0,dir=0;for(let i=L;i>0;i--){const x=A[i].b4-A[i-1].b4;if(!dir){if(x===0)break;dir=x>0?1:-1;st=1}else if((x>0?1:x<0?-1:0)===dir)st++;else break}
  // 位階：近 52 週
  const y=A.slice(-52).map(x=>x.b4),hi=Math.max(...y),lo=Math.min(...y),pos=hi>lo?(r.b4-lo)/(hi-lo)*100:null;
  // 標籤（與動能頁同一規則，看 4 週）
  const tag=c4==null||p4==null?['','⚪ 資料不足']:c4>0.3&&p4<-1?['ok','🟢 籌碼集中']:c4>0.3&&p4>3?['mid','🟠 散戶追進']:c4<-0.3&&p4>1?['bad','🔴 籌碼分散']:c4>0.3?['ok','🟢 大戶增持']:c4<-0.3?['mid','🟠 大戶減持']:['','⚪ 變化不大'];
  const why={'🟢 籌碼集中':'大戶比例上升、股東人數減少 → 散戶賣給大戶，籌碼往少數人手上集中','🟠 散戶追進':'大戶比例與股東人數同時增加 → 新進的人多，追價資金多、波動會變大','🔴 籌碼分散':'大戶比例下降、股東人數增加 → 大戶出貨給散戶，通常不是好事','🟢 大戶增持':'大戶比例上升、股東人數沒什麼變 → 大戶在市場上慢慢吸籌，但還沒看到散戶明顯退場','🟠 大戶減持':'大戶比例下降、股東人數沒什麼變 → 大戶在減碼，看是不是連續好幾週','⚪ 變化不大':'4 週內大戶比例與人數都沒有明顯變化','⚪ 資料不足':'還沒累積 4 週資料'}[tag[1]];
  const sg=(v,dd=2,u='')=>v==null?'—':`<strong class="${sign(v)}">${(v>0?'+':'')+fmt(v,dd)}${u}</strong>`;
  const short={'🟢 籌碼集中':'散戶賣給大戶，籌碼集中','🟠 散戶追進':'大戶與人數同增，追價資金多','🔴 籌碼分散':'大戶出貨給散戶','🟢 大戶增持':'大戶慢慢吸籌','🟠 大戶減持':'大戶在減碼','⚪ 變化不大':'4 週內沒有明顯變化','⚪ 資料不足':'還沒累積 4 週資料'}[tag[1]];
  $('tTdw').innerHTML=`<span class="pill ${tag[0]}">${tag[1]}</span> ${short}`+(st>=3?`，已連續 <strong>${st} 週${dir>0?'增加':'減少'}</strong>`:'')+(pos!=null&&A.length>=20?`・近一年 <strong>${fmt(pos,0)}%</strong> 位置`:'')+
    (D.cyclical?' <span class="pill">循環股</span>':'')+` <span class="y10tip" data-tdwt>說明 ▾</span>`;
  const sgi=(v,dd=2,u='')=>v==null?'—':(v>0?'+':'')+fmt(v,dd)+u;
  $('tdwK').hidden=false;$('tdwK').innerHTML=[['400張以上',fmt(r.b4,1)+'%',c4,'4週',`週 ${sgi(c1)}<br>13週 ${sgi(c13)}`+(c52!=null?`<br>52週 ${sgi(c52)}`:'')],['千張以上',fmt(r.b10,1)+'%',d(r,w4,'b10'),'4週',`週 ${sgi(d(r,w1,'b10'))}<br>13週 ${sgi(d(r,w13,'b10'))}`],['股東人數',r.ppl>=10000?fmt(r.ppl/10000,1)+'萬':fmt(r.ppl),p4,'4週%',`${fmt(r.ppl)} 人<br>13週 ${sgi(pp(r,w13),1,'%')}`]]
    .map(([a,b,c,u,x])=>`<div class="${sign(a==='股東人數'?(c==null?null:-c):c)}"><span>${a}</span><b>${b}</b><i>${c==null?'&nbsp;':u+' '+(c>0?'+':'')+fmt(c,a==='股東人數'?1:2)}</i><i class="tdwx" hidden>${x}</i></div>`).join('');
  $('tdw').querySelectorAll('.tdwx').forEach(e=>e.hidden=!$('tdw').classList.contains('open'));
  const o=base(),ch=mk('cTdw');$('cTdw').hidden=false;
  o.xAxis.data=R.map(x=>x.d);o.xAxis.axisLabel.interval=Math.max(0,Math.round(R.length/6)-1);o.xAxis.axisLabel.formatter=(v,i)=>{const m=v.slice(2,7).replace('-','/'),pv=R[i-1]&&R[i-1].d.slice(0,7);return pv===v.slice(0,7)&&i%2?'':m};
  o.yAxis.scale=true;o.yAxis.axisLabel.formatter='{value}%';o.grid.right=40;
  o.yAxis=[o.yAxis,{...o.yAxis,scale:true,splitLine:{show:false},axisLabel:{show:false}}];
  const SZ=R.length<=30?4:R.length<=60?3:R.length<=110?2:0,line=(name,k,col,ya,dash)=>({name,type:'line',yAxisIndex:ya||0,data:R.map(x=>x[k]),showSymbol:SZ>0,symbol:'circle',symbolSize:(v,p)=>p.dataIndex===R.length-1?SZ+1.5:SZ,connectNulls:true,lineStyle:{width:ya?1.5:2,color:col,type:dash?'dashed':'solid'},itemStyle:{color:col},endLabel:{show:true,color:col,fontSize:10,fontFamily:'IBM Plex Mono',formatter:p=>p.value==null?'':(ya?(p.value>=10000?fmt(p.value/10000,1)+'萬':fmt(p.value)):fmt(p.value,1)+'%')}});
  o.series=[line('400張以上%','b4',acc),line('千張以上%','b10',acc2,0,true),line('股東人數','ppl',warm,1,true)];
  o.tooltip.formatter=ps=>{const x=R[ps[0].dataIndex];return `<b>${x.d}</b><br>400 張以上 ${fmt(x.b4,2)}%<br>千張以上 ${fmt(x.b10,2)}%<br>股東人數 ${fmt(x.ppl)} 人`};
  ch.setOption(o,true);ch.resize();spreadEnd(ch,o,[0,1,2]);
  $('tdwSeg').hidden=A.length<=52;$('tdwSeg').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',+b.dataset.n===TDWN));
  $('fTdw').textContent=`集保 ${r.d.slice(5).replace('-','/')} 週`+(A.length<52?`・本站累積 ${A.length} 週（主題成份股回補中，其他股票每週自動變長）`:'');
  $('fTdw2').hidden=!$('tdw').classList.contains('open');$('fTdw2').textContent=`${why}。集保戶股權分散表每週六更新，400 張以上＝持股 40 萬股以上的人（含法人、董監），千張以上＝100 萬股以上；股東人數（右軸）＝所有集保戶。四週規則：大戶比 +0.3 點且人數 −1%＝集中、大戶比 +0.3 且人數 +3%＝散戶追進、大戶比 −0.3 且人數 +1%＝分散；只有大戶比動＝增持／減持。注意：除權息前後、法人換倉、ETF 成份調整都會讓大戶比短期跳動，看 4～13 週趨勢比單週可靠。`+(D.cyclical?'循環股高峰期大戶比例常先降、人數暴增（散戶接最後一棒），比財報更早反映。':'')+`資料：集保結算所（本站每日排程抓；FinMind 的集保分級為付費資料集）。`;
}
$('tdw').addEventListener('click',e=>{if(!TDW||!e.target.closest('#tdwK,[data-tdwt],#tTdw .pill'))return;const o=$('tdw').classList.toggle('open');$('tdw').querySelectorAll('.tdwx').forEach(x=>x.hidden=!o);$('fTdw2').hidden=!o;const t=$('tdw').querySelector('[data-tdwt]');if(t)t.textContent=o?'收起 ▴':'說明 ▾'});
$('tdwSeg').addEventListener('click',e=>{const b=e.target.closest('button[data-n]');if(!b||!TDW)return;TDWN=+b.dataset.n;try{localStorage.setItem('tdwN',TDWN)}catch(_){}renderTdw()});
// ---- 逐日籌碼（chip.json）''')

open(dst, 'w', encoding='utf-8').write(s)
print('ok', dst, len(s))
