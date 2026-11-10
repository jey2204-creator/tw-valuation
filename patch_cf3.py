#!/usr/bin/env python3
"""10年財報「💵 現金流」頁籤升級成三大現金流：每期一根上下堆疊柱
（零線以上＝流入、以下＝流出；藍 營業／橘 投資／紫 籌資），柱區內一條自由現金流線，
柱子上方獨立一格畫期末現金線；頁尾判讀現金流型態、股利＋買回 vs 自由現金流、籌資來源。
用法：python3 patch_cf3.py index.html beta.html
"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
n0 = len(s)

def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (s.count(old), old[:80])
    s = s.replace(old, new)

# 1. buildY10：現金流量表多抓 投資／籌資活動淨現金流、發放現金股利、買回庫藏股、現金增資
rep("""  const eqAt=d=>EQP[d]!=null?EQP[d]:EQ[d]!=null?EQ[d]:null,tlAt=""",
"""  // 現金流頁籤：投資／籌資活動淨現金流（保留正負號）＋發放現金股利、買回庫藏股、現金增資（取絕對值）。現金流量表是年初累計，拆成單季；
  // 股利這類第一季常常沒有的科目，用營業現金流有資料的日期補 0 再拆，不然整年會算不出來
  const OCFR=serT(cf,['CashFlowsFromOperatingActivities','NetCashInflowFromOperatingActivities']),
    CFCUM=(()=>{const ys={};Object.entries(OCFR).forEach(([k,v])=>{if(Y10QD.includes(k.slice(5)))(ys[+k.slice(0,4)]=ys[+k.slice(0,4)]||{})[+k.slice(5,7)/3]=v});
      const ra=Object.values(ys).filter(y=>y[1]&&y[4]!=null).map(y=>Math.abs(y[4])/Math.abs(y[1])).sort((a,b)=>a-b);return !ra.length||ra[Math.floor(ra.length/2)]>2.5})(),
    cfQ=(d,fill)=>{const src={...d};if(fill&&Object.keys(src).length)Object.keys(OCFR).forEach(k=>{if(src[k]==null)src[k]=0});
      const ys={},out={};Object.entries(src).forEach(([k,v])=>{if(Y10QD.includes(k.slice(5)))(ys[+k.slice(0,4)]=ys[+k.slice(0,4)]||{})[+k.slice(5,7)/3]=v});
      Object.entries(ys).forEach(([y,qs])=>Object.entries(qs).forEach(([n,v])=>{n=+n;if(!CFCUM||n===1)out[`${y}-${n}`]=v;else if(qs[n-1]!=null)out[`${y}-${n}`]=v-qs[n-1]}));return out},
    cfAbs=re=>{const o={};cf.forEach(r=>{if(r.value==null)return;if(re.test((r.origin_name||'').trim()))o[r.date]=(o[r.date]||0)+Math.abs(r.value)});return o},
    cfNet=(types,re,re2)=>{let d=y10Ser(cf,types,re);if(!Object.keys(d).length)d=y10Ser(cf,[],re2);return d},
    ICF=cfQ(cfNet(['CashProvidedByInvestingActivities','NetCashInflowFromInvestingActivities','CashFlowsFromInvestingActivities','NetCashFlowsFromUsedInInvestingActivities','CashFlowsProvidedFromInvestingActivities'],/^投資活動之淨現金流(入|出)/,/投資活動.*淨現金/)),
    FNF=cfQ(cfNet(['CashFlowsProvidedFromFinancingActivities','CashProvidedByFinancingActivities','NetCashInflowFromFinancingActivities','CashFlowsFromFinancingActivities','NetCashFlowsFromUsedInFinancingActivities'],/^籌資活動之淨現金流(入|出)/,/(籌資|融資)活動.*淨現金/)),
    DIVP=cfQ(cfAbs(/^(發放現金股利|支付(之)?(現金)?股利)/),true),BUYB=cfQ(cfAbs(/^(庫藏股票?(買回|收買)(成本)?|買回庫藏股票?)/),true),CAPI=cfQ(cfAbs(/^現金增資/),true);
  if(location.search.includes('dbg'))window.__y10dbgC=[...new Set(cf.map(r=>r.type+'｜'+r.origin_name))];
  const eqAt=d=>EQP[d]!=null?EQP[d]:EQ[d]!=null?EQ[d]:null,tlAt=""")

# 2. 單季資料加欄位
rep("""rdx:RDX[d]==null?null:e8(Math.abs(RDX[d])),nop:e8(NOP[d]),tax:e8(TAX[d]),nit:e8(NIT[d])})});""",
"""rdx:RDX[d]==null?null:e8(Math.abs(RDX[d])),nop:e8(NOP[d]),tax:e8(TAX[d]),nit:e8(NIT[d]),
      icf:e8(ICF[`${y}-${n}`]),fnf:e8(FNF[`${y}-${n}`]),divp:e8(DIVP[`${y}-${n}`]),buyb:e8(BUYB[`${y}-${n}`]),capi:e8(CAPI[`${y}-${n}`])})});""")

# 3. 年列／季列：icf 投資、fnf 籌資、divp 發放股利、buyb 買回庫藏股、capi 現金增資、dib 有息負債增減（年列＝跟一年前同季比，季列＝跟上一季比）
rep("""    return {l,y,ttm,rev,gm:P(gp,rev),om:P(op,rev),nm:P(ni,rev),ni,eps,ocf,fcf:ocf!=null&&cx!=null?ocf-cx:null,cx,""",
"""    return {l,y,ttm,rev,gm:P(gp,rev),om:P(op,rev),nm:P(ni,rev),ni,eps,ocf,fcf:ocf!=null&&cx!=null?ocf-cx:null,cx,
      icf:S(qs,'icf'),fnf:S(qs,'fnf'),divp:S(qs,'divp'),buyb:S(qs,'buyb'),capi:S(qs,'capi'),dib:z.ib!=null&&pz&&pz.ib!=null?z.ib-pz.ib:null,""")
rep("""ocf:x.ocf,fcf:x.ocf!=null&&x.cx!=null?x.ocf-x.cx:null,
      roe:ni4""", """ocf:x.ocf,fcf:x.ocf!=null&&x.cx!=null?x.ocf-x.cx:null,cx:x.cx,
      icf:x.icf,fnf:x.fnf,divp:x.divp,buyb:x.buyb,capi:x.capi,dib:i&&x.ib!=null&&Qa[i-1].ib!=null?x.ib-Qa[i-1].ib:null,
      roe:ni4""")

# 4. 快取鍵升版
rep("const k='y10v9_'+id,c=store.get(k);", "const k='y10v10_'+id,c=store.get(k);")
rep("x.startsWith('y10v8_')||x.startsWith('y10v9_')).forEach", "x.startsWith('y10v8_')||x.startsWith('y10v9_')||x.startsWith('y10v10_')).forEach")

# 5. 季模式只畫近 20 季
rep("""  if(Y10T==='i'&&Q)R=R.slice(-20);""", """  if((Y10T==='i'||Y10T==='c')&&Q)R=R.slice(-20);""")

# 6. 頁籤 'c' 的圖
rep("""  }else{
    o.series=[bar('營業現金流','ocf',acc,big),{...bar('自由現金流','fcf',acc2,big),label:{show:false}},{...line('母公司淨利','ni',fg),endLabel:{show:false}}];
    foot='自由現金流＝營業現金流 − 資本支出（取得不動產、廠房及設備）。長期淨利有、自由現金流卻常是負的＝賺的錢都要再投資或卡在應收／存貨。';
  }""",
"""  }else if(!R.some(x=>x.ocf!=null&&x.icf!=null&&x.fnf!=null)){
    o.series=[bar('營業現金流','ocf',acc,big),{...bar('自由現金流','fcf',acc2,big),label:{show:false}},{...line('母公司淨利','ni',fg),endLabel:{show:false}}];
    foot='自由現金流＝營業現金流 − 資本支出（取得不動產、廠房及設備）。長期淨利有、自由現金流卻常是負的＝賺的錢都要再投資或卡在應收／存貨。資料源沒有投資／籌資活動現金流科目，這一頁只畫營業與自由現金流。'+
      (window.__y10dbgC?' 【偵錯】現金流量表科目：'+(window.__y10dbgC.join('；')||'無'):'');
  }else{
    o.yAxis.scale=false;o.grid={...o.grid,right:72,top:46};o.legend={...o.legend,itemGap:7,itemWidth:9,textStyle:{...o.legend.textStyle,fontSize:10}};
    const dark=/^#?[0-3]/.test(css('--bg').replace('#','')),cFn=dark?'#b59cff':'#7a5bd0',K3=['ocf','icf','fnf'];
    // 每期一根上下堆疊柱：零線以上＝現金流入、以下＝流出；柱子壓在下面 64%，期末現金線用右軸換算後固定落在最上面一條（80%～96% 高度）
    const pos=R.map(x=>K3.reduce((a,k)=>a+Math.max(x[k]||0,0),0)),neg=R.map(x=>K3.reduce((a,k)=>a+Math.min(x[k]||0,0),0)),
      mxp=Math.max(1,...pos,...R.map(x=>x.fcf||0)),mnn=Math.min(0,...neg,...R.map(x=>x.fcf||0)),st=nice5((mxp-mnn)/4),hs=st/4,lminC=mnn<0?-Math.ceil(-mnn*1.03/hs)*hs:0,lmaxC=lminC+(mxp-lminC)/.64;   // 下限貼著最深的流出（以 1/4 格取整），刻度只標整格
    o.yAxis={...o.yAxis,min:lminC,max:lmaxC,interval:hs,axisLabel:{...o.yAxis.axisLabel,formatter:v=>v<=mxp*1.04&&Math.abs(v/st-Math.round(v/st))<1e-6?echarts.format.addCommas(Math.round(v*100)/100):''},splitLine:{...o.yAxis.splitLine,show:false}};
    const cv=R.map(x=>x.cash).filter(v=>v!=null),hasC=cv.length>1,rhi0=hasC?Math.max(...cv):1,rlo0=hasC?Math.min(...cv):0,rpad=Math.max(rhi0-rlo0,rhi0*.08,.1),rmid=(rhi0+rlo0)/2,
      rlo=rhi0-rlo0<rpad?rmid-rpad/2:rlo0,rhi=rhi0-rlo0<rpad?rmid+rpad/2:rhi0,rS=(rhi-rlo)/.16,rmin=rlo-.8*rS;
    o.yAxis=[o.yAxis,{...o.yAxis,min:rmin,max:rmin+rS,interval:undefined,splitLine:{show:false},axisLabel:{show:false}}];
    const big=v=>echarts.format.addCommas(Math.abs(v)>=100?Math.round(v):Math.round(v*10)/10);   // 這一頁的數字加千分位
    const sb=(name,k,col)=>{const b0=bar(name,k,col,big);b0.stack='c';b0.label={show:false};b0.barCategoryGap=Q?'18%':'26%';
      b0.data=b0.data.map(d=>({...d,itemStyle:{...d.itemStyle,borderRadius:0}}));b0.itemStyle={color:col};return b0};
    const B=[sb('營業','ocf',acc),sb('投資','icf',warm),sb('籌資','fnf',cFn)];
    B[0].markLine={silent:true,symbol:'none',label:{show:false},lineStyle:{color:mu,type:'dotted',opacity:.6},data:[{yAxis:lminC+(lmaxC-lminC)*.755},...(lminC<0?[{yAxis:0,lineStyle:{color:fg,type:'solid',opacity:.55,width:1}}]:[])]};
    const fl=line('自由現金流','fcf',fg,0);fl.lineStyle.width=1.5;fl.endLabel.formatter=p=>p.value==null?'':'自由 '+big(p.value);
    o.series=[...B,fl];
    if(hasC){const cl=line('期末現金','cash',fg,1,true);cl.lineStyle.width=1.5;cl.endLabel.formatter=p=>p.value==null?'':'現金 '+big(p.value);o.series.push(cl)}
    // 判讀：型態（三大活動正負號）、自由現金流、股利＋買回 vs 自由現金流、籌資來源
    const ok=R.filter(x=>x.ocf!=null&&x.icf!=null&&x.fnf!=null),ld=ok[ok.length-1],fin=/金融|保險|證券|銀行/.test(indOfStock()),sgn=v=>(v>=0?'+':'−')+big(Math.abs(v));
    const typ=x=>{const a=x.ocf>0,b=x.icf>0,c=x.fnf>0;
      return a&&!b&&!c?['g','🟢 成熟賺錢型（營業＋、投資−、籌資−）','本業賺的錢夠付擴產，還有剩拿去還債、發股利']
        :a&&!b&&c?['o','🟠 擴產型（營業＋、投資−、籌資＋）','本業賺錢但不夠花，差額靠借款或增資補，要看新產能能不能換到營收']
        :a&&b&&!c?['o','🟠 收成／縮編型（營業＋、投資＋、籌資−）','本業賺錢又在收回投資或賣資產，拿去還債或發股利，成長動能要另外確認']
        :a&&b&&c?['w','⚪ 囤現金型（三項都流入）','錢都往公司裡堆，通常是大投資或併購前的準備']
        :!a&&!b&&c?['r','🔴 燒錢型（營業−、投資−、籌資＋）','本業流出還在投資，全靠外部資金，籌不到錢就斷炊']
        :!a&&b?['r','🔴 賣資產撐本業型（營業−、投資＋）','本業在流出，靠處分資產或收回投資補洞']
        :['r','🔴 吃老本型（營業−、投資−、籌資−）','三項都流出，只能消耗手上現金']};
    let v='';
    if(ld){const lbl=ld.ttm?'近四季':ld.l,t=typ(ld),net=ld.ocf+ld.icf+ld.fnf;
      v=`${lbl}：營業 ${sgn(ld.ocf)}、投資 ${sgn(ld.icf)}、籌資 ${sgn(ld.fnf)} 億，三項合計 ${sgn(net)} 億`+(ld.cash!=null?`，期末現金 ${big(ld.cash)} 億`:'')+`。${t[1]}：${t[2]}。`;
      const fy=ok.filter(x=>!x.ttm);if(!Q&&fy.length>=3){const n=fy.filter(x=>typ(x)[0]==='g').length,r=fy.filter(x=>typ(x)[0]==='r').length;v+=`${fy.length} 個完整年度裡 ${n} 年是成熟賺錢型`+(r?`、${r} 年是紅燈型態`:'')+'。'}
      if(fin)v+='金融業的存放款都算營業活動，三大現金流的正負號沒有上面的意義，這一頁不適用。';
      else{
        const fk=ok.filter(x=>x.fcf!=null),nf=fk.filter(x=>x.fcf<0).length;
        if(ld.fcf!=null)v+=`自由現金流 ${sgn(ld.fcf)} 億`+(fk.length>=4?`（圖上 ${fk.length} 期有 ${nf} 期為負）`:'')+(ld.fcf<0?(ld.ocf>0?'，營業賺的被資本支出吃光，':'，')+'缺口要靠借款、增資或手上現金補。':'。');
        // 股利＋買回：現金流量表有「發放現金股利」就用實付數；沒有就用 每股股利 × 股數（淨利 ÷ EPS）估，只在年模式的完整年度估
        let pay=null,est=false;
        if(ld.divp!=null&&ld.divp>0)pay=ld.divp+(ld.buyb||0);
        else if(!Q&&!ld.ttm&&ld.div>0&&ld.eps>0&&ld.ni>0){pay=ld.div*ld.ni/ld.eps;est=true}
        if(pay!=null&&pay>0&&ld.fcf!=null){const br=ld.buyb>0?`（含買回庫藏股 ${big(ld.buyb)} 億）`:'';
          v+=`💰 ${est?'該年度盈餘配發的現金股利約':'實際發出股利'+(ld.buyb>0?'＋買回':'')} ${big(pay)} 億${est?'':br}`+
            (ld.fcf<=0?'，但自由現金流是負的 ⚠️ 等於借錢或拿老本發股利，撐不久。':pay>ld.fcf?`，是自由現金流的 ${fmt(pay/ld.fcf*100,0)}% ⚠️ 發的比賺到的自由現金多，差額來自借款或手上現金。`:`，占自由現金流 ${fmt(pay/ld.fcf*100,0)}%，付得起。`)}
        if(ld.capi>0)v+=`🏭 現金增資 ${big(ld.capi)} 億`+(ld.dib>0?`、有息負債增加 ${big(ld.dib)} 億`:'')+`；${ld.dib>ld.capi?'資金主要靠借款':'資金主要靠增資，股本變大會稀釋 EPS'}。`;
        else if(ld.dib!=null&&ld.ib>0&&Math.abs(ld.dib)>=Math.max(1,ld.ib*.1))v+=`🏭 有息負債${ld.ttm||Q?'':'這一年'}${ld.dib>0?'增加':'減少'} ${big(Math.abs(ld.dib))} 億`+(ld.dib>0?(ld.fnf>0?'，籌資流入主要是借來的；利息負擔看「🏦 ROE負債」的利息保障倍數。':'。'):'，在還債。')}}
    foot=`每期一根柱：零線以上＝現金流入、以下＝流出；藍 營業（本業收到的現金）、橘 投資（買設備／轉投資，通常為負）、紫 籌資（借款／增資為正，還債／發股利為負）。實線＝自由現金流（營業現金流 − 資本支出）；最上面一格的虛線＝期末現金（只看走勢與尾端數字）。${Q?'季模式只畫近 20 季，單季波動大，型態以年模式為準。':''}${v}`+
      (window.__y10dbgC?' 【偵錯】現金流量表科目：'+(window.__y10dbgC.join('；')||'無'):'');
  }""")

# 7. 展開區、薄條第一行
rep("""if(x.ocf!=null)L.push(`營業現金流 ${f(x.ocf)}・自由現金流 ${f(x.fcf)}・淨利 ${f(x.ni)} 億`);""",
"""if(x.ocf!=null)L.push(`營業現金流 ${f(x.ocf)}`+(x.icf!=null?`・投資 ${f(x.icf)}・籌資 ${f(x.fnf)}`:'')+`・自由現金流 ${f(x.fcf)}・淨利 ${f(x.ni)} 億`+(x.divp>0?`｜發放股利 ${f(x.divp)}`:'')+(x.buyb>0?`・買回 ${f(x.buyb)}`:'')+(x.capi>0?`・現金增資 ${f(x.capi)}`:''));""")
rep("""    else m=`營業現金流 ${f(x.ocf,0)}・自由現金流 ${f(x.fcf,0)}・淨利 ${f(x.ni,0)} 億`;""",
"""    else m=x.icf==null?`營業現金流 ${f(x.ocf,0)}・自由現金流 ${f(x.fcf,0)}・淨利 ${f(x.ni,0)} 億`:`營業 ${f(x.ocf,0)}・投資 ${f(x.icf,0)}・籌資 ${f(x.fnf,0)}・<b>自由 ${f(x.fcf,0)}</b> 億`;""")

# 8. 端點標籤避讓：自由現金流、期末現金兩條線
rep("""u:[0,1,2,3],i:o.series.map((x,i)=>x.type==='line'?i:-1).filter(i=>i>=0)}[Y10T];""",
    """u:[0,1,2,3],i:o.series.map((x,i)=>x.type==='line'?i:-1).filter(i=>i>=0),c:o.series.length>3?o.series.map((x,i)=>x.type==='line'?i:-1).filter(i=>i>=0):null}[Y10T];""")

# 9. 明細表加「營業現金」「投資現金」「籌資現金」欄（接在自由現金流前面）
rep("""<th>利息保障</th><th>自由現金流</th>""", """<th>利息保障</th><th>營業現金</th><th>投資現金</th><th>籌資現金</th><th>自由現金流</th>""")
rep("""<td>${c(x.fcf,0)}</td><td>${c(x.pe,1)}</td>""", """<td>${c(x.ocf,0)}</td><td>${c(x.icf,0)}</td><td>${c(x.fnf,0)}</td><td>${c(x.fcf,0)}</td><td>${c(x.pe,1)}</td>""")

# 10. 版本標
rep("""Y10T==='i'?' v1110j':'')""", """Y10T==='i'?' v1110j':Y10T==='c'?' v1110m':'')""")

open(dst, 'w', encoding='utf-8').write(s)
print('ok', n0, '->', len(s))
