#!/usr/bin/env python3
"""10年財報加「🧾 損益」頁籤：每期一根 100% 堆疊柱＝每 100 元營收花去哪
（營業成本／營業費用〔抓得到就拆 推銷・管理・研發〕／營業利益），
柱子上方獨立一格畫兩條線：業外÷營收、有效稅率；頁尾寫營益率變化來自毛利率還是費用率、業外占稅前比重、稅率。
用法：python3 patch_is.py index.html beta.html
"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
n0 = len(s)

def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (s.count(old), old[:80])
    s = s.replace(old, new)

# 1. 頁籤按鈕（放在「💹 三率」右邊）
rep('<button type="button" data-t="p">💹 三率</button>',
    '<button type="button" data-t="p">💹 三率</button><button type="button" data-t="i">🧾 損益</button>')

# 2. buildY10：損益表多抓 營業成本、營業費用（推銷／管理／研發）、業外、所得稅、合併稅後淨利
rep("""  const CAP=b(['OrdinaryShare','CapitalStock'],/^普通股股本$/),TA=""",
"""  // 損益頁籤：營業成本、營業費用（合計＋推銷／管理／研發，FinMind 沒給細項時只有合計）、營業外收支、所得稅、合併稅後淨利
  const COGS=g(['CostOfGoodsSold','OperatingCosts'],/^營業成本(合計)?$/),OPEX=g(['OperatingExpenses'],/^營業費用(合計)?$/),
    SX=g(['SellingExpenses','SellingExpense'],/^推銷費用(合計)?$/),AX=g(['AdministrativeExpenses','AdministrativeExpense'],/^管理費用(合計)?$/),
    RDX=g(['ResearchAndDevelopmentExpenses','ResearchAndDevelopmentExpense'],/^研究發展費用(合計)?$/),
    NOP=g(['TotalNonoperatingIncomeAndExpense','NonoperatingIncomeAndExpense'],/^營業外收入及支出(合計)?$/),
    TAX=g(['TAX','IncomeTaxExpense','IncomeTax'],/^所得稅(費用|利益)/),NIT=g(['IncomeAfterTaxes','NetIncome'],/^本期(稅後)?淨利/);
  if(location.search.includes('dbg'))window.__y10dbgI=[...new Set(fs.map(r=>r.type+'｜'+r.origin_name))];
  const CAP=b(['OrdinaryShare','CapitalStock'],/^普通股股本$/),TA=""")

# 3. 單季資料加欄位
rep("""      ar:e8(AR[d]),inv:e8(INV[d]),ppe:e8(PPE[d]),ca:e8(CA[d]),cl:e8(CL[d]),prep:e8(PREP[d])})});""",
"""      ar:e8(AR[d]),inv:e8(INV[d]),ppe:e8(PPE[d]),ca:e8(CA[d]),cl:e8(CL[d]),prep:e8(PREP[d]),
      cogs:COGS[d]==null?null:e8(Math.abs(COGS[d])),opex:OPEX[d]==null?null:e8(Math.abs(OPEX[d])),sx:SX[d]==null?null:e8(Math.abs(SX[d])),ax:AX[d]==null?null:e8(Math.abs(AX[d])),
      rdx:RDX[d]==null?null:e8(Math.abs(RDX[d])),nop:e8(NOP[d]),tax:e8(TAX[d]),nit:e8(NIT[d])})});""")

# 4. isx()：成本率／費用率／業外率／有效稅率，年列與季列都展開
rep("""  const row=(l,qs,y,ttm)=>{""",
"""  // 損益：cogs 成本＝沒科目就用 營收−毛利；opex 費用＝沒科目就用 毛利−營業利益；nop 業外＝沒科目就用 稅前−營業利益；tax 所得稅＝沒科目就用 稅前−合併稅後淨利
  // cgr 成本率、oxr 費用率、sxr／axr／rdr 推銷／管理／研發費用率、nopr 業外÷營收（都是 %營收）；etr 有效稅率＝所得稅÷稅前（稅前為正才算）；nopp 業外占稅前(%)
  const isx=o=>{const rev=o.rev;if(!(rev>0))return {};
    const cogs=o.cogs!=null?o.cogs:o.gp!=null?rev-o.gp:null,opex=o.opex!=null?o.opex:o.gp!=null&&o.op!=null?o.gp-o.op:null,
      nop=o.nop!=null?o.nop:o.pre!=null&&o.op!=null?o.pre-o.op:null,tax=o.tax!=null?o.tax:o.pre!=null&&o.nit!=null?o.pre-o.nit:null,p=v=>v==null?null:v/rev*100;
    return {cogs,opex,sx:o.sx,ax:o.ax,rdx:o.rdx,nop,tax,pre:o.pre,cgr:p(cogs),oxr:p(opex),sxr:p(o.sx),axr:p(o.ax),rdr:p(o.rdx),nopr:p(nop),
      etr:o.pre>0&&tax!=null?tax/o.pre*100:null,nopp:o.pre>0&&nop!=null?nop/o.pre*100:null}};
  const row=(l,qs,y,ttm)=>{""")
rep("""      ...dbt(z,ni),...bsx(z),
""", """      ...dbt(z,ni),...bsx(z),...isx({rev,gp,op,pre,cogs:S(qs,'cogs'),opex:S(qs,'opex'),sx:S(qs,'sx'),ax:S(qs,'ax'),rdx:S(qs,'rdx'),nop:S(qs,'nop'),tax:S(qs,'tax'),nit:S(qs,'nit')}),
""")
rep("""...dbt(x,ni4),...bsx(x),at:""", """...dbt(x,ni4),...bsx(x),...isx(x),at:""")

# 5. 快取鍵升版
rep("const k='y10v8_'+id,c=store.get(k);", "const k='y10v9_'+id,c=store.get(k);")
rep("x.startsWith('y10v7_')||x.startsWith('y10v8_')).forEach", "x.startsWith('y10v7_')||x.startsWith('y10v8_')||x.startsWith('y10v9_')).forEach")

# 6. 季模式只畫近 20 季（柱內要放數字）
rep("""  if(Y10T==='b'&&Q)R=R.slice(-12);""",
"""  if(Y10T==='i'&&Q)R=R.slice(-20);   // 損益柱內要標數字，季模式只畫近 20 季
  if(Y10T==='b'&&Q)R=R.slice(-12);""")

# 7. 頁籤 'i' 的圖
rep("""  }else if(Y10T==='b'){
    o.yAxis.scale=false;o.grid={...o.grid,right:40,top:46};""",
"""  }else if(Y10T==='i'){
    o.yAxis.scale=false;o.grid={...o.grid,right:66,top:46};o.legend={...o.legend,itemGap:7,itemWidth:9,textStyle:{...o.legend.textStyle,fontSize:10}};
    const hasIS=R.some(x=>x.cgr!=null&&x.om!=null),split=hasIS&&R.some(x=>x.sxr!=null)&&R.every(x=>x.oxr==null||x.sxr!=null);
    const dark=/^#?[0-3]/.test(css('--bg').replace('#','')),cRd=dark?'#b59cff':'#7a5bd0',CAPB=180;
    // 每期一根柱＝每 100 元營收：成本＋費用＋營業利益（虧損時營業利益往下畫）；費用拆得出來就分 推銷／管理等（＝費用合計−推銷−研發）／研發
    const P=R.map(x=>{if(x.cgr==null)return {};const rd=x.rdr||0,ad=split?Math.max(0,(x.oxr||0)-(x.sxr||0)-rd):null;return {cgr:x.cgr,oxr:x.oxr,sxr:x.sxr,adr:ad,rdr:x.rdr,om:x.om}});
    const KS=split?['cgr','sxr','adr','rdr','om']:['cgr','oxr','om'];
    const V=P.map(p=>{let c=0;const o2={};KS.forEach(k=>{let v=p[k];if(v==null){o2[k]=null;return}if(k==='om'&&v<0){o2[k]=Math.max(v,-60);return}v=Math.max(0,Math.min(v,CAPB-c));c+=v;o2[k]=v});return o2});
    const tops=V.map(p=>KS.reduce((a,k)=>a+Math.max(p[k]||0,0),0)),mxp=Math.max(100,...tops),lminI=Math.floor(Math.min(0,...V.map(p=>p.om||0))/25)*25,lmaxI=lminI+(mxp-lminI)/.64;
    // 上下分格（同一個座標區，跟資產負債頁同一套）：柱子壓在下面 64%，兩條線用右軸換算後固定落在最上面一條（80%～96% 高度）
    o.yAxis={...o.yAxis,min:lminI,max:lmaxI,interval:25,axisLabel:{...o.yAxis.axisLabel,formatter:v=>v<=100&&v%50===0?v+'%':''},splitLine:{...o.yAxis.splitLine,show:false}};
    const cl2=(v,lo,hi)=>v==null?null:Math.max(lo,Math.min(hi,v)),LN=R.map(x=>({nopr:cl2(x.nopr,-50,50),etr:cl2(x.etr,0,60)}));
    const rv=LN.flatMap(x=>[x.nopr,x.etr]).filter(v=>v!=null),rhi0=rv.length?Math.max(...rv):20,rlo0=rv.length?Math.min(...rv):0,rpad=Math.max(rhi0-rlo0,5),rmid=(rhi0+rlo0)/2,
      rlo=rhi0-rlo0<rpad?rmid-rpad/2:rlo0,rhi=rhi0-rlo0<rpad?rmid+rpad/2:rhi0,rS=(rhi-rlo)/.16,rmin=rlo-.8*rS;
    o.yAxis=[o.yAxis,{...o.yAxis,min:rmin,max:rmin+rS,interval:undefined,splitLine:{show:false},axisLabel:{show:false}}];
    const sb=(name,k,col,op,lc)=>{const b0=bar(name,k,col,big);b0.stack='i';b0.barCategoryGap=Q?'16%':'24%';
      b0.data=b0.data.map((d,i)=>({...d,value:V[i][k],itemStyle:{...d.itemStyle,borderRadius:0,opacity:(d.itemStyle.opacity||1)*(op||1)}}));b0.itemStyle={color:col,opacity:op||1};
      b0.label={show:true,position:'inside',fontSize:9,opacity:1,color:lc||'#fff',fontFamily:'IBM Plex Mono',formatter:p=>{const v=P[p.dataIndex][k];return show(p.dataIndex)&&v!=null&&Math.abs(p.value)>=12?String(Math.round(v)):''}};return b0};
    const pl=(n,k,col,dash,sgn)=>{const l0=line(n,k,col,1,dash);l0.data=LN.map(x=>x[k]);l0.lineStyle.width=1.5;l0.endLabel.formatter=p=>p.value==null?'':(sgn?'業外 ':'稅率 ')+(sgn&&p.value>0?'+':'')+fmt(p.value,sgn?1:0)+'%';return l0};
    if(hasIS){
      const B=split?[sb('成本','cgr',mu,.45,fg),sb('推銷','sxr',warm),sb('管理','adr',warm,.5,fg),sb('研發','rdr',cRd),sb('營業利益','om',acc2)]:[sb('成本','cgr',mu,.45,fg),sb('營業費用','oxr',warm),sb('營業利益','om',acc2)];
      B[0].markLine={silent:true,symbol:'none',label:{show:false},lineStyle:{color:mu,type:'dotted',opacity:.6},data:[{yAxis:lminI+(lmaxI-lminI)*.755},...(lminI<0?[{yAxis:0,lineStyle:{color:mu,type:'solid',opacity:.8}}]:[])]};
      o.series=[...B,pl('業外÷營收','nopr',fg,false,true),pl('稅率','etr',fg,true)];
    }else{o.yAxis[0]={...o.yAxis[0],min:undefined,max:undefined,interval:undefined,scale:true,axisLabel:{...o.yAxis[0].axisLabel,formatter:'{value}%'},splitLine:{...o.yAxis[0].splitLine,show:true}};
      o.yAxis[1]={...o.yAxis[1],min:undefined,max:undefined,scale:true};o.series=[line('淨利率','nm',warm),pl('稅率','etr',fg,true)]}
    const ok=R.filter(x=>x.cgr!=null&&x.oxr!=null&&x.om!=null),ld=ok[ok.length-1],p0=ok[0],fin=/金融|保險|證券|銀行/.test(indOfStock());
    let v='';
    if(!hasIS)v=fin?'金融業的損益表是「淨收益−呆帳−營業費用」，沒有營業成本與毛利，這一頁只畫淨利率與稅率。':'財報沒有營業成本／營業利益科目，這一頁只畫淨利率與稅率。';
    else if(ld){const lbl=ld.ttm?'近四季':ld.l,sg1=d=>(d>=0?'+':'−')+fmt(Math.abs(d),1);
      v=`${lbl}每 100 元營收：成本 ${fmt(ld.cgr,0)}、費用 ${fmt(ld.oxr,0)}`+(split&&ld.sxr!=null?`（推銷 ${fmt(ld.sxr,1)}・管理等 ${fmt(Math.max(0,ld.oxr-ld.sxr-(ld.rdr||0)),1)}・研發 ${fmt(ld.rdr||0,1)}）`:'')+`、營業利益 ${fmt(ld.om,0)}`+
        (ld.pre!=null?`；業外 ${ld.nop==null?'—':(ld.nop>=0?'+':'−')+big(Math.abs(ld.nop))} 億、稅前 ${big(ld.pre)} 億`:'')+(ld.tax!=null?`、所得稅 ${big(ld.tax)} 億`+(ld.etr!=null?`（稅率 ${fmt(ld.etr,0)}%）`:''):'')+`、母公司淨利 ${ld.ni==null?'—':big(ld.ni)} 億。`;
      if(p0&&p0!==ld){const dO=ld.om-p0.om,dG=ld.gm-p0.gm,dX=ld.oxr-p0.oxr,l0=p0.ttm?'近四季':p0.l;
        if(Math.abs(dO)>=2)v+=`營益率 ${l0} ${fmt(p0.om,1)}% → ${fmt(ld.om,1)}%（${sg1(dO)} 點）：毛利率 ${sg1(dG)} 點、費用率 ${sg1(dX)} 點；`+
          (dO>0?(dG>=-dX?'主要靠毛利率，代表定價力或產品組合變好，品質最好。':'主要靠費用率下降，是營收長得比費用快的規模效益，營收一掉頭費用率會彈回來。')
               :(dG<=-dX?'主要是毛利率掉，成本漲或被砍價，比費用增加難救。':'主要是費用率升高，要看是研發／擴編的投資期還是營收掉了費用降不下來。'));
        else v+=`營益率 ${l0} ${fmt(p0.om,1)}% → ${fmt(ld.om,1)}%，結構穩定。`}
      if(ld.nopp!=null&&Math.abs(ld.nopp)>=30)v+=`⚠️ 稅前淨利有 ${fmt(ld.nopp,0)}% ${ld.nopp>0?'來自業外（匯兌、轉投資、處分資產），不一定每年都有，估值時別直接用這個 EPS 外推':'被業外損失吃掉'}，對照淨利卡的本業／業外拆解。`;
      else if(ld.pre!=null&&ld.pre<=0&&ld.nop!=null&&ld.op!=null)v+=ld.op>0?'⚠️ 本業賺錢但被業外損失吃成稅前虧損。':'本業虧損。';
      if(ld.etr!=null&&ld.etr<10)v+=`稅率只有 ${fmt(ld.etr,0)}%（虧損扣抵、免稅所得或租稅優惠），用完後淨利會被稅多吃一截。`;
      else if(ld.etr!=null&&ld.etr>30)v+=`稅率 ${fmt(ld.etr,0)}% 偏高（海外稅負、未分配盈餘稅或一次性補稅）。`;
      if(split&&ld.rdr!=null&&ld.rdr>=10)v+=`研發費用率 ${fmt(ld.rdr,0)}%，屬研發驅動型公司，費用率高不等於浪費，重點看毛利率撐不撐得住。`}
    foot=(hasIS?`每期一根柱＝每 100 元營收花去哪：灰 成本、${split?'橘 推銷、淡橘 管理（含其他費用）、紫 研發':'橘 營業費用（推銷＋管理＋研發；資料源只給合計）'}、青綠 營業利益（＝營益率，虧損時往下畫）；灰＋橘越矮、青綠越高越好。線（畫在柱子上方獨立一格，只看走勢與尾端數字）：業外÷營收（實線，正＝業外賺）、稅率＝所得稅 ÷ 稅前淨利（虛線，稅前虧損不畫）。`:'')+(Q&&hasIS?'季模式只畫近 20 季。':'')+v+
      (window.__y10dbgI?' 【偵錯】損益表科目：'+(window.__y10dbgI.join('；')||'無'):'');
  }else if(Y10T==='b'){
    o.yAxis.scale=false;o.grid={...o.grid,right:40,top:46};""")

# 8. 展開區加一行；薄條第一行
rep("""if(x.ib!=null)L.push(`有息負債 ${f(x.ib,0)}・無息""",
"""if(x.cgr!=null)L.push(`成本 ${f(x.cogs,0)}・費用 ${f(x.opex,0)}`+(x.sx!=null?`（推銷 ${f(x.sx,0)}・研發 ${f(x.rdx,0)}）`:'')+`・業外 ${f(x.nop,0)}・所得稅 ${f(x.tax,0)}・淨利 ${f(x.ni,0)} 億`+(x.etr!=null?`｜稅率 ${fmt(x.etr,0)}%`:''));if(x.ib!=null)L.push(`有息負債 ${f(x.ib,0)}・無息""")
rep("""    else if(T==='e')m=`EPS ${f(x.eps,2)}・年增""",
"""    else if(T==='i')m=x.cgr==null?`淨利率 ${f(x.nm,1)}%`+(x.etr!=null?`・稅率 ${fmt(x.etr,0)}%`:''):`費用 ${x.oxr==null?'—':fmt(x.oxr,0)+'%'}・<b>營益 ${f(x.om,1)}%</b>・業外 ${x.nop==null?'—':f(x.nop,0)} 億`;
    else if(T==='e')m=`EPS ${f(x.eps,2)}・年增""")

# 9. 端點標籤避讓：業外率、稅率兩條線
rep("""l:[2,3],b:[8,9],d:[1,2],u:[0,1,2,3]}[Y10T];""", """l:[2,3],b:[8,9],d:[1,2],u:[0,1,2,3],i:o.series.map((x,i)=>x.type==='line'?i:-1).filter(i=>i>=0)}[Y10T];""")

# 10. 明細表加「費用率」「業外億」「稅率」欄（接在淨利率後面）
rep("""<th>淨利率</th><th>EPS</th>""", """<th>淨利率</th><th>費用率</th><th>業外億</th><th>稅率</th><th>EPS</th>""")
rep("""<td>${c(x.nm,1)}</td><td>${c(x.eps,2)}</td>""",
    """<td>${c(x.nm,1)}</td><td>${c(x.oxr,1)}</td><td>${c(x.nop,0)}</td><td>${x.etr==null?'—':c(x.etr,0)+'%'}</td><td>${c(x.eps,2)}</td>""")

# 11. 版本標
rep("""(Y10T==='l'?' v1109e':Y10T==='b'?' v1110d':'')""", """(Y10T==='l'?' v1109e':Y10T==='b'?' v1110d':Y10T==='i'?' v1110j':'')""")

open(dst, 'w', encoding='utf-8').write(s)
print('ok', n0, '->', len(s))
