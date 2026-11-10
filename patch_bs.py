#!/usr/bin/env python3
"""10年財報加「⚖️ 資產負債」頁籤：每期兩根堆疊柱並排——
左＝資產（現金／應收／存貨／固定資產／其他），右＝資金來源（流動負債／非流動負債／權益），
線＝流動比、速動比（右軸）；頁尾寫資產配置、短期償債、應收＋存貨占比變化、固定資產 vs 營收。
用法：python3 patch_bs.py index.html beta.html
"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
n0 = len(s)

def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (s.count(old), old[:80])
    s = s.replace(old, new)

# 1. 頁籤按鈕（放在「💳 負債」右邊）
rep('<button type="button" data-t="l">💳 負債</button>',
    '<button type="button" data-t="l">💳 負債</button><button type="button" data-t="b">⚖️ 資產負債</button>')

# 2. buildY10：資產負債表多抓 應收、存貨、固定資產、流動資產、流動負債、預付款項
rep("""  if(location.search.includes('dbg'))window.__y10dbgL=""",
"""  // 資產負債頁籤：應收（帳款＋票據，含關係人）、存貨、不動產廠房設備、流動資產／流動負債合計、預付款項；_per 結尾的是占比列，不能加進來
  const bsumV=re=>{const o={};bs.forEach(r=>{if(r.value==null||/_per$/.test(r.type||''))return;const nm=(r.origin_name||'').trim();if(re.test(nm))o[r.date]=(o[r.date]||0)+r.value});return o};
  const ARRE=/^應收(帳款|票據)([－\\-—]\\s*關係人)?(淨額)?$/,AR=bsumV(ARRE),INV=b(['Inventories'],/^存貨(淨額|合計)?$/),
    PPE=b(['PropertyPlantAndEquipment'],/^不動產、廠房及設備(淨額|合計)?$/),CA=b(['CurrentAssets'],/^流動資產(合計|總計|總額)$/),
    CL=b(['CurrentLiabilities'],/^流動負債(合計|總計|總額)$/),PREP=b(['Prepayments'],/^預付款項$/);
  if(location.search.includes('dbg'))window.__y10dbgB=[...new Set(bs.filter(r=>!/_per$/.test(r.type||'')&&/應收|存貨|不動產、廠房|流動資產|流動負債|預付/.test(r.origin_name||'')).map(r=>r.type+'｜'+r.origin_name))];
  if(location.search.includes('dbg'))window.__y10dbgL=""")

# 3. 單季資料加欄位
rep("""      ib:TA[d]!=null?e8(IB[d]||0):null,lease:e8(LEASE[d]||0),cash:e8(CASH[d])})});""",
"""      ib:TA[d]!=null?e8(IB[d]||0):null,lease:e8(LEASE[d]||0),cash:e8(CASH[d]),
      ar:e8(AR[d]),inv:e8(INV[d]),ppe:e8(PPE[d]),ca:e8(CA[d]),cl:e8(CL[d]),prep:e8(PREP[d])})});""")

# 4. bsx()：資產配置／資金來源／流動比、速動比（放在 row 之前），年列與季列都展開
rep("""  const row=(l,qs,y,ttm)=>{""",
"""  // 資產負債：ta 總資產＝cash＋ar＋inv＋ppe＋oa(其他)；資金來源＝cl 流動負債＋ncl 非流動負債＋eqt 權益（ta−tl，含非控制權益）；
  // cr 流動比＝流動資產÷流動負債、qr 速動比＝(流動資產−存貨−預付)÷流動負債（%）；aiw 應收＋存貨占總資產(%)
  const bsx=z=>{const ta=z.ta;if(ta==null)return {};const tl=z.tl,cl=z.cl,oa=Math.max(0,ta-(z.cash||0)-(z.ar||0)-(z.inv||0)-(z.ppe||0));
    return {ta,ar:z.ar,inv:z.inv,ppe:z.ppe,oa,cl,ncl:tl==null?null:cl==null?tl:Math.max(0,tl-cl),eqt:tl==null?null:ta-tl,
      cr:z.ca!=null&&cl>0?z.ca/cl*100:null,qr:z.ca!=null&&cl>0?(z.ca-(z.inv||0)-(z.prep||0))/cl*100:null,aiw:ta>0?((z.ar||0)+(z.inv||0))/ta*100:null}};
  const row=(l,qs,y,ttm)=>{""")
rep("""      ...dbt(z,ni),
""", """      ...dbt(z,ni),...bsx(z),
""")
rep("""debt:x.tl!=null&&x.ta?x.tl/x.ta*100:null,...dbt(x,ni4),at:""", """debt:x.tl!=null&&x.ta?x.tl/x.ta*100:null,...dbt(x,ni4),...bsx(x),at:""")

# 5. 快取鍵升版
rep("const k='y10v7_'+id,c=store.get(k);", "const k='y10v8_'+id,c=store.get(k);")
rep("x.startsWith('y10v6_')||x.startsWith('y10v7_')).forEach", "x.startsWith('y10v6_')||x.startsWith('y10v7_')||x.startsWith('y10v8_')).forEach")

# 6. 季模式只畫近 12 季（一期兩根柱，40 季塞不下）
rep("""  if(Y10T==='d')R=F;   // 股利頁籤不畫近4季""",
"""  if(Y10T==='d')R=F;   // 股利頁籤不畫近4季
  if(Y10T==='b'&&Q)R=R.slice(-12);   // 資產負債一期兩根柱，季模式只畫近 12 季""")

# 7. 頁籤 'b' 的圖
rep("""  }else if(Y10T==='d'){
    o.yAxis.scale=false;o.grid.right=40;o.yAxis=[""",
"""  }else if(Y10T==='b'){
    o.yAxis.scale=false;o.grid={...o.grid,right:40,top:46};o.legend={...o.legend,itemGap:7,itemWidth:9,textStyle:{...o.legend.textStyle,fontSize:10}};
    const mx=Math.max(1,...R.map(x=>x.ta||0));
    // 上下分格（同一個座標區）：柱子壓在下面 64%，流動比／速動比兩條線用右軸換算後固定落在最上面一條（80%～96% 高度），互不重疊
    let lmaxB;{const st=nice5(mx/4);lmaxB=mx/.64;o.yAxis={...o.yAxis,min:0,max:lmaxB,interval:st,axisLabel:{...o.yAxis.axisLabel,formatter:v=>v<=mx*1.04&&Math.abs(v/st-Math.round(v/st))<1e-6?echarts.format.addCommas(v):''},splitLine:{...o.yAxis.splitLine,show:false}}}
    const CAPR=500,rv=R.flatMap(x=>[x.cr,x.qr]).filter(v=>v!=null).map(v=>Math.min(v,CAPR)),rhi0=rv.length?Math.max(...rv):150,rlo0=rv.length?Math.min(...rv):100,rpad=Math.max(rhi0-rlo0,rhi0*.08,10),rmid=(rhi0+rlo0)/2,
      rlo=rhi0-rlo0<rpad?rmid-rpad/2:rlo0,rhi=rhi0-rlo0<rpad?rmid+rpad/2:rhi0,rS=(rhi-rlo)/.16,rmin=rlo-.8*rS;
    o.yAxis=[o.yAxis,{...o.yAxis,min:rmin,max:rmin+rS,interval:undefined,splitLine:{show:false},axisLabel:{show:false}}];
    const dark=/^#?[0-3]/.test(css('--bg').replace('#','')),cInv=dark?'#b59cff':'#7a5bd0',cPpe=dark?'#8fa3bd':'#5f7390';
    const sb=(name,k,col,stack,op)=>{const b0=bar(name,k,col,big);b0.stack=stack;b0.label={show:false};b0.barGap='10%';b0.barCategoryGap=Q?'24%':'26%';
      b0.data=b0.data.map(d=>({...d,itemStyle:{...d.itemStyle,borderRadius:0,opacity:(d.itemStyle.opacity||1)*(op||1)}}));b0.itemStyle={color:col,opacity:op||1};return b0};
    const A5=[sb('現金','cash',acc,'a'),sb('應收','ar',acc2,'a'),sb('存貨','inv',cInv,'a'),sb('固定資產','ppe',cPpe,'a'),sb('其他資產','oa',mu,'a',.3)],
      L3=[sb('流動負債','cl',warm,'f'),sb('長期負債','ncl',warm,'f',.45),sb('權益','eqt',fg,'f',.55)];
    A5[4].label={...lab(v=>v,fg),formatter:p=>{const x=R[p.dataIndex];return (Q?p.dataIndex===R.length-1:show(p.dataIndex))&&x.ta!=null?big(x.ta):''}};
    const pl=(n,k,col,dash)=>{const l0=line(n,k,col,1,dash);l0.data=R.map(x=>x[k]==null?null:Math.min(x[k],CAPR));l0.lineStyle.width=1.5;l0.endLabel.formatter=p=>p.value==null?'':(p.value>=CAPR?'>'+CAPR:fmt(p.value,0))+'%';return l0};
    A5[0].markLine={silent:true,symbol:'none',label:{show:false},lineStyle:{color:mu,type:'dotted',opacity:.6},data:[{yAxis:lmaxB*.755}]};
    o.series=[...A5,...L3,pl('流動比','cr',fg),pl('速動比','qr',fg,true)];
    const ld=[...R].reverse().find(x=>x.ta!=null),p0=R.find(x=>x.ta!=null),fin=/金融|保險|證券|銀行/.test(indOfStock());
    let v='';
    if(ld){const lbl=ld.ttm?'最新一季':ld.l,sh=k=>ld[k]==null?'—':fmt(ld[k]/ld.ta*100,0)+'%';
      v=`${lbl}總資產 ${big(ld.ta)} 億：現金 ${sh('cash')}、應收 ${sh('ar')}、存貨 ${sh('inv')}、固定資產 ${sh('ppe')}、其他 ${sh('oa')}；錢的來源：${ld.cl==null?`負債 ${sh('ncl')}`:`流動負債 ${sh('cl')}、長期負債 ${sh('ncl')}`}、權益 ${sh('eqt')}。`;
      if(fin)v+='金融業的資產＝放款／投資、負債＝存款／保費，沒有流動、非流動之分，這一頁不適用。';
      else{
        if(ld.cr!=null)v+=(ld.cr>=150&&ld.qr>=100?'🟢':ld.cr<100?'🔴':'🟠')+` 流動比 ${fmt(ld.cr,0)}%、速動比 ${fmt(ld.qr,0)}%`+
          (ld.cr>=150&&ld.qr>=100?'，一年內要還的錢手上的流動資產夠付。':ld.cr<100?'，流動資產不夠付一年內到期的負債，要靠營業現金流或借新還舊（電信、通路、航空這類收現快的行業天生偏低，搭配現金流頁看）。':'，短期資金偏緊，要看營業現金流穩不穩。');
        else v+='財報沒有流動資產／流動負債合計，無法算流動比。';
        if(p0&&p0!==ld&&p0.aiw!=null&&ld.aiw!=null){const d=ld.aiw-p0.aiw,l0=p0.ttm?'最新一季':p0.l;
          if(d>=5)v+=`⚠️ 應收＋存貨占總資產從 ${l0} 的 ${fmt(p0.aiw,0)}% 升到 ${fmt(ld.aiw,0)}%，錢卡在客戶和倉庫的比例變高，對照存貨健康度卡與營收有沒有跟上。`;
          else if(d<=-5)v+=`應收＋存貨占總資產從 ${fmt(p0.aiw,0)}% 降到 ${fmt(ld.aiw,0)}%，資產變輕。`}
        if(p0&&p0!==ld&&p0.ppe>0&&ld.ppe!=null&&ld.ppe/p0.ppe>=1.5){const pm=ld.ppe/p0.ppe,rm=p0.rev>0&&ld.rev>0?ld.rev/p0.rev:null;
          v+=`固定資產 ×${fmt(pm,1)}`+(rm!=null?`、同期營收 ×${fmt(rm,1)}`+(pm>rm*1.3?'，擴產跑在營收前面，要看新產能有沒有訂單填滿。':'，產能有換到營收。'):'。')}}}
    foot=`每期兩根柱等高（資產＝負債＋權益）：左柱＝錢放在哪（藍 現金、青 應收、紫 存貨、灰藍 固定資產、淡灰 其他），右柱＝錢從哪來（橘 流動負債＝一年內要還、淡橘 長期負債、深灰 權益＝股東的錢）。線（畫在柱子上方獨立一格，只看走勢與尾端數字）：流動比＝流動資產 ÷ 流動負債（實線）、速動比＝再扣掉存貨與預付（虛線），>150%／>100% 算安全。${Q?'季模式只畫近 12 季。':''}${v}有息／無息負債與現金對比看「💳 負債」頁籤。`+
      (window.__y10dbgB?' 【偵錯】資產負債科目：'+(window.__y10dbgB.join('；')||'無'):'');
  }else if(Y10T==='d'){
    o.yAxis.scale=false;o.grid.right=40;o.yAxis=[""")

# 8. 展開區加兩行；薄條第一行
rep("""if(x.at!=null)L.push(`周轉率 ${fmt(x.at,2)} 次""",
"""if(x.ta!=null)L.push(`總資產 ${f(x.ta,0)} 億：現金 ${f(x.cash,0)}・應收 ${f(x.ar,0)}・存貨 ${f(x.inv,0)}・固定資產 ${f(x.ppe,0)}・其他 ${f(x.oa,0)}`+(x.cr!=null?`｜流動比 ${fmt(x.cr,0)}%・速動比 ${fmt(x.qr,0)}%`:''));if(x.at!=null)L.push(`周轉率 ${fmt(x.at,2)} 次""")
rep("""    else if(T==='d')m=`股利 ${f(x.div,2)} 元""",
"""    else if(T==='b')m=x.ta==null?'無資產負債資料':`資產 <b>${f(x.ta,0)}</b> 億＝負債 ${f(x.tl,0)}＋權益 ${f(x.eqt,0)}`+(x.cr!=null?`・流動比 ${fmt(x.cr,0)}%・速動 ${fmt(x.qr,0)}%`:'');
    else if(T==='d')m=`股利 ${f(x.div,2)} 元""")

# 9. 端點標籤避讓：流動比、速動比兩條線
rep("""l:[2,3],d:[1,2],u:[0,1,2,3]}[Y10T];""", """l:[2,3],b:[8,9],d:[1,2],u:[0,1,2,3]}[Y10T];""")

# 10. 明細表加「流動比」「速動比」欄
rep("""<th>負債比</th><th>有息負債</th>""", """<th>負債比</th><th>流動比</th><th>速動比</th><th>有息負債</th>""")
rep("""<td>${c(x.debt,1)}</td><td>${c(x.ib,0)}</td>""",
    """<td>${c(x.debt,1)}</td><td>${x.cr==null?'—':`<span class="${x.cr<100?'dn':''}">${c(x.cr,0)}</span>`}</td><td>${c(x.qr,0)}</td><td>${c(x.ib,0)}</td>""")

# 11. 版本標
rep("""(Y10T==='l'?' v1109e':'')""", """(Y10T==='l'?' v1109e':Y10T==='b'?' v1110d':'')""")

open(dst, 'w', encoding='utf-8').write(s)
print('ok', n0, '->', len(s))
