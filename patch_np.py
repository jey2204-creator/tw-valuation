"""淨利卡（①淨利直方圖＋②本業／業外拆解）：把 index.html 套成 beta_np.html
用法：python3 patch_np.py index.html beta_np.html
搬正式版：python3 patch_np.py index.html index.html（記得把 BETA 標題那段拿掉，見 BETA 參數）
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
    rep("<title>台股估值看板</title>", "<title>台股估值看板 β淨利</title>")

# 1) 導覽列
rep('<a href="#eps">EPS</a>', '<a href="#eps">EPS</a><a href="#np" id="chipNp">淨利</a>')

# 2) 卡片：放在 EPS 卡下面
rep('''  <div class="chart" id="cEps"></div>
</section>''', '''  <div class="chart" id="cEps"></div>
</section>
<section class="card" id="np" hidden>
  <h2 style="display:flex;align-items:center;gap:8px">淨利 <small>季｜億元</small><span class="segm" id="npSeg" style="margin-left:auto"><button type="button" aria-pressed="true" data-m="n">淨利</button><button type="button" aria-pressed="false" data-m="s">本業／業外</button></span></h2>
  <p class="take" id="tNp"></p>
  <div class="chart" id="cNp"></div>
  <p class="foot" id="fNp"></p>
</section>''')

# 3) render() 掛上
rep("renderCx();renderCf();renderInv();renderChip();renderGuide();",
    "renderNp();loadFlashNp(D.id);renderCx();renderCf();renderInv();renderChip();renderGuide();")

# 4) 即時查詢：多算 np；快取鍵換版，舊快取沒有 np
rep("cf:buildCf(fs,cf,q),last:", "cf:buildCf(fs,cf,q),np:buildNp(fs,q),last:")
rep("const k='live4_'+id", "const k='live5_'+id")

# 5) 函式
JS = r'''
// ---- 淨利：D.np 每季 [季別, 營業利益, 稅前淨利, 稅後淨利(合併), 歸屬母公司淨利]（億）；業外＝稅前−營業利益 ----
// 與 fetch.py 的 build_np() 相同邏輯
function buildNp(fs,q){
  const g=(types,re)=>{let d=serT(fs,types);if(!Object.keys(d).length&&re){d={};fs.forEach(r=>{if(r.value!=null&&re.test((r.origin_name||'').trim()))d[r.date]=r.value})}return d};
  const op=serT(fs,['OperatingIncome']),
    pre=g(['PreTaxIncome','IncomeBeforeIncomeTax','ProfitLossBeforeTax'],/^(繼續營業單位)?稅前(淨利|損益)/),
    nn=g(['TotalNonoperatingIncomeAndExpense','NonoperatingIncomeAndExpense'],/^營業外收入及支出(合計)?$/),
    na=serT(fs,['IncomeAfterTaxes','NetIncome']),pa=serT(fs,['EquityAttributableToOwnersOfParent']);
  const b=v=>v==null?null:Math.round(v/1e6)/100,out=[];
  q.forEach(x=>{const y=2000+ +x[0].slice(0,2),n=+x[0][3],d=`${y}-${['03-31','06-30','09-30','12-31'][n-1]}`;
    const ni=pa[d]!=null?pa[d]:na[d];if(ni==null)return;
    let P=pre[d];if(P==null&&op[d]!=null&&nn[d]!=null)P=op[d]+nn[d];
    out.push([x[0],b(op[d]),b(P),b(na[d]),b(ni)])});
  return out;
}
let NPM=(()=>{try{return localStorage.getItem('npM')||'n'}catch(e){return 'n'}})(),NPF=null;
async function loadFlashNp(id){
  if(!NPF)NPF=fetch('data/flash.json?t='+Math.floor(Date.now()/6e5)).then(r=>r.ok?r.json():null).catch(()=>null);
  const F=await NPF;if(!F||!D||D.id!==id||!(D.np||[]).length)return;
  const it=(F.items||[]).filter(x=>x.c===id&&x.q&&x.s&&(x.s.ni!=null||x.s.eps!=null)).sort((a,b)=>a.q!==b.q?(a.q<b.q?1:-1):(a.s.ni==null)!==(b.s.ni==null)?(a.s.ni==null?1:-1):(a.t<b.t?1:-1))[0];
  if(!it)return;
  // 只有 EPS（法說／自結公告）→ 淨利 ≈ EPS × 股數（億股）
  const est=it.s.ni==null;if(est&&!D.shares)return;
  const l=it.q.slice(2,4)+'Q'+it.q.slice(-1);if(l!==qNext(D.np[D.np.length-1][0]))return;
  const md=(it.t||'').split(' ')[0].split('/').slice(1).join('/');
  D._fl={id,l,op:it.s.op!=null?it.s.op:null,pre:it.s.pre!=null?it.s.pre:null,na:null,ni:est?+(it.s.eps*D.shares).toFixed(2):it.s.ni,eps:it.s.eps,est,fl:md||'—'};renderNp();
}
function npRows(){
  const R=(D.np||[]).map(x=>({l:x[0],op:x[1],pre:x[2],na:x[3],ni:x[4]}));
  if(D._fl&&D._fl.id===D.id&&R.length&&D._fl.l===qNext(R[R.length-1].l))R.push({...D._fl});
  const ix={};R.forEach((r,i)=>ix[r.l]=i);
  const ly=l=>R[ix[String(+l.slice(0,2)-1).padStart(2,'0')+l.slice(2)]];
  const gr=(c,p)=>p==null||c==null?{}:p>0?(c>0?{v:(c/p-1)*100}:{t:'轉虧'}):c>0?{t:'轉盈'}:{t:'虧損'};
  R.forEach((r,i)=>{r.nn=r.pre!=null&&r.op!=null?+(r.pre-r.op).toFixed(2):null;r.sh=r.pre>0&&r.nn!=null?r.nn/r.pre*100:null;
    const a=ly(r.l);r.y=gr(r.ni,a&&a.ni);const p=R[i-1];r.q=p&&qNext(p.l)===r.l?gr(r.ni,p.ni):{};
    if(i>=3){const w=R.slice(i-3,i+1);if(w.every((x,j)=>!j||qNext(w[j-1].l)===x.l)){r.t4=sum(w.map(x=>x.ni));
      const s4=w.filter(x=>x.pre!=null&&x.nn!=null);if(s4.length===4){const P=sum(s4.map(x=>x.pre));r.sh4=P>0?sum(s4.map(x=>x.nn))/P*100:null}}}});
  R.forEach(r=>{const a=ly(r.l);r.y4=gr(r.t4,a&&a.t4)});
  return R;
}
function npGr(g,d=0){if(!g||(g.v==null&&!g.t))return '—';if(g.t)return `<b class="${g.t==='轉盈'?'up':g.t==='轉虧'?'dn':''}">${g.t}</b>`;
  return `<b class="${g.v>0?'up':g.v<0?'dn':''}">${g.v>300?'>+300%':pct(g.v,d)}</b>`}
function renderNp(){
  const R=npRows(),has=R.length>=4;$('np').hidden=!has;$('chipNp').hidden=!has;if(!has)return;
  const S=R.slice(-12),r=R[R.length-1],fin=S.every(x=>x.op==null||x.pre==null),M=fin?'n':NPM;
  const up=css('--up'),dn=css('--down'),mu=css('--muted'),acc=css('--accent'),warm=css('--warm'),fg=css('--fg');
  const f=v=>v==null?'—':fmt(v,Math.abs(v)<10?2:Math.abs(v)<100?1:0);
  $('npSeg').hidden=fin;$('npSeg').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.m===M));
  const o=base(),ch=mk('cNp');o.xAxis.data=S.map(x=>x.l+(x.fl?'*':''));o.yAxis.scale=false;
  const lab=n=>({show:true,position:'top',fontSize:9,color:mu,fontFamily:'IBM Plex Mono',formatter:p=>p.dataIndex>=S.length-n&&p.value!=null?(Math.abs(p.value)>=1000?String(Math.round(p.value)):f(p.value)):''}); // ≥1000 不加逗號，手機上 4 根柱的數字才放得下
  const colOf=x=>x.y.t==='轉盈'||x.y.v>0?up:x.y.t==='轉虧'||x.y.v<0?dn:mu;
  if(M==='n'){
    // 柱子壓在下方約 6 成、年增率線放上方，避免數字互相蓋住
    const bmax=Math.max(...S.map(x=>x.ni||0)),bmin=Math.min(0,...S.map(x=>x.ni||0)),ys=S.map(x=>x.y.v==null||x.y.v>300?null:x.y.v).filter(v=>v!=null);
    const lo=ys.length?Math.min(...ys):0,hi=ys.length?Math.max(...ys):10,sp=Math.max(hi-lo,10);
    const span=Math.max(bmax*1.65,0)-Math.min(bmin*1.2,0),st=(r=>{const e=Math.pow(10,Math.floor(Math.log10(r)));return [1,2,2.5,5,10].map(k=>k*e).find(k=>k>=r)})(span/5||1),nice=v=>v?Math.sign(v)*Math.ceil(Math.abs(v)/st)*st:0;o.yAxis.interval=st; // 軸上限取整數刻度，避免 containLabel 預留長小數標籤而把圖擠到右邊
    o.yAxis.max=bmax>0?nice(bmax*1.65):null;o.yAxis.min=bmin<0?-nice(-bmin*1.2):0;
    // 隱藏的右軸在 containLabel 下仍會被預留寬度 → 改用左軸最長標籤估算邊界
    {let w=1;for(let v=o.yAxis.min;v<=(o.yAxis.max||0)+st/2;v+=st)w=Math.max(w,(+v.toFixed(6)).toLocaleString('zh-TW').length);o.grid={...o.grid,containLabel:false,left:Math.round(w*6.2+12),right:8,bottom:24}}
    o.yAxis=[o.yAxis,{type:'value',show:false,scale:false,min:Math.floor(lo-sp*1.75),max:Math.ceil(hi+sp*.25)}];
    o.series=[{name:'母公司淨利',type:'bar',barCategoryGap:'28%',itemStyle:{color:up,borderRadius:[2,2,0,0]},label:lab(4),
        data:S.map(x=>({value:x.ni,itemStyle:{color:colOf(x),opacity:x.fl?.45:1,borderColor:colOf(x),borderWidth:x.fl?1.5:0,borderType:'dashed'}}))},
      {name:'年增率',type:'line',yAxisIndex:1,data:S.map((x,i)=>({value:x.y.v==null||x.y.v>300?null:+x.y.v.toFixed(1),label:{position:(S.length-1-i)%2?'bottom':'top'}})),symbol:'circle',symbolSize:4,lineStyle:{width:2,color:warm},itemStyle:{color:warm},labelLayout:{hideOverlap:true},
        label:{show:true,position:'top',fontSize:9,color:warm,fontFamily:'IBM Plex Mono',formatter:p=>p.dataIndex>=S.length-4&&p.value!=null?(p.value>0?'+':'')+Math.round(p.value)+'%':''}}];
  }else{
    o.series=[{name:'本業',type:'bar',stack:'p',barCategoryGap:'28%',data:S.map(x=>({value:x.op,itemStyle:{opacity:x.fl?.5:1}})),itemStyle:{color:acc}},
      {name:'業外',type:'bar',stack:'p',itemStyle:{color:warm},
        data:S.map((x,i)=>({value:x.nn,itemStyle:{opacity:x.fl?.5:1},label:{show:i>=S.length-8&&x.sh!=null,position:x.nn<0?'bottom':'top',fontSize:9,fontFamily:'IBM Plex Mono',
          color:x.sh>=40||x.op<=0?up:x.sh>=20||x.sh<=-20?warm:mu,formatter:()=>x.sh>100?'>100%':x.sh<-100?'<-100%':Math.round(x.sh)+'%'}}))},
      {name:'母公司淨利',type:'line',data:S.map(x=>x.ni),symbol:'circle',symbolSize:4,z:5,lineStyle:{width:1.5,color:fg},itemStyle:{color:fg}}];
    o.grid.top=36;
  }
  o.tooltip.formatter=ps=>{const x=S[ps[0].dataIndex];
    return `<b>${x.l}</b>${x.fl?`（${x.fl} 快訊${x.est?'，EPS×股數推算':''}）`:''}<br>母公司淨利 <b>${f(x.ni)}</b> 億<br>年增 ${npGr(x.y)}・季增 ${npGr(x.q)}`+
      (x.nn!=null?`<br>本業 ${f(x.op)} ＋ 業外 ${f(x.nn)} ＝ 稅前 ${f(x.pre)} 億`+(x.sh!=null?`<br>業外占稅前 ${fmt(x.sh,0)}%`:''):'')+
      (x.t4!=null?`<br>近四季淨利 ${f(x.t4)} 億（年增 ${npGr(x.y4)}）`:'')};
  ch.setOption(o,true);ch.resize();
  // 結論：看最新一季業外占稅前淨利
  let V;const r0=r,rb=[...R].reverse().find(x=>x.op!=null&&x.pre!=null);
  {const r=rb||r0,ql=rb&&rb!==r0?`（${rb.l}）`:'';
  if(fin)V=['','金融業','財報沒有營業利益，不拆本業／業外'];
  else if(r.pre==null||r.op==null)V=['','⚪ 無拆解','這一季沒有營業利益或稅前淨利資料'];
  else if(r.pre<=0)V=['bad','🔴 稅前虧損',`本業 ${f(r.op)} 億、業外 ${f(r.nn)} 億`];
  else if(r.op<=0)V=['bad','🔴 本業虧損',`稅前賺的 ${f(r.pre)} 億全靠業外，本業其實在虧`];
  else if(r.sh>=40)V=['bad','🔴 靠業外撐',`業外占稅前淨利 ${fmt(r.sh,0)}%，獲利不能當成本業實力`];
  else if(r.sh>=20)V=['mid','🟠 業外偏高',`業外占稅前淨利 ${fmt(r.sh,0)}%，看是匯兌、投資收益還是一次性處分`];
  else if(r.sh<=-20)V=['mid','🟠 業外拖累',`業外虧 ${f(-r.nn)} 億，本業其實比淨利看起來好`];
  else V=['ok','🟢 本業為主',`業外占稅前淨利 ${fmt(r.sh,0)}%，淨利主要來自本業`];
  V[1]+=ql;}
  const qe=(Q.find(x=>x[0]===r.l)||[])[5],qa=(Q.find(x=>x[0]===String(+r.l.slice(0,2)-1).padStart(2,'0')+r.l.slice(2))||[])[5];
  const ey=qe!=null&&qa>0?(qe/qa-1)*100:null,gap=ey!=null&&r.y.v!=null&&r.y.v<=300?ey-r.y.v:null;
  $('tNp').innerHTML=`<span class="pill ${V[0]}">${V[1]}</span> ${V[2]}`+((rb||r).sh4!=null&&!fin?`（近四季 ${fmt((rb||r).sh4,0)}%）`:'')+
    `<br>${r.l} 母公司淨利 <strong>${f(r.ni)} 億</strong>，年增 ${npGr(r.y)}・季增 ${npGr(r.q)}`+
    (r.t4!=null?`；近四季 <strong>${f(r.t4)} 億</strong>（年增 ${npGr(r.y4)}）`:'')+
    (r.fl?`<br><span class="pill">快訊</span> ${r.l} 取自 ${r.fl} 重大訊息`+(r.est?`（只公布 EPS ${fmt(r.eps,2)} 元 → 淨利以 EPS × 股數<b>推算</b>，沒有本業／業外）`:`（董事會通過財報${r.eps!=null?`，EPS ${fmt(r.eps,2)} 元`:''}）`)+'，財報資料庫還沒進來；虛線柱、標 *':'')+
    (gap!=null&&Math.abs(gap)>=5?`<br><span class="pill">股本</span> EPS 年增 ${pct(ey,0)}、淨利年增 ${pct(r.y.v,0)}，差 ${fmt(Math.abs(gap),0)} 點：${gap<0?'股數變多（增資、轉換債）稀釋了 EPS':'股數變少（減資、庫藏股）墊高了 EPS'}`:'')+
    (D.cyclical&&!fin?'<br><span class="pill">循環股</span> 景氣高峰時淨利年增最好看，要搭配淨值比河流圖看位置':'');
  $('fNp').textContent=(M==='n'?'柱：單季歸屬母公司淨利（紅＝年增、綠＝年減、灰＝無比較）；線：淨利年增率（>300% 不畫）。':'藍＝本業（營業利益）、橘＝業外（稅前淨利 − 營業利益，負的畫在 0 軸下），柱頂％＝業外占稅前淨利（≥20% 橘、≥40% 紅）；線：歸屬母公司淨利（已扣所得稅與非控制權益，所以會比柱子低）。')+
    ' 業外常見來源：匯兌損益、轉投資收益、處分資產；一次性項目要看財報附註。淨利與 EPS 不同之處：EPS 會被股本變動稀釋或墊高。';
}
$('npSeg').addEventListener('click',e=>{const b=e.target.closest('button[data-m]');if(!b||!D)return;NPM=b.dataset.m;try{localStorage.setItem('npM',NPM)}catch(_){}renderNp()});
'''
rep("// 與 fetch.py 的 build_cf() 相同邏輯", JS + "// 與 fetch.py 的 build_cf() 相同邏輯")

open(dst, "w", encoding="utf-8").write(h)
print("ok", dst, len(h))
