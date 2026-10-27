"""10 年財報卡：把 index.html 套成 beta.html
用法：python3 patch_10y.py index.html beta.html
搬正式版：python3 patch_10y.py index.html index.html
資料：使用者滑到卡片時，瀏覽器直接向 FinMind 抓 11 年的財報／資產負債／現金流／股利／股價（5 次請求），
     算好後存在手機 localStorage（y10v1_代號，12 小時），不經 GitHub Actions、不需回補。
"""
import sys

src, dst = sys.argv[1], sys.argv[2]
BETA = dst != src
h = open(src, encoding="utf-8").read()


def rep(old, new, n=1):
    global h
    c = h.count(old)
    assert c == n, f"錨點出現 {c} 次（預期 {n}）：{old[:60]}"
    h = h.replace(old, new)


if BETA:
    rep("<title>台股估值看板</title>", "<title>台股估值看板 β10年</title>")

# 1) 導覽列：放在「淨利」後面
rep('<a href="#np" id="chipNp">淨利</a>', '<a href="#np" id="chipNp">淨利</a><a href="#y10">10年</a>')

# 2) 卡片：放在淨利卡下面
rep('''  <div class="chart" id="cNp"></div>
  <p class="foot" id="fNp"></p>
</section>''', '''  <div class="chart" id="cNp"></div>
  <p class="foot" id="fNp"></p>
</section>
<section class="card" id="y10">
  <h2 style="display:flex;align-items:center;gap:8px;white-space:nowrap">10年財報 <small id="y10U">年度</small><span class="segm" id="y10Per" style="margin-left:auto"><button type="button" aria-pressed="true" data-p="y">年</button><button type="button" aria-pressed="false" data-p="q">季</button></span></h2>
  <div class="y10k" id="y10K"></div>
  <p class="take" id="tY10"></p>
  <div class="y10tab" id="y10Tab"><button type="button" data-t="g">📈 營收</button><button type="button" data-t="p">💹 三率</button><button type="button" data-t="e">💰 EPS股利</button><button type="button" data-t="r">🏦 ROE負債</button><button type="button" data-t="c">💵 現金流</button></div>
  <div class="chart" id="cY10" style="height:210px"></div>
  <p class="foot" id="fY10"></p>
  <details class="ind" id="y10More"><summary>年度明細表 <span>▾</span></summary><div class="tbl"><table id="tbY10"></table></div></details>
</section>
<style>
#y10Per button{padding:4px 9px}#y10 h2 small{overflow:hidden;text-overflow:ellipsis}
.y10k{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:8px 0 4px}
.y10k div{border:1px solid var(--line);border-radius:10px;padding:5px 7px;min-width:0}
.y10k span{display:block;font-size:10.5px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.y10k b{display:block;font-family:var(--f-num);font-size:15px;font-weight:600;line-height:1.25}
.y10k i{display:block;font-style:normal;font-size:10px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.y10tab{display:flex;gap:5px;overflow-x:auto;scrollbar-width:none;margin:8px 0 2px}
.y10tab::-webkit-scrollbar{display:none}
.y10tab button{flex:none;font:inherit;font-size:12px;border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:999px;padding:3px 9px;cursor:pointer}
.y10tab button[aria-pressed=true]{background:var(--accent);border-color:var(--accent);color:#fff}
#tbY10{font-family:var(--f-num);font-size:11.5px;white-space:nowrap}
#tbY10 th,#tbY10 td{padding:3px 6px;text-align:right}
#tbY10 th:first-child,#tbY10 td:first-child{position:sticky;left:0;background:var(--card);text-align:left}
#tbY10 thead th{color:var(--muted);font-weight:500}
#tbY10 tr.ttm td{color:var(--muted)}
.y10msg{font-size:13px;color:var(--muted);padding:18px 0;text-align:center}
.y10msg button{font:inherit;margin-top:8px;border:1px solid var(--accent);color:var(--accent);background:none;border-radius:999px;padding:3px 12px}
</style>''')

# 3) render() 掛上
rep("renderNp();loadFlashNp(D.id);", "renderNp();loadFlashNp(D.id);y10Init(D.id);")

# 4) 函式
JS = r'''
// ---- 10 年財報：使用者滑到卡片才向 FinMind 抓（5 次請求），算好存 localStorage 12 小時 ----
let Y10=null,Y10ID=null,Y10IO=null,Y10L=null;
let Y10T=(()=>{try{return localStorage.getItem('y10T')||'g'}catch(e){return 'g'}})(),Y10P=(()=>{try{return localStorage.getItem('y10P')||'y'}catch(e){return 'y'}})();
const Y10QD=['03-31','06-30','09-30','12-31'];
function y10Ser(rows,types,re){let d=serT(rows,types);if(!Object.keys(d).length&&re){d={};rows.forEach(r=>{if(r.value!=null&&re.test((r.origin_name||'').trim()))d[r.date]=r.value})}return d}
function buildY10(fs,bs,cf,dv,px){
  const g=(t,re)=>y10Ser(fs,t,re),b=(t,re)=>y10Ser(bs,t,re);
  const REV=g(['Revenue'],/^營業收入合計$/),GP=g(['GrossProfit'],/^營業毛利/),OP=g(['OperatingIncome'],/^營業利益/),
    NI=g(['EquityAttributableToOwnersOfParent'],/^母公司業主/),EPS=g(['EPS'],/^基本每股盈餘/);
  const CAP=b(['OrdinaryShare','CapitalStock'],/^普通股股本$/),TA=b(['TotalAssets'],/^資產總(計|額)$/),TL=b(['Liabilities','TotalLiabilities'],/^負債總(計|額)$/),
    EQP=b(['EquityAttributableToOwnersOfParent'],/^歸屬於母公司業主之權益(合計|總計)?$/),EQ=b(['Equity','TotalEquity'],/^權益總(計|額)$/);
  const OCF=toQuarterS(serT(cf,['CashFlowsFromOperatingActivities','NetCashInflowFromOperatingActivities'])),
    CX=toQuarter(cfItem(cf,['取得不動產、廠房及設備'],['PropertyAndPlantAndEquipment','AcquisitionOfPropertyPlantAndEquipment','PaymentsToAcquirePropertyPlantAndEquipment']));
  const eqAt=d=>EQP[d]!=null?EQP[d]:EQ[d]!=null?EQ[d]:null,tlAt=d=>TL[d]!=null?TL[d]:(TA[d]!=null&&EQ[d]!=null?TA[d]-EQ[d]:null);
  const e8=v=>v==null?null:v/1e8,r1=v=>v==null||!isFinite(v)?null:Math.round(v*10)/10,r2=v=>v==null||!isFinite(v)?null:Math.round(v*100)/100;
  // 單季
  const Qa=[];Object.keys(REV).filter(d=>Y10QD.includes(d.slice(5))).sort().forEach(d=>{
    const y=+d.slice(0,4),n=+d.slice(5,7)/3,rv=REV[d];if(!rv)return;
    let eps=EPS[d];if(eps==null&&NI[d]!=null&&CAP[d])eps=NI[d]/(CAP[d]/10);
    Qa.push({d,y,n,l:`${String(y).slice(2)}Q${n}`,rev:e8(rv),gp:e8(GP[d]),op:e8(OP[d]),ni:e8(NI[d]),eps,ocf:e8(OCF[`${y}-${n}`]),cx:e8(CX[`${y}-${n}`]),
      eq:e8(eqAt(d)),ta:e8(TA[d]),tl:e8(tlAt(d))})});
  if(Qa.length<4)return null;
  const S=(a,k)=>a.some(x=>x[k]==null)?null:a.reduce((s,x)=>s+x[k],0),P=(a,b)=>a==null||!b?null:a/b*100;
  // 股利：依「股利所屬年度」（year 欄的民國年）加總；同一個年度字串重複公告時取最新一筆
  const dvk={};dv.forEach(r=>{const k=String(r.year||'')+'|'+(r.CashExDividendTradingDate||r.StockExDividendTradingDate||'');if(!dvk[k]||(r.date||'')>(dvk[k].date||''))dvk[k]=r});
  const DV={};Object.values(dvk).forEach(r=>{const m=String(r.year||'').match(/(\d{2,4})\s*年/);let fy=m?+m[1]:NaN;if(fy<1000)fy+=1911;if(!(fy>1990))fy=+(r.date||'').slice(0,4)-1;
    const c=(+r.CashEarningsDistribution||0)+(+r.CashStatutorySurplus||0),s=(+r.StockEarningsDistribution||0)+(+r.StockStatutorySurplus||0);
    if(!c&&!s)return;const o=DV[fy]=DV[fy]||{c:0,s:0};o.c+=c;o.s+=s});
  // 股價：年底收盤、年均收盤
  const PY={};px.forEach(r=>{const y=+r.date.slice(0,4),o=PY[y]=PY[y]||{n:0,s:0,d:'',c:null};o.n++;o.s+=r.close;if(r.date>o.d){o.d=r.date;o.c=r.close}});
  const lastPx=px.length?px.reduce((a,r)=>r.date>a.date?r:a):null;
  const row=(l,qs,y,ttm)=>{const rev=S(qs,'rev'),gp=S(qs,'gp'),op=S(qs,'op'),ni=S(qs,'ni'),eps=S(qs,'eps'),ocf=S(qs,'ocf'),cx=S(qs,'cx');
    const z=qs[qs.length-1],pz=Qa.find(x=>x.y===z.y-1&&x.n===z.n),eqA=z.eq!=null?(pz&&pz.eq!=null?(z.eq+pz.eq)/2:z.eq):null;
    const dd=ttm?null:DV[y],pc=ttm?(lastPx&&lastPx.close):PY[y]&&PY[y].c,pa=ttm?(lastPx&&lastPx.close):PY[y]&&PY[y].s/PY[y].n;
    return {l,y,ttm,rev,gm:P(gp,rev),om:P(op,rev),nm:P(ni,rev),ni,eps,ocf,fcf:ocf!=null&&cx!=null?ocf-cx:null,cx,
      roe:ni!=null&&eqA>0?ni/eqA*100:null,debt:z.tl!=null&&z.ta?z.tl/z.ta*100:null,div:dd?dd.c:null,sdiv:dd?dd.s:null,
      po:dd&&eps>0?dd.c/eps*100:null,close:pc||null,pe:pa&&eps>0?pa/eps:null}};
  const A=[];[...new Set(Qa.map(x=>x.y))].sort().forEach(y=>{const qs=Qa.filter(x=>x.y===y);if(qs.length===4)A.push(row(String(y),qs,y,false))});
  const lq=Qa[Qa.length-1];
  if(lq.n!==4){const l4=Qa.slice(-4),ok=l4.length===4&&l4.every((x,i)=>!i||(x.y*4+x.n)-(l4[i-1].y*4+l4[i-1].n)===1);
    if(ok)A.push(row('近4季',l4,lq.y,true))}
  A.forEach(x=>{let pr=null;
    if(!x.ttm)pr=A.find(z=>!z.ttm&&z.y===x.y-1)||null;
    else{const pt=Qa.filter(q=>(q.y*4+q.n)<=(lq.y*4+lq.n)-4).slice(-4);if(pt.length===4)pr={rev:S(pt,'rev'),eps:S(pt,'eps')}}
    x.ry=pr&&pr.rev?(x.rev/pr.rev-1)*100:null;x.ey=pr&&pr.eps>0&&x.eps!=null?(x.eps/pr.eps-1)*100:null});
  // 單季序列（季模式）：ROE 用近四季淨利 ÷ 平均權益
  const Qr=Qa.map((x,i)=>{const ly=Qa.find(z=>z.y===x.y-1&&z.n===x.n),l4=i>=3?Qa.slice(i-3,i+1):null,c4=l4&&(x.y*4+x.n)-(l4[0].y*4+l4[0].n)===3?l4:null;
    const ni4=c4?S(c4,'ni'):null,eqA=x.eq!=null?(c4&&c4[0]&&ly&&ly.eq!=null?(x.eq+ly.eq)/2:x.eq):null;
    return {l:x.l,rev:x.rev,gm:P(x.gp,x.rev),om:P(x.op,x.rev),nm:P(x.ni,x.rev),ni:x.ni,eps:x.eps,ocf:x.ocf,fcf:x.ocf!=null&&x.cx!=null?x.ocf-x.cx:null,
      roe:ni4!=null&&eqA>0?ni4/eqA*100:null,debt:x.tl!=null&&x.ta?x.tl/x.ta*100:null,ry:ly&&ly.rev?(x.rev/ly.rev-1)*100:null,ey:ly&&ly.eps>0&&x.eps!=null?(x.eps/ly.eps-1)*100:null}});
  const rr=o=>{const k={};for(const [a,v] of Object.entries(o))k[a]=typeof v==='number'?(['eps','div','sdiv'].includes(a)?r2(v):r1(v)):v;return k};
  return {A:A.slice(-12).map(rr),Q:Qr.slice(-40).map(rr),asof:lq.l};
}
async function loadY10(id){
  const k='y10v1_'+id,c=store.get(k);
  if(c&&Date.now()-c.t<12*3600e3&&c.v){Y10=c.v;Y10L=null;renderY10();return}
  if(Y10L===id)return;Y10L=id;
  $('cY10').hidden=true;$('tY10').innerHTML='<div class="y10msg">⏳ 正在向 FinMind 抓 11 年財報（約 5–10 秒）…</div>';
  try{
    const y=new Date().getFullYear(),st=`${y-11}-01-01`;
    const [fs,bs,cf,dv,px]=await Promise.all([fm('TaiwanStockFinancialStatements',id,st),fm('TaiwanStockBalanceSheet',id,st),
      fm('TaiwanStockCashFlowsStatement',id,st).catch(()=>[]),fm('TaiwanStockDividend',id,st).catch(()=>[]),fm('TaiwanStockPrice',id,st).catch(()=>[])]);
    if(Y10ID!==id)return;
    const v=buildY10(fs,bs,cf,dv,px);Y10L=null;
    if(!v){$('tY10').innerHTML='<div class="y10msg">歷史財報不足 4 季，無法顯示</div>';return}
    Y10=v;try{store.set(k,{t:Date.now(),v})}catch(e){}
    if(!localStorage.getItem(k))try{Object.keys(localStorage).filter(x=>x.startsWith('y10v1_')).forEach(x=>localStorage.removeItem(x));store.set(k,{t:Date.now(),v})}catch(e){}
    renderY10();
  }catch(e){Y10L=null;if(Y10ID!==id)return;
    $('tY10').innerHTML=`<div class="y10msg">⚠️ ${e.message}<br><button type="button" id="y10Re">重試</button></div>`;
    $('y10Re').onclick=()=>loadY10(id)}
}
function y10Init(id){
  if(Y10ID===id&&(Y10||Y10L===id)){if(Y10)renderY10();return}
  Y10ID=id;Y10=null;Y10L=null;$('y10K').innerHTML='';$('tbY10').innerHTML='';$('fY10').textContent='';$('cY10').hidden=true;
  $('tY10').innerHTML='<div class="y10msg">滑到這裡會自動載入</div>';
  if(Y10IO)Y10IO.disconnect();
  if(!('IntersectionObserver' in window)){loadY10(id);return}
  Y10IO=new IntersectionObserver(es=>{if(es.some(e=>e.isIntersecting)){Y10IO.disconnect();loadY10(id)}},{rootMargin:'600px 0px'});
  Y10IO.observe($('y10'));
}
function renderY10(){
  if(!Y10)return;
  const A=Y10.A,F=A.filter(x=>!x.ttm),T=A.find(x=>x.ttm),mu=css('--muted'),up=css('--up'),dn=css('--down'),acc=css('--accent'),acc2=css('--accent2'),warm=css('--warm'),fg=css('--fg');
  const f=(v,d)=>v==null?'—':fmt(v,d==null?(Math.abs(v)<10?2:Math.abs(v)<100?1:0):d),sg=v=>v==null?'':v>0?'up':v<0?'dn':'';
  const cagr=(k)=>{const a=F.find(x=>x[k]!=null),z=[...F].reverse().find(x=>x[k]!=null);if(!a||!z||a===z)return {t:'—',s:''};
    const n=z.y-a.y;if(!(a[k]>0))return {t:'—',s:`${a.l} 為虧損`};if(!(z[k]>0))return {t:'轉虧',s:`${a.l}→${z.l}`,v:-1};
    const v=(Math.pow(z[k]/a[k],1/n)-1)*100;return {t:pct(v,1),s:`${a.l.slice(2)}→${z.l.slice(2)}・${n}年`,n,v}};
  const cr=cagr('rev'),ce=cagr('eps'),roes=F.map(x=>x.roe).filter(v=>v!=null),avgR=roes.length?roes.reduce((a,b)=>a+b,0)/roes.length:null;
  const loss=F.filter(x=>x.eps!=null&&x.eps<0).length;
  let streak=0;for(const x of [...F].reverse()){if(x.div>0)streak++;else break}
  const pos=F.filter(x=>x.po!=null),avgPo=pos.length?pos.reduce((a,x)=>a+x.po,0)/pos.length:null;
  const fc=F.filter(x=>x.fcf!=null&&x.ni!=null),sF=fc.reduce((a,x)=>a+x.fcf,0),sN=fc.reduce((a,x)=>a+x.ni,0),conv=fc.length>=3&&sN>0?sF/sN*100:null;
  $('y10K').innerHTML=[
    ['營收年複合成長',`<b class="${sg(cr.v)}">${cr.t}</b>`,cr.s],
    ['EPS 年複合成長',`<b class="${sg(ce.v)}">${ce.t}</b>`,ce.s],
    ['平均 ROE',`<b>${avgR==null?'—':fmt(avgR,1)+'%'}</b>`,roes.length?`最低 ${fmt(Math.min(...roes),1)}%・${roes.length} 年`:''],
    ['虧損年數',`<b class="${loss?'dn':''}">${loss} 年</b>`,`共 ${F.length} 個完整年度`],
    ['連續配息',`<b>${streak} 年</b>`,avgPo==null?'無配息資料':`平均配息率 ${fmt(avgPo,0)}%`],
    ['自由現金流／淨利',`<b class="${conv==null?'':conv>=80?'up':conv<40?'dn':''}">${conv==null?'—':fmt(conv,0)+'%'}</b>`,fc.length?`${fc.length} 年累計`:'無現金流資料']
  ].map(([a,b,c])=>`<div><span>${a}</span>${b}<i>${c||'&nbsp;'}</i></div>`).join('');
  // 判讀：近四季 EPS 跟 10 年常態比（降低近因偏誤）
  const E=F.map(x=>x.eps).filter(v=>v!=null),mE=E.length?E.reduce((a,b)=>a+b,0)/E.length:null,sd=E.length>2?Math.sqrt(E.reduce((a,v)=>a+(v-mE)**2,0)/E.length):null;
  const cv=mE>0&&sd!=null?sd/mE:null,now=T?T.eps:F.length?F[F.length-1].eps:null,ratio=mE>0&&now!=null?now/mE:null,lastL=T?'近四季':F.length?F[F.length-1].l:'';
  const drops=F.filter(x=>x.ey!=null&&x.ey<=-20).length;
  const kind=loss?'曾虧損・循環':drops>=2?'循環型':ce.v>=8?'穩定成長':'平穩型';
  let V;
  if(ratio==null)V=['','⚪ 資料不足',''];
  else if(kind==='穩定成長')V=['ok','🟢 長期成長',`EPS ${ce.n} 年複合成長 ${ce.t}、EPS 年減超過 2 成只有 ${drops} 次；比 10 年平均高是成長的結果，重點看成長能否延續`];
  else if(ratio>=1.6&&kind!=='穩定成長')V=['bad','🔴 位在獲利高檔',`${lastL} EPS ${f(now,2)} 是 ${F.length} 年平均 ${f(mE,2)} 的 ${fmt(ratio,1)} 倍；循環股在高峰時本益比最低，「看起來便宜」最容易買在頂部`];
  else if(ratio>=1.3)V=['mid','🟠 高於 10 年常態',`${lastL} EPS ${f(now,2)} 是平均的 ${fmt(ratio,1)} 倍，評價時別直接用高峰 EPS 外推`];
  else if(ratio<=.6&&mE>0)V=['ok','🟢 位在獲利低檔',`${lastL} EPS ${f(now,2)} 只有平均 ${f(mE,2)} 的 ${fmt(ratio,1)} 倍；若體質沒變，可能是循環谷底（要確認不是結構性衰退）`];
  else V=['','⚪ 接近 10 年常態',`${lastL} EPS ${f(now,2)}，${F.length} 年平均 ${f(mE,2)}`];
  $('tY10').innerHTML=`<span class="pill">${kind}</span> <span class="pill ${V[0]}">${V[1]}</span> ${V[2]}`+`<br><span style="color:var(--muted);font-size:12px">分類依據：虧損 ${loss} 年、EPS 年減超過 2 成 ${drops} 次${cv!=null?`、EPS 波動度（標準差÷平均）${fmt(cv,2)}`:''}</span>`;
  // 圖
  const Q=Y10P==='q',R=Q?Y10.Q:A;$('y10U').textContent=Q?`單季｜${R.length}季`:`年度｜${F.length}年${T?'＋近4季':''}`;
  $('y10Per').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.p===Y10P));
  $('y10Tab').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.t===Y10T));
  $('cY10').hidden=false;const ch=mk('cY10'),o=base();o.xAxis.data=R.map(x=>Q?x.l:(x.ttm?'近4季':"'"+x.l.slice(2)));o.yAxis.scale=false;
  const N=R.length,every=Q?4:2,show=i=>Q?(i>=N-4):((N-1-i)%every===0);
  const lab=(fm,col)=>({show:true,position:'top',fontSize:9,color:col||mu,fontFamily:'IBM Plex Mono',formatter:p=>show(p.dataIndex)&&p.value!=null?fm(p.value):''});
  const bar=(name,k,col,fm)=>({name,type:'bar',barCategoryGap:Q?'22%':'30%',label:lab(fm),itemStyle:{color:typeof col==='function'?up:col},
    data:R.map(x=>({value:x[k],itemStyle:{color:typeof col==='function'?col(x):col,opacity:x.ttm?.5:1,borderColor:typeof col==='function'?col(x):col,borderWidth:x.ttm?1.5:0,borderType:'dashed',borderRadius:[2,2,0,0]}}))});
  const line=(name,k,col,ya,dash)=>({name,type:'line',yAxisIndex:ya||0,data:R.map(x=>x[k]),symbol:'circle',symbolSize:Q?2:4,connectNulls:true,lineStyle:{width:2,color:col,type:dash?'dashed':'solid'},itemStyle:{color:col},
    endLabel:{show:true,color:col,fontSize:10,fontFamily:'IBM Plex Mono',formatter:p=>p.value==null?'':fmt(p.value,1)}});
  const gc=k=>x=>x[k]==null?mu:x[k]>0?up:x[k]<0?dn:mu,big=v=>Math.abs(v)>=1000?String(Math.round(v)):f(v);
  let foot='';o.grid={...o.grid,top:30};
  if(Y10T==='g'){
    o.yAxis=[o.yAxis,{type:'value',show:false,scale:false}];
    o.series=[bar('營收(億)','rev',gc('ry'),big),{...line('年增率','ry',warm,1),endLabel:{show:false},label:{show:true,position:'bottom',fontSize:9,color:warm,fontFamily:'IBM Plex Mono',formatter:p=>show(p.dataIndex)&&p.value!=null?(p.value>0?'+':'')+Math.round(p.value)+'%':''},labelLayout:{hideOverlap:true}}];
    const ys=R.map(x=>x.ry).filter(v=>v!=null),lo=ys.length?Math.min(...ys):0,hi=ys.length?Math.max(...ys):10,sp=Math.max(hi-lo,10);
    o.yAxis[1].min=Math.floor(lo-sp*1.75);o.yAxis[1].max=Math.ceil(hi+sp*.25);
    {const bm=Math.max(...R.map(x=>x.rev||0)),st=(v=>{const e=Math.pow(10,Math.floor(Math.log10(v)));return [1,2,2.5,5,10].map(k=>k*e).find(k=>k>=v)})(bm*1.65/5||1);o.yAxis[0].interval=st;o.yAxis[0].max=Math.ceil(bm*1.65/st)*st}
    foot=`柱：${Q?'單季':'年度'}營收（紅＝年增、綠＝年減${Q?'':'，虛線＝近四季合計'}）；線：年增率。`;
  }else if(Y10T==='p'){
    o.yAxis.scale=true;o.yAxis.axisLabel.formatter='{value}%';o.grid.right=34;
    o.series=[['毛利率','gm',acc],['營益率','om',acc2],['淨利率','nm',warm]].map(([n,k,c])=>line(n,k,c));
    foot='淨利率以歸屬母公司淨利計算；毛利率長期穩定或往上＝有定價能力，景氣差時掉最多的通常是營益率。';
  }else if(Y10T==='e'){
    o.series=[bar('EPS','eps',gc('ey'),v=>f(v,Math.abs(v)<100?2:0))];
    if(!Q)o.series.push({...bar('現金股利','div',acc2,v=>f(v,2)),label:{show:false}});
    foot=Q?'柱：單季 EPS（紅＝年增、綠＝年減）。':'柱：年度 EPS（四季加總，紅＝年增、綠＝年減）＋該年度盈餘配發的現金股利（青綠）。配息率看明細表。EPS 未還原減資／增資，股本大變動的年份前後不能直接比。';
  }else if(Y10T==='r'){
    o.yAxis.axisLabel.formatter='{value}%';o.grid.right=34;
    o.series=[line('ROE','roe',acc),line('負債比','debt',warm,0,true)];
    o.series[0].markLine={silent:true,symbol:'none',label:{show:true,position:'insideStartTop',formatter:'15%',color:mu,fontSize:9},lineStyle:{color:mu,type:'dotted'},data:[{yAxis:15}]};
    foot=`ROE＝母公司淨利 ÷ 平均股東權益${Q?'（近四季淨利）':''}，長期 ≥15% 算優秀；負債比＝總負債 ÷ 總資產（虛線），金融業天生很高不適用。`;
  }else{
    o.series=[bar('營業現金流','ocf',acc,big),{...bar('自由現金流','fcf',acc2,big),label:{show:false}},{...line('母公司淨利','ni',fg),endLabel:{show:false}}];
    foot='自由現金流＝營業現金流 − 資本支出（取得不動產、廠房及設備）。長期淨利有、自由現金流卻常是負的＝賺的錢都要再投資或卡在應收／存貨。';
  }
  o.tooltip.formatter=ps=>{const x=R[ps[0].dataIndex],L=[`<b>${x.ttm?'近四季（'+Y10.asof+' 止）':x.l}</b>`];
    L.push(`營收 ${f(x.rev,0)} 億（年增 ${pct(x.ry,1)}）`);L.push(`毛利率 ${f(x.gm,1)}%・營益率 ${f(x.om,1)}%・淨利率 ${f(x.nm,1)}%`);
    L.push(`EPS ${f(x.eps,2)} 元（年增 ${x.ey==null?'—':pct(x.ey,0)}）`+(x.div!=null?`・現金股利 ${f(x.div,2)}${x.po!=null?`（配息率 ${fmt(x.po,0)}%）`:''}`:''));
    L.push(`ROE ${f(x.roe,1)}%・負債比 ${f(x.debt,1)}%`);if(x.ocf!=null)L.push(`營業現金流 ${f(x.ocf)}・自由現金流 ${f(x.fcf)}・淨利 ${f(x.ni)} 億`);
    if(x.pe!=null)L.push(`${x.ttm?'目前':'年均'}本益比 ${fmt(x.pe,1)} 倍`);return L.join('<br>')};
  ch.setOption(o,true);ch.resize();
  $('fY10').textContent=foot+' 資料：FinMind，進這一頁才即時抓，手機快取 12 小時。';
  // 明細表（年度）
  const c=(v,d)=>v==null?'—':fmt(v,d),cp=v=>v==null?'—':`<span class="${sg(v)}">${pct(v,0)}</span>`;
  $('tbY10').innerHTML='<thead><tr><th>年度</th><th>營收億</th><th>年增</th><th>毛利率</th><th>營益率</th><th>淨利率</th><th>EPS</th><th>EPS年增</th><th>現金股利</th><th>配息率</th><th>ROE</th><th>負債比</th><th>自由現金流</th><th>年均PE</th></tr></thead><tbody>'+
    [...A].reverse().map(x=>`<tr class="${x.ttm?'ttm':''}"><td>${x.ttm?'近四季':x.l}</td><td>${c(x.rev,0)}</td><td>${cp(x.ry)}</td><td>${c(x.gm,1)}</td><td>${c(x.om,1)}</td><td>${c(x.nm,1)}</td><td>${c(x.eps,2)}</td><td>${cp(x.ey)}</td><td>${c(x.div,2)}${x.sdiv?`<sup title="另配股票股利 ${x.sdiv} 元">+股</sup>`:''}</td><td>${c(x.po,0)}${x.po!=null?'%':''}</td><td>${c(x.roe,1)}</td><td>${c(x.debt,1)}</td><td>${c(x.fcf,0)}</td><td>${c(x.pe,1)}</td></tr>`).join('')+'</tbody>';
}
$('y10Per').addEventListener('click',e=>{const b=e.target.closest('button[data-p]');if(!b)return;Y10P=b.dataset.p;try{localStorage.setItem('y10P',Y10P)}catch(_){}renderY10()});
$('y10Tab').addEventListener('click',e=>{const b=e.target.closest('button[data-t]');if(!b)return;Y10T=b.dataset.t;try{localStorage.setItem('y10T',Y10T)}catch(_){}renderY10()});
'''
rep("// 與 fetch.py 的 build_cf() 相同邏輯\nfunction buildCf(", JS + "// 與 fetch.py 的 build_cf() 相同邏輯\nfunction buildCf(")

open(dst, "w", encoding="utf-8").write(h)
print(f"{src} → {dst} OK")
