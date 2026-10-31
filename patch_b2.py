#!/usr/bin/env python3
"""第二批：10年財報加「股利」「杜邦」頁籤、ROE負債頁籤加利息保障倍數、個股頁標頭加同業對照
用法：python3 patch_b2.py index.html beta.html
"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:70])
    s = s.replace(old, new)

# ---------- ① 頁籤按鈕 ----------
rep('<button type="button" data-t="r">🏦 ROE負債</button><button type="button" data-t="c">💵 現金流</button>',
    '<button type="button" data-t="r">🏦 ROE負債</button><button type="button" data-t="d">💸 股利</button><button type="button" data-t="u">🧮 杜邦</button><button type="button" data-t="c">💵 現金流</button>')

# ---------- ② buildY10：多抓稅前淨利、利息費用；row 多算殖利率、周轉率、權益乘數、利息保障 ----------
rep("NI=g(['EquityAttributableToOwnersOfParent'],/^母公司業主/),EPS=g(['EPS'],/^基本每股盈餘/);",
    "NI=g(['EquityAttributableToOwnersOfParent'],/^母公司業主/),EPS=g(['EPS'],/^基本每股盈餘/),\n"
    "    PRE=g(['PreTaxIncome','IncomeBeforeIncomeTax','ProfitLossBeforeTax'],/^(繼續營業單位)?稅前(淨利|損益)/),INT0=g(['InterestExpense','FinanceCosts','FinanceCost','InterestExpenses'],/(財務成本|利息費用|利息支出)/),\n"
    "    INTC=toQuarterS(y10Ser(cf,['InterestPaid','InterestPayed','PaymentsOfInterest'],/(支付之?利息|利息支付|支付利息)/)),\n"
    "    INT=Object.keys(INT0).length?INT0:(()=>{const o={};Object.entries(INTC).forEach(([k,v])=>{const [y,n]=k.split('-');o[`${y}-${Y10QD[n-1]}`]=v});return o})(),INTSRC=Object.keys(INT0).length?'is':Object.keys(INT).length?'cf':null;\n"
    "  if(location.search.includes('dbg')){const hit=r=>/利息|財務|Interest|Finance/i.test((r.origin_name||'')+' '+(r.type||''));window.__y10dbg=[...new Set([...fs.filter(hit).map(r=>'損益表 '+r.type+'｜'+r.origin_name),...cf.filter(hit).map(r=>'現金流 '+r.type+'｜'+r.origin_name)])]}")
rep("eq:e8(eqAt(d)),ta:e8(TA[d]),tl:e8(tlAt(d))})});",
    "eq:e8(eqAt(d)),ta:e8(TA[d]),tl:e8(tlAt(d)),pre:e8(PRE[d]),intx:INT[d]==null?null:e8(Math.abs(INT[d]))})});")
rep("const z=qs[qs.length-1],pz=Qa.find(x=>x.y===z.y-1&&x.n===z.n),eqA=z.eq!=null?(pz&&pz.eq!=null?(z.eq+pz.eq)/2:z.eq):null;",
    "const z=qs[qs.length-1],pz=Qa.find(x=>x.y===z.y-1&&x.n===z.n),eqA=z.eq!=null?(pz&&pz.eq!=null?(z.eq+pz.eq)/2:z.eq):null,\n"
    "      taA=z.ta!=null?(pz&&pz.ta!=null?(z.ta+pz.ta)/2:z.ta):null,pre=S(qs,'pre'),intx=S(qs,'intx');")
rep("po:dd&&eps>0?dd.c/eps*100:null,close:pc||null,pe:pa&&eps>0?pa/eps:null}};",
    "po:dd&&eps>0?dd.c/eps*100:null,close:pc||null,pe:pa&&eps>0?pa/eps:null,\n"
    "      yld:dd&&pa>0?dd.c/pa*100:null,at:rev!=null&&taA>0?rev/taA:null,lev:taA>0&&eqA>0?taA/eqA:null,cov:pre!=null&&intx>0?(pre+intx)/intx:null}};")
# 季序列：近四季營收 ÷ 平均資產、權益乘數、利息保障（近四季）
rep("const ni4=c4?S(c4,'ni'):null,eqA=x.eq!=null?(c4&&c4[0]&&ly&&ly.eq!=null?(x.eq+ly.eq)/2:x.eq):null;",
    "const ni4=c4?S(c4,'ni'):null,eqA=x.eq!=null?(c4&&c4[0]&&ly&&ly.eq!=null?(x.eq+ly.eq)/2:x.eq):null,\n"
    "      taA=x.ta!=null?(c4&&ly&&ly.ta!=null?(x.ta+ly.ta)/2:x.ta):null,rev4=c4?S(c4,'rev'):null,pre4=c4?S(c4,'pre'):null,int4=c4?S(c4,'intx'):null;")
rep("roe:ni4!=null&&eqA>0?ni4/eqA*100:null,debt:x.tl!=null&&x.ta?x.tl/x.ta*100:null,ry:ly&&ly.rev?",
    "roe:ni4!=null&&eqA>0?ni4/eqA*100:null,debt:x.tl!=null&&x.ta?x.tl/x.ta*100:null,at:rev4!=null&&taA>0?rev4/taA:null,lev:taA>0&&eqA>0?taA/eqA:null,cov:pre4!=null&&int4>0?(pre4+int4)/int4:null,ry:ly&&ly.rev?")
rep("k[a]=typeof v==='number'?(['eps','div','sdiv'].includes(a)?r2(v):r1(v)):v;",
    "k[a]=typeof v==='number'?(['eps','div','sdiv','at','lev'].includes(a)?r2(v):r1(v)):v;")
rep("return {A:A.slice(-12).map(rr),Q:Qr.slice(-40).map(rr),asof:lq.l,adj:adjK?Math.round(adjK*100)/100:null};",
    "return {A:A.slice(-12).map(rr),Q:Qr.slice(-40).map(rr),asof:lq.l,adj:adjK?Math.round(adjK*100)/100:null,intSrc:INTSRC};")
# 快取鍵升版（舊快取沒有新欄位）
rep("const k='y10v4_'+id,c=store.get(k);", "const k='y10v5_'+id,c=store.get(k);")
rep("x.startsWith('y10v2_')||x.startsWith('y10v3_')||x.startsWith('y10v4_')", "x.startsWith('y10v2_')||x.startsWith('y10v3_')||x.startsWith('y10v4_')||x.startsWith('y10v5_')")

# ---------- ③ renderY10：股利／杜邦頁籤，ROE負債加利息保障 ----------
rep("const Q=Y10P==='q';let R=Q?Y10.Q:A,FL=null;",
    "const Q=Y10P==='q'&&Y10T!=='d';let R=Q?Y10.Q:A,FL=null;   // 股利按年度歸屬，季模式也用年度")
rep("$('y10U').textContent=Q?`${R.length}季`:`${F.length}年${T?'+近4季':''}`;",
    "if(Y10T==='d')R=F;   // 股利頁籤不畫近4季\n  $('y10U').textContent=Q?`${R.length}季`:`${R.length}年${R.some(x=>x.ttm)?'+近4季':''}`;")
old = """  }else if(Y10T==='r'){
    o.yAxis.axisLabel.formatter='{value}%';o.grid.right=34;
    o.series=[line('ROE','roe',acc),line('負債比','debt',warm,0,true)];
    o.series[0].markLine={silent:true,symbol:'none',label:{show:true,position:'insideStartTop',formatter:'15%',color:mu,fontSize:9},lineStyle:{color:mu,type:'dotted'},data:[{yAxis:15}]};
    foot=`ROE＝母公司淨利 ÷ 平均股東權益${Q?'（近四季淨利）':''}，長期 ≥15% 算優秀；負債比＝總負債 ÷ 總資產（虛線），金融業天生很高不適用。`;
  }else{"""
new = """  }else if(Y10T==='r'){
    o.yAxis.axisLabel.formatter='{value}%';o.grid.right=34;
    const hasCov=R.some(x=>x.cov!=null),CAP=50;
    const cvs=R.map(x=>x.cov).filter(v=>v!=null),cmx=cvs.length?Math.max(...cvs):0,cmax=cmx>=CAP?CAP*1.1:Math.max(8,Math.ceil(cmx*1.25));
    // 左軸（ROE、負債比 %）自己定上下限，右軸（倍）依同比例設負的下限，讓兩軸的 0 對齊（ROE 為負時右軸的 0 才不會掉到圖底）
    const lv=R.flatMap(x=>[x.roe,x.debt]).filter(v=>v!=null),nice=v=>{const e=Math.pow(10,Math.floor(Math.log10(v||1)));return [1,2,2.5,5,10].map(k=>k*e).find(k=>k>=v)};
    const lhi=lv.length?Math.max(...lv,15):15,llo=lv.length?Math.min(...lv,0):0,st=nice(Math.max(lhi*1.12-Math.min(llo,0),10)/5),lmax=Math.ceil(lhi*1.12/st)*st,lmin=llo<0?-Math.ceil(-llo*1.1/st)*st:0;
    o.yAxis={...o.yAxis,scale:false,min:lmin,max:lmax,interval:st};
    o.yAxis=[o.yAxis,{...o.yAxis,min:lmin/lmax*cmax,max:cmax,interval:undefined,splitLine:{show:false},axisLabel:{show:false}}];o.grid.right=40;
    o.series=[line('ROE','roe',acc),line('負債比','debt',warm,0,true)];
    o.series[0].markLine={silent:true,symbol:'none',label:{show:true,position:'insideStartTop',formatter:'15%',color:mu,fontSize:9},lineStyle:{color:mu,type:'dotted'},data:[{yAxis:15}]};
    if(hasCov){const cl=line('利息保障(倍)','cov',acc2,1);cl.data=R.map(x=>x.cov==null?null:Math.max(0,Math.min(x.cov,CAP)));cl.endLabel.formatter=p=>p.value==null?'':(p.value>=CAP?'>'+CAP:p.value<1?'<1':fmt(p.value,0))+'倍';cl.lineStyle.width=1.5;o.series.push(cl)}
    const lc=[...R].reverse().find(x=>x.cov!=null),ld=[...R].reverse().find(x=>x.debt!=null);
    foot=`ROE＝母公司淨利 ÷ 平均股東權益${Q?'（近四季淨利）':''}，長期 ≥15% 算優秀；負債比＝總負債 ÷ 總資產（虛線），金融業天生很高不適用。`+
      (hasCov?`利息保障倍數＝(稅前淨利＋利息費用) ÷ 利息費用（${Y10.intSrc==='cf'?'利息費用取現金流量表「支付之利息」；':''}右軸，圖上截在 ${CAP} 倍）：${lc?`${lc.ttm?'近四季':lc.l} ${lc.cov>=CAP?'>'+CAP:lc.cov<1?'<1（稅前虧損或不夠付利息）':fmt(lc.cov,1)} 倍`:''}${R.some(x=>x.cov!=null&&x.cov<1)?'；虧損年份算出來為負，圖上壓在 0':''}；<3 倍代表獲利只夠付利息，景氣轉差時借新還舊會有壓力，>10 倍很安全。`:'財報沒有利息費用（財務成本）科目或為零，無法算利息保障倍數。'+(window.__y10dbg?' 【偵錯】含「利息／財務」的科目：'+(window.__y10dbg.length?window.__y10dbg.join('；'):'一個都沒有'):''))+
      (ld&&ld.debt!=null&&ld.debt>=60&&!/金融/.test(indOfStock())?`負債比 ${fmt(ld.debt,0)}% 偏高，要看負債是有息借款還是客戶預收／應付帳款（財報附註）。`:'');
  }else if(Y10T==='d'){
    o.yAxis.scale=false;o.grid.right=40;o.yAxis=[o.yAxis,{...o.yAxis,scale:false,min:0,splitLine:{show:false},axisLabel:{show:false}}];
    const pl=line('配息率','po',warm,1),yl=line('殖利率','yld',acc,1);pl.data=R.map(x=>x.po==null?null:Math.min(x.po,150));pl.endLabel.formatter=p=>p.value==null?'':(p.value>=150?'>150':fmt(p.value,0))+'%';yl.endLabel.formatter=p=>p.value==null?'':fmt(p.value,1)+'%';
    o.series=[{...bar('現金股利','div',acc2,v=>f(v,2))},pl,yl];
    const ld=[...R].reverse().find(x=>x.div!=null),pd=ld?R[R.indexOf(ld)-1]:null,dvUp=ld&&pd&&pd.div!=null?ld.div>pd.div:null,epsDn=ld&&pd&&pd.eps>0&&ld.eps!=null?ld.eps<pd.eps:null;
    foot='柱：該年度盈餘配發的現金股利（已分割還原）；線：配息率＝股利 ÷ 當年 EPS（橘，截在 150%）、殖利率＝股利 ÷ 當年年均收盤（藍）。'+
      (ld?`${ld.l} 股利 ${f(ld.div,2)} 元、配息率 ${ld.po==null?'—':fmt(ld.po,0)+'%'}、殖利率 ${ld.yld==null?'—':fmt(ld.yld,1)+'%'}。`:'')+
      (ld&&ld.po!=null&&ld.po>100?'配息率超過 100%＝拿老本或借錢發股利，不可持續；':'')+(dvUp&&epsDn?'股利增加但 EPS 下降，配息率被拉高，下一年可能減發；':'')+
      '高殖利率要看是股價跌出來的（殖利率陷阱）還是獲利撐的。近四季不畫（股利按年度歸屬）。';
  }else if(Y10T==='u'){
    o.yAxis.axisLabel.formatter='{value}%';o.grid.right=34;
    o.grid.right=40;o.yAxis=[o.yAxis,{...o.yAxis,scale:true,splitLine:{show:false},axisLabel:{show:false}}];
    const al=line('周轉率(次)','at',acc2,1,true),ll=line('權益乘數(倍)','lev',mu,1,true);al.endLabel.formatter=ll.endLabel.formatter=p=>p.value==null?'':fmt(p.value,2);
    o.series=[line('ROE','roe',acc),line('淨利率','nm',warm),al,ll];
    // ROE 變化的來源（對數分解）：第一個完整年度 → 最新
    const ok=R.filter(x=>x.roe>0&&x.nm>0&&x.at>0&&x.lev>0),a0=ok[0],a1=ok[ok.length-1];let dec='';
    if(a0&&a1&&a0!==a1){const L=Math.log(a1.roe/a0.roe),c=[['淨利率',Math.log(a1.nm/a0.nm)],['周轉率',Math.log(a1.at/a0.at)],['槓桿',Math.log(a1.lev/a0.lev)]].sort((x,y)=>Math.abs(y[1])-Math.abs(x[1]));
      const lab=x=>x.ttm?'近四季':x.l,ch=(a1.roe/a0.roe-1)*100;
      dec=`${lab(a0)}→${lab(a1)} ROE ${fmt(a0.roe,1)}%→${fmt(a1.roe,1)}%（${pct(ch,0)}）${Math.abs(L)>0.01?`，主要來自「${c[0][0]}」（占變化 ${fmt(Math.abs(c[0][1]/L)*100,0)}%）${c[1]&&Math.abs(c[1][1]/L)>=0.25?`、其次${c[1][0]}`:''}`:''}；`+
        (c[0][0]==='槓桿'&&c[0][1]>0&&L>0?'靠加槓桿把 ROE 拉高，品質較差；':c[0][0]==='淨利率'&&L>0?'靠獲利率提升，品質最好；':c[0][0]==='周轉率'&&L>0?'靠資產用得更有效率；':'')}
    foot=`杜邦拆解：ROE ≈ 淨利率 × 資產周轉率（營收 ÷ 平均總資產，右軸）× 權益乘數（平均總資產 ÷ 平均母公司權益，右軸）${Q?'，季模式用近四季':''}。${dec}淨利率驅動＝定價力，周轉率驅動＝效率，槓桿驅動＝借錢，三者同樣的 ROE 風險完全不同。`;
  }else{"""
rep(old, new)
rep("ch.setOption(o,true);ch.resize();if(Y10T==='p')spreadEnd(ch,o,[0,1,2]);else ch.setOption({graphic:{elements:[]}},{replaceMerge:['graphic']});",
    "ch.setOption(o,true);ch.resize();{const li={p:[0,1,2],r:o.series.map((x,i)=>x.type==='line'?i:-1).filter(i=>i>=0),d:[1,2],u:[0,1,2,3]}[Y10T];if(li)spreadEnd(ch,o,li);else ch.setOption({graphic:{elements:[]}},{replaceMerge:['graphic']})}")
# tooltip 加殖利率、周轉率、槓桿、利息保障
rep("L.push(`ROE ${f(x.roe,1)}%・負債比 ${f(x.debt,1)}%`);",
    "L.push(`ROE ${f(x.roe,1)}%・負債比 ${f(x.debt,1)}%`+(x.cov!=null?`・利息保障 ${x.cov>=50?'>50':fmt(x.cov,1)} 倍`:''));if(x.at!=null)L.push(`周轉率 ${fmt(x.at,2)} 次・權益乘數 ${fmt(x.lev,2)} 倍`+(x.yld!=null?`・殖利率 ${fmt(x.yld,1)}%`:''));")
# 明細表加殖利率、利息保障
rep("<th>現金股利</th><th>配息率</th><th>ROE</th><th>負債比</th><th>自由現金流</th><th>年均PE</th></tr></thead>",
    "<th>現金股利</th><th>配息率</th><th>殖利率</th><th>ROE</th><th>負債比</th><th>利息保障</th><th>自由現金流</th><th>年均PE</th></tr></thead>")
rep("<td>${c(x.po,0)}${x.po!=null?'%':''}</td><td>${c(x.roe,1)}</td><td>${c(x.debt,1)}</td><td>${c(x.fcf,0)}</td>",
    "<td>${c(x.po,0)}${x.po!=null?'%':''}</td><td>${c(x.yld,1)}${x.yld!=null?'%':''}</td><td>${c(x.roe,1)}</td><td>${c(x.debt,1)}</td><td>${x.cov==null?'—':x.cov>=50?'>50':x.cov<1?'<span class=\"dn\">&lt;1</span>':c(x.cov,1)}</td><td>${c(x.fcf,0)}</td>")

# ---------- ④ 同業對照（標頭一行） ----------
rep('<div class="peers" id="peers"></div>', '<div class="meta" id="indCmp" hidden></div>\n  <div class="peers" id="peers"></div>')
rep("    salLine(id);aiLine(id);\n", "    salLine(id);aiLine(id);indCmp(id);\n")
rep("function indOfStock(){", r"""// ---- 同業對照：同官方產業別（「…類」「…業」併同名）的上市櫃股票，summary.json 的本益比／淨值比／殖利率／月營收年增中位數與本股位階 ----
const indKey=s=>(s||'').replace(/[類業]$/,'');
function indCmp(id){
  const el=$('indCmp');el.hidden=true;try{
    if(!S||!S.d||!LIST.length)return;const me=LIST.find(x=>x[0]===id);if(!me||!me[3])return;
    const k=indKey(me[3]),peers=LIST.filter(x=>indKey(x[3])===k&&S.d[x[0]]),mine=S.d[id];if(peers.length<5||!mine)return;
    const col=(i,ok)=>peers.map(x=>S.d[x[0]][i]).filter(v=>v!=null&&isFinite(v)&&ok(v)),med=a=>{const s=[...a].sort((x,y)=>x-y);return s.length?(s.length%2?s[(s.length-1)/2]:(s[s.length/2-1]+s[s.length/2])/2):null},
      rk=(a,v,hiGood)=>{if(v==null||!a.length)return null;const p=Math.round(a.filter(x=>x<v).length/a.length*100);return p},
      F=[['本益比',2,v=>v>0&&v<200,'倍',1,false],['淨值比',3,v=>v>0&&v<50,'倍',1,false],['殖利率',4,v=>v>=0&&v<30,'%',1,true],['營收年增',5,v=>v>-100&&v<1000,'%',0,true]];
    const parts=F.map(([n,i,ok,u,d,hi])=>{const a=col(i,ok),m=med(a),v=mine[i]!=null&&ok(mine[i])?mine[i]:null,p=rk(a,v);if(m==null)return null;
      const cls=v==null||p==null?'':hi?(p>=70?'up':p<=30?'dn':''):(p>=70?'dn':p<=30?'up':'');
      return `<div class="${cls}" title="同業 ${a.length} 檔有值"><span>${n}</span><b>${v==null?'—':fmt(v,d)+u}</b><i>中位 ${fmt(m,d)}${u}</i><i>${p==null?'&nbsp;':'高於 '+p+'% 同業'}</i></div>`}).filter(Boolean);
    if(!parts.length)return;
    el.innerHTML=`<div class="sx" style="margin:4px 0 0">${parts.join('')}</div><div style="font-size:10.5px;margin-top:2px">同業對照：${k}・${peers.length} 檔（上市櫃官方產業別${/^(電子工業|其他)$/.test(me[3])?'，FinMind 分類很粗，參考就好':''}）；紅＝比同業好（本益比／淨值比低、殖利率／營收年增高），綠＝比同業差</div>`;
    el.hidden=false;
  }catch(e){}
}
function indOfStock(){""")

open(dst, 'w', encoding='utf-8').write(s)
print('ok', dst, len(s))
