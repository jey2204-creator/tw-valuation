#!/usr/bin/env python3
"""10年財報加「💳 負債」頁籤：總負債拆成有息（借款＋公司債＋租賃）／無息，疊成億元柱，
現金折線、有息負債比（右軸虛線）；頁尾寫淨負債／權益、幾年淨利可還清。
用法：python3 patch_debt.py index.html beta.html
"""
import sys, re
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
n0 = len(s)

def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (s.count(old), old[:80])
    s = s.replace(old, new)

# 1. 頁籤按鈕
rep('<button type="button" data-t="r">🏦 ROE負債</button>',
    '<button type="button" data-t="r">🏦 ROE負債</button><button type="button" data-t="l">💳 負債</button>')

# 2. buildY10：資產負債表抓有息負債各科目＋現金（以中文科目名正則加總，FinMind 英文 type 名不固定）
rep("""    EQP=b(['EquityAttributableToOwnersOfParent'],/^歸屬於母公司業主之權益(合計|總計)?$/),EQ=b(['Equity','TotalEquity'],/^權益總(計|額)$/);""",
"""    EQP=b(['EquityAttributableToOwnersOfParent'],/^歸屬於母公司業主之權益(合計|總計)?$/),EQ=b(['Equity','TotalEquity'],/^權益總(計|額)$/);
  // 有息負債：短期借款、應付短期票券、一年內到期長期負債／公司債、長期借款、應付公司債、租賃負債（流動＋非流動）；現金及約當現金
  const bsum=re=>{const o={};bs.forEach(r=>{if(r.value==null)return;const nm=(r.origin_name||'').trim();if(re.test(nm))o[r.date]=(o[r.date]||0)+r.value});return o};
  const IBRE=/^(短期借款|應付短期票券|一年或一營業週期內到期(之)?(長期負債|長期借款|應付公司債)|一年內到期(之)?(長期負債|長期借款|應付公司債)|長期借款|應付公司債|租賃負債)/,
    IB=bsum(IBRE),LEASE=bsum(/^租賃負債/),CASH=b(['CashAndCashEquivalents'],/^現金及約當現金$/);
  if(location.search.includes('dbg'))window.__y10dbgL=[...new Set(bs.filter(r=>IBRE.test((r.origin_name||'').trim())||/借款|公司債|票券|租賃/.test(r.origin_name||'')).map(r=>r.type+'｜'+r.origin_name))];""")

# 3. 單季資料加欄位
rep("""      eq:e8(eqAt(d)),ta:e8(TA[d]),tl:e8(tlAt(d)),pre:e8(PRE[d]),intx:INT[d]==null?null:e8(Math.abs(INT[d]))})});""",
"""      eq:e8(eqAt(d)),ta:e8(TA[d]),tl:e8(tlAt(d)),pre:e8(PRE[d]),intx:INT[d]==null?null:e8(Math.abs(INT[d])),
      ib:TA[d]!=null?e8(IB[d]||0):null,lease:e8(LEASE[d]||0),cash:e8(CASH[d])})});""")

# 4. 年度列：負債拆解（取年底那季）
rep("""      roe:ni!=null&&eqA>0?ni/eqA*100:null,debt:z.tl!=null&&z.ta?z.tl/z.ta*100:null,div:dd?dd.c:null,sdiv:dd?dd.s:null,""",
"""      roe:ni!=null&&eqA>0?ni/eqA*100:null,debt:z.tl!=null&&z.ta?z.tl/z.ta*100:null,div:dd?dd.c:null,sdiv:dd?dd.s:null,
      ...dbt(z,ni),""")
# 季列
rep("""      roe:ni4!=null&&eqA>0?ni4/eqA*100:null,debt:x.tl!=null&&x.ta?x.tl/x.ta*100:null,at:rev4!=null&&taA>0?rev4/taA:null,""",
"""      roe:ni4!=null&&eqA>0?ni4/eqA*100:null,debt:x.tl!=null&&x.ta?x.tl/x.ta*100:null,...dbt(x,ni4),at:rev4!=null&&taA>0?rev4/taA:null,""")
# dbt 函式（放在 row 之前）
rep("""  const row=(l,qs,y,ttm)=>{""",
"""  // 負債結構：tl 總負債、ib 有息、nib 無息＝總負債−有息、cash 現金、nd 淨負債＝有息−現金、ibr 有息負債比(%總資產)、nde 淨負債／權益(%)、ndy 淨負債÷淨利（幾年還清）
  const dbt=(z,ni)=>{const tl=z.tl,ib=z.ib,cash=z.cash;if(tl==null||ib==null)return {tl,ib:null,nib:null,cash,nd:null,ibr:null,nde:null,ndy:null};
    const nd=cash!=null?ib-cash:null;return {tl,ib,lease:z.lease,nib:Math.max(0,tl-ib),cash,nd,ibr:z.ta?ib/z.ta*100:null,nde:nd!=null&&z.eq>0?nd/z.eq*100:null,ndy:nd!=null&&nd>0&&ni>0?nd/ni:null}};
  const row=(l,qs,y,ttm)=>{""")

# 5. 四捨五入：ndy 兩位
rep("""(['eps','div','sdiv','at','lev'].includes(a)?r2(v):r1(v))""",
    """(['eps','div','sdiv','at','lev','ndy'].includes(a)?r2(v):r1(v))""")

# 6. 快取鍵升版
rep("const k='y10v6_'+id,c=store.get(k);", "const k='y10v7_'+id,c=store.get(k);")
rep("x.startsWith('y10v5_')||x.startsWith('y10v6_')).forEach", "x.startsWith('y10v5_')||x.startsWith('y10v6_')||x.startsWith('y10v7_')).forEach")

# 7. 頁籤 'l' 的圖
rep("""  }else if(Y10T==='d'){
    o.yAxis.scale=false;o.grid.right=40;""",
"""  }else if(Y10T==='l'){
    o.yAxis.scale=false;o.grid.right=40;
    const mx=Math.max(1,...R.map(x=>Math.max(x.tl||0,x.cash||0)));
    {const st=nice5(mx*1.3/5);o.yAxis={...o.yAxis,min:0,max:Math.ceil(mx*1.3/st)*st,interval:st}}
    const rv=R.map(x=>x.ibr).filter(v=>v!=null),rmx=rv.length?Math.max(...rv,10):10;   // 右軸上限壓在比率最高點上方一點，讓比率線浮在柱子總額標籤之上
    o.yAxis=[o.yAxis,{...o.yAxis,min:0,max:rmx*1.12,interval:undefined,splitLine:{show:false},axisLabel:{show:false}}];
    const sIB={...bar('有息負債','ib',warm,big),stack:'d',label:{show:false}},
      sNIB={...bar('無息負債','nib',mu,big),stack:'d'};
    sNIB.data=sNIB.data.map(d=>({...d,itemStyle:{...d.itemStyle,opacity:(d.itemStyle.opacity||1)*.55}}));
    sNIB.label={...lab(v=>v,fg),formatter:p=>{const x=R[p.dataIndex];return (Q?p.dataIndex===R.length-1:show(p.dataIndex))&&x.tl!=null?big(x.tl):''}};
    sIB.data=sIB.data.map(d=>({...d,itemStyle:{...d.itemStyle,borderRadius:0}}));
    const cl={...line('現金','cash',acc),endLabel:{show:true,color:acc,fontSize:10,fontFamily:'IBM Plex Mono',formatter:p=>p.value==null?'':big(p.value)}};
    const rl=line('有息負債比','ibr',warm,1,true);rl.endLabel.formatter=p=>p.value==null?'':fmt(p.value,0)+'%';rl.lineStyle.width=1.5;
    o.series=[sIB,sNIB,cl,rl];
    const ld=[...R].reverse().find(x=>x.ib!=null),fin=/金融|保險|證券|銀行/.test(indOfStock());
    let v='';
    if(ld){const lbl=ld.ttm?'近四季':ld.l;
      v=`${lbl}：總負債 ${big(ld.tl)} 億＝有息 ${big(ld.ib)}（占總資產 ${fmt(ld.ibr,0)}%）＋無息 ${big(ld.nib)}；現金 ${ld.cash==null?'—':big(ld.cash)} 億`+
        (ld.nd!=null?`，${ld.nd<=0?`淨現金 ${big(-ld.nd)} 億`:`淨負債 ${big(ld.nd)} 億`}`:'')+(ld.lease&&ld.ib>0&&ld.lease/ld.ib>=.05?`（有息含租賃負債 ${big(ld.lease)} 億）`:'')+'。';
      if(fin)v+='金融業的負債＝存款／保費，這一頁不適用。';
      else if(ld.nd!=null&&ld.nd<=0)v+='🟢 淨現金：手上現金比全部借款多，沒有償債壓力。';
      else if(ld.nde!=null){const lossNow=ld.ndy==null;
        v+=(lossNow?'🟠 淨負債／權益 ':ld.nde<50?'🟢 淨負債／權益 ':ld.nde<100?'🟠 淨負債／權益 ':'🔴 淨負債／權益 ')+fmt(ld.nde,0)+'%'+
          (lossNow?'，近期虧損、靠獲利還不了，要看現金撐不撐得到轉虧為盈':`，約 ${fmt(ld.ndy,1)} 年淨利可還清`+(ld.nde>=100?'；借的比自己的本還多，升息或景氣轉差時最先出事':ld.nde>=50?'；偏重，要搭配利息保障倍數看':'；合理'))+'。'}
      const p0=R.find(x=>x.ib!=null),lk=R.filter(x=>x.ib!=null);
      if(p0&&lk.length>=3&&p0!==ld){const g=ld.ib-p0.ib,ni=R.filter(x=>x.ni!=null).slice(-3);
        if(g>0&&p0.ib>0&&g/p0.ib>=1)v+=`有息負債從 ${p0.ttm?'近四季':p0.l} 的 ${big(p0.ib)} 億增到 ${big(ld.ib)} 億（×${fmt(ld.ib/p0.ib,1)}），要對照現金流頁看是擴產還是在補營運缺口。`}}
    foot=`柱：期末總負債拆成有息（橘＝借款、公司債、租賃）與無息（灰＝應付帳款、合約負債、應付費用等）；線：現金及約當現金（藍）、有息負債比＝有息負債 ÷ 總資產（橘虛線，右軸）。${v}無息負債多半是對供應商或客戶的議價力，不是壞事；真正要還的是有息那段。`;
  }else if(Y10T==='d'){
    o.yAxis.scale=false;o.grid.right=40;""")

# nice5 輔助（放在 renderY10 的 gc 定義旁）
rep("""  const gc=k=>x=>x[k]==null?mu:x[k]>0?up:x[k]<0?dn:mu,big=v=>Math.abs(v)>=1000?String(Math.round(v)):f(v);""",
"""  const gc=k=>x=>x[k]==null?mu:x[k]>0?up:x[k]<0?dn:mu,big=v=>Math.abs(v)>=1000?String(Math.round(v)):f(v),
    nice5=v=>{const e=Math.pow(10,Math.floor(Math.log10(v||1)));return [1,2,2.5,5,10].map(k=>k*e).find(k=>k>=v)};""")

# 8. tooltip 加負債行
rep("""    L.push(`ROE ${f(x.roe,1)}%・負債比 ${f(x.debt,1)}%`+(x.cov!=null?`・利息保障 ${x.cov>=50?'>50':fmt(x.cov,1)} 倍`:''));""",
"""    L.push(`ROE ${f(x.roe,1)}%・負債比 ${f(x.debt,1)}%`+(x.cov!=null?`・利息保障 ${x.cov>=50?'>50':fmt(x.cov,1)} 倍`:''));
    if(x.ib!=null)L.push(`有息負債 ${f(x.ib,0)}・無息 ${f(x.nib,0)}・現金 ${f(x.cash,0)} 億`+(x.nd!=null?`・${x.nd<=0?'淨現金 '+f(-x.nd,0):'淨負債 '+f(x.nd,0)} 億`:''));""")

# 9. 端點標籤避讓清單加 'l'
rep("""{const li={p:[0,1,2],r:o.series.map((x,i)=>x.type==='line'?i:-1).filter(i=>i>=0),d:[1,2],u:[0,1,2,3]}[Y10T];""",
    """{const li={p:[0,1,2],r:o.series.map((x,i)=>x.type==='line'?i:-1).filter(i=>i>=0),l:[2,3],d:[1,2],u:[0,1,2,3]}[Y10T];""")

# 10. 明細表加「有息負債」「淨負債」欄
rep("""<th>負債比</th><th>利息保障</th><th>自由現金流</th><th>年均PE</th></tr></thead><tbody>'+""",
    """<th>負債比</th><th>有息負債</th><th>淨負債</th><th>利息保障</th><th>自由現金流</th><th>年均PE</th></tr></thead><tbody>'+""")
rep("""<td>${c(x.debt,1)}</td><td>${x.cov==null?'—':x.cov>=50""",
    """<td>${c(x.debt,1)}</td><td>${c(x.ib,0)}</td><td>${x.nd==null?'—':`<span class="${x.nd<=0?'up':''}">${c(x.nd,0)}</span>`}</td><td>${x.cov==null?'—':x.cov>=50""")

# 11. 偵錯列印
rep("""(window.__y10dbg?' 【偵錯】含「利息／財務」的科目：'""",
    """(window.__y10dbgL&&Y10T==='r'?' 【偵錯】負債科目：'+(window.__y10dbgL.join('；')||'無')+' ':'')+(window.__y10dbg?' 【偵錯】含「利息／財務」的科目：'""")

# 11b. ROE負債頁尾的提示改指向新頁籤
rep("要看負債是有息借款還是客戶預收／應付帳款（財報附註）。", "有息借款還是應付帳款看「💳 負債」頁籤。")

# 11c. 作用中的頁籤捲進可視範圍（新頁籤在最右邊，iPhone 上會被捲出畫面）
rep("""  $('y10Tab').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.t===Y10T));""",
"""  $('y10Tab').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.t===Y10T));
  {const tb=$('y10Tab'),ab=tb.querySelector('[aria-pressed=true]');if(ab){const l=ab.offsetLeft,r=l+ab.offsetWidth;if(l<tb.scrollLeft)tb.scrollLeft=Math.max(0,l-6);else if(r>tb.scrollLeft+tb.clientWidth)tb.scrollLeft=r-tb.clientWidth+6}}""")

# 12. 版本標
rep("""foot+' 資料：FinMind，進這一頁才即時抓，手機快取 12 小時。'""",
    """foot+' 資料：FinMind，進這一頁才即時抓，手機快取 12 小時。'+(Y10T==='l'?' v1109d':'')""")

open(dst, 'w', encoding='utf-8').write(s)
print('ok', n0, '->', len(s))
