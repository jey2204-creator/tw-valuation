#!/usr/bin/env python3
"""掃描頁估值模式加「負債」排序／篩選。
資料：data/debt.json（fetch_debt.py 排程，全市場最新一季）→ 沒有的檔在讀估值時多問 FinMind 一次資產負債表（快取 7 天）。
排序鈕「負債」連點循環：淨負債／權益 → 有息負債比 → 負債比（高→低）；篩選：淨現金、負債重≥100%。
小卡：排序／篩選用到負債時，第二顆分位改成負債小標；放大卡加一行負債結構。
用法：python3 patch_dscan.py scan.html beta_scan.html
"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()

def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (s.count(old), old[:90])
    s = s.replace(old, new)

# 1. 按鈕
rep("""<button data-k="pbh" class="vs" hidden title="淨值比歷史分位 高→低">PB貴</button></div>""",
    """<button data-k="pbh" class="vs" hidden title="淨值比歷史分位 高→低">PB貴</button><button data-k="dh" class="vs" hidden title="負債：連點切換 淨負債／權益 → 有息負債比 → 負債比（高→低）">淨負債</button></div>""")
rep("""<button class="f vs" data-vf="pb80" hidden title="淨值比分位 ≥80%">PB≥80%</button></div>""",
    """<button class="f vs" data-vf="pb80" hidden title="淨值比分位 ≥80%">PB≥80%</button><button class="f vs" data-vf="ncash" hidden title="現金 ≥ 有息負債（淨現金）">淨現金</button><button class="f vs" data-vf="d100" hidden title="淨負債／權益 ≥100%（借的比本多）">負債重</button></div>""")

# 2. 狀態
rep("""let MODE='k',RV='auto',SK_K='chg',SK_V='mh';const VSK=new Set(['mh','ml','peh','pbh']),VF={m80:false,m20:false,pe80:false,pb80:false};""",
    """let MODE='k',RV='auto',SK_K='chg',SK_V='mh';const VSK=new Set(['mh','ml','peh','pbh','dh']),VF={m80:false,m20:false,pe80:false,pb80:false,ncash:false,d100:false};
let DK=(()=>{try{return ['nde','ibr','dr'].includes(localStorage.getItem('scanDK'))?localStorage.getItem('scanDK'):'nde'}catch(e){return 'nde'}})();   // 負債排序用哪個尺
const DKL={nde:['淨負債','淨負債／權益 高→低'],ibr:['有息比','有息負債 ÷ 總資產 高→低'],dr:['負債比','總負債 ÷ 總資產 高→低']};
let DEBT={};
// 與 index.html buildY10 的 dbt() 同一套科目：有息＝借款＋票券＋一年內到期＋公司債＋租賃
const IBRE=/^(短期借款|應付短期票券|一年或一營業週期內到期(之)?(長期負債|長期借款|應付公司債)|一年內到期(之)?(長期負債|長期借款|應付公司債)|長期借款|應付公司債|租賃負債)/;
function debtCalc(rows){if(!rows||!rows.length)return null;const d=rows.reduce((m,r)=>r.date>m?r.date:m,'');const R=rows.filter(r=>r.date===d&&r.value!=null);
  const g=re=>R.reduce((a,r)=>a+(re.test((r.origin_name||'').trim())?r.value:0),0),one=(re,types)=>{const t=R.find(r=>types.includes(r.type));return t?t.value:(g(re)||null)};
  const ta=one(/^資產總(計|額)$/,['TotalAssets']),eq=one(/^權益總(計|額)$/,['Equity','TotalEquity']),eqp=one(/^歸屬於母公司業主之權益(合計|總計)?$/,['EquityAttributableToOwnersOfParent'])||eq,cash=one(/^現金及約當現金$/,['CashAndCashEquivalents']);
  let tl=one(/^負債總(計|額)$/,['Liabilities','TotalLiabilities']);if(!ta)return null;if(tl==null&&eq!=null)tl=ta-eq;if(tl==null)return null;
  const ib=g(IBRE),nd=cash==null?null:ib-cash,e8=v=>v==null?null:Math.round(v/1e7)/10;
  return [`${d.slice(2,4)}Q${Math.ceil(+d.slice(5,7)/3)}`,Math.round(tl/ta*1000)/10,Math.round(ib/ta*1000)/10,nd==null||!(eqp>0)?null:Math.round(nd/eqp*1000)/10,e8(ib),e8(cash),e8(tl)]}
function dOf(c){const v=DEBT[c];if(!v||!v[0])return null;return {q:v[0],dr:v[1],ibr:v[2],nde:v[3],ib:v[4],cash:v[5],tl:v[6],nd:v[4]!=null&&v[5]!=null?Math.round((v[4]-v[5])*10)/10:null}}
const dUsed=()=>sortK==='dh'||VF.ncash||VF.d100;
const dCls=(k,v)=>v==null?'p0':k==='nde'?(v<=0?'p1':v>=100?'p4':v>=50?'p3':'p2'):k==='ibr'?(v>=40?'p4':v>=20?'p3':'p1'):(v>=70?'p4':v>=50?'p3':'p1');""")

# 3. 載入 debt.json
rep("""  PRE=new Set((ix||[]).map(x=>x.id));SUM=sm&&sm.d?sm:null}catch(e){}}""",
    """  PRE=new Set((ix||[]).map(x=>x.id));SUM=sm&&sm.d?sm:null}catch(e){}
  try{const j=await fetch('data/debt.json?t='+Math.floor(Date.now()/36e5)).then(r=>r.ok?r.json():null);if(j&&j.d)DEBT=j.d}catch(e){}}""")

# 4. valGet：沒有負債資料就多問一次 FinMind（不影響估值主流程）
rep("""  const pes=riv.map(r=>r[4]),pbs=riv.map(r=>r[5]);
  const j=cycJudge(c,riv,cyc),""",
    """  const pes=riv.map(r=>r[4]),pbs=riv.map(r=>r[5]);
  if(!DEBT[c]||!DEBT[c][0]){const dc=store.get('debt_'+c);if(dc&&dc.v&&Date.now()-dc.t<7*86400e3)DEBT[c]=dc.v;else{try{const y=new Date();y.setDate(y.getDate()-400);const v=debtCalc(await fm('TaiwanStockBalanceSheet',c,y.toISOString().slice(0,10)));if(v){DEBT[c]=v;store.set('debt_'+c,{t:Date.now(),v})}}catch(e){if(e.quota)throw e}}}
  const j=cycJudge(c,riv,cyc),""")

# 5. 排序鈕連點循環＋標籤
rep("""    if(b.dataset.k){if(b.dataset.k==='chg'&&sortK==='chg')CHGP=CHGP==='d'?'w':CHGP==='w'?'m':'d';sortK=b.dataset.k;""",
    """    if(b.dataset.k){if(b.dataset.k==='chg'&&sortK==='chg')CHGP=CHGP==='d'?'w':CHGP==='w'?'m':'d';if(b.dataset.k==='dh'&&sortK==='dh'){DK=DK==='nde'?'ibr':DK==='ibr'?'dr':'nde';try{localStorage.setItem('scanDK',DK)}catch(e){}}sortK=b.dataset.k;""")
rep("""  const cb=document.querySelector('#sortBar button[data-k=chg]');cb.textContent={d:'日漲',w:'週漲',m:'月漲'}[CHGP];""",
    """  {const db=document.querySelector('#sortBar button[data-k=dh]');if(db){db.textContent=DKL[DK][0];db.title='負債：'+DKL[DK][1]+'，連點切換 淨負債／權益 → 有息負債比 → 負債比'}}
  const cb=document.querySelector('#sortBar button[data-k=chg]');cb.textContent={d:'日漲',w:'週漲',m:'月漲'}[CHGP];""")

# 6. 篩選＋排序
rep("""function rowsV(){let R=ROWS.filter(r=>{const v=VAL[r.c];if(!VF.m80&&!VF.m20&&!VF.pe80&&!VF.pb80)return true;if(!v)return false;
    return (!VF.m80||(v.mainPct!=null&&v.mainPct>=80))&&(!VF.m20||(v.mainPct!=null&&v.mainPct<=20))&&(!VF.pe80||(v.pePct!=null&&v.pePct>=80))&&(!VF.pb80||(v.pbPct!=null&&v.pbPct>=80))});
  const ck=CHGK(),g=(r,k)=>{const v=VAL[r.c];return v&&v[k]!=null?v[k]:null};
  const key={li:r=>-r.li,chg:r=>(r[ck]??-9),mh:r=>g(r,'mainPct')??-1,ml:r=>{const p=g(r,'mainPct');return p==null?-1:100-p},peh:r=>g(r,'pePct')??-1,pbh:r=>g(r,'pbPct')??-1}[sortK]||(r=>g(r,'mainPct')??-1);""",
    """function rowsV(){let R=ROWS.filter(r=>{const v=VAL[r.c],d=dOf(r.c);
    if(VF.ncash||VF.d100){if(!d)return false;if(VF.ncash&&!(d.nd!=null&&d.nd<=0))return false;if(VF.d100&&!(d.nde!=null&&d.nde>=100))return false}
    if(!VF.m80&&!VF.m20&&!VF.pe80&&!VF.pb80)return true;if(!v)return false;
    return (!VF.m80||(v.mainPct!=null&&v.mainPct>=80))&&(!VF.m20||(v.mainPct!=null&&v.mainPct<=20))&&(!VF.pe80||(v.pePct!=null&&v.pePct>=80))&&(!VF.pb80||(v.pbPct!=null&&v.pbPct>=80))});
  const ck=CHGK(),g=(r,k)=>{const v=VAL[r.c];return v&&v[k]!=null?v[k]:null},gd=r=>{const d=dOf(r.c);return d&&d[DK]!=null?d[DK]:-9999};
  const key={li:r=>-r.li,chg:r=>(r[ck]??-9),mh:r=>g(r,'mainPct')??-1,ml:r=>{const p=g(r,'mainPct');return p==null?-1:100-p},peh:r=>g(r,'pePct')??-1,pbh:r=>g(r,'pbPct')??-1,dh:gd}[sortK]||(r=>g(r,'mainPct')??-1);""")

# 7. 小卡第二顆：用到負債時換成負債小標
rep("""  const m=v.main==='pb';return m?one('PB',v.pb,v.pbPct,true)+one('PE',v.pe,v.pePct,false):one('PE',v.pe,v.pePct,true)+one('PB',v.pb,v.pbPct,false)}""",
    """  const m=v.main==='pb',main=m?one('PB',v.pb,v.pbPct,true):one('PE',v.pe,v.pePct,true),sub=m?one('PE',v.pe,v.pePct,false):one('PB',v.pb,v.pbPct,false);
  if(dUsed()){const d=dOf(c),k=sortK==='dh'?DK:'nde',x=d?d[k]:null,lab=k==='nde'?'負':k==='ibr'?'息':'債';
    return main+`<span class="pv" title="${d?`${d.q} 總負債 ${d.tl} 億＝有息 ${d.ib}（占資產 ${d.ibr}%）；現金 ${d.cash}；淨負債／權益 ${d.nde==null?'—':d.nde+'%'}`:'沒有負債資料'}"><i>${lab}</i><b class="${dCls(k,x)}">${x==null?'—':k==='nde'&&x<=0?'淨現':Math.round(x)+'%'}</b></span>`}
  return main+sub}""")

# 8. 放大卡加一行
rep("""・近四季 ROE ≈ <b class="${v.roe!=null&&v.roe<5?'dn':''}">${v.roe==null?'—':v.roe+'%'}</b>${v.roe!=null&&v.roe<5?'（淨值報酬低，淨值比低可能是價值陷阱）':''} <button id="cycBtn" style="color:var(--accent);font-weight:700">${v.cyc?'取消循環股':'標為循環股'}</button></div>`})()""",
    """・近四季 ROE ≈ <b class="${v.roe!=null&&v.roe<5?'dn':''}">${v.roe==null?'—':v.roe+'%'}</b>${v.roe!=null&&v.roe<5?'（淨值報酬低，淨值比低可能是價值陷阱）':''} <button id="cycBtn" style="color:var(--accent);font-weight:700">${v.cyc?'取消循環股':'標為循環股'}</button></div>`+(()=>{const d=dOf(r.c);if(!d)return '';const fin=/金融|保險|證券|銀行/.test(IND[r.c]||'');
      const tag=fin?'<span class="pill">金融業不適用</span>':d.nd!=null&&d.nd<=0?'<span class="pill" style="color:var(--down)">🟢 淨現金</span>':d.nde==null?'':d.nde>=100?'<span class="pill" style="color:var(--up)">🔴 負債重</span>':d.nde>=50?'<span class="pill" style="color:var(--warm)">🟠 偏重</span>':'<span class="pill" style="color:var(--down)">🟢 合理</span>';
      return `<div class="sh-t" style="color:var(--muted)"><b>負債</b>（${esc(d.q)}）：總負債 ${d.tl} 億＝有息 <b>${d.ib}</b>（占資產 ${d.ibr}%）＋無息 ${d.tl!=null&&d.ib!=null?Math.max(0,Math.round((d.tl-d.ib)*10)/10):'—'}；現金 ${d.cash==null?'—':d.cash} 億，${d.nd==null?'':d.nd<=0?`淨現金 ${-d.nd} 億`:`淨負債 ${d.nd} 億（÷權益 <b>${d.nde==null?'—':d.nde+'%'}</b>）`} ${tag}</div>`})()})()""")

# 9. 統計列加兩個數
rep("""${nc?`・循環股 <b>${nc}</b> 檔（用淨值比）`:''}・點小卡放大`:'';""",
    """${nc?`・循環股 <b>${nc}</b> 檔（用淨值比）`:''}${(()=>{const ds=ROWS.map(r=>dOf(r.c)).filter(Boolean);return ds.length?`・淨現金 <b class="dn">${ds.filter(d=>d.nd!=null&&d.nd<=0).length}</b> 檔・負債重 <b class="up">${ds.filter(d=>d.nde!=null&&d.nde>=100).length}</b> 檔`:''})()}・點小卡放大`:'';""")

# 10. 頁尾說明
rep("""  $('foot').innerHTML=`<b>估值掃描</b>：""",
    """  $('foot').innerHTML=(dUsed()?`<b>負債</b>：淨負債／權益＝(有息負債 − 現金) ÷ 母公司權益，≤0 為淨現金 🟢、≥100% 借的比本多 🔴；有息負債＝借款＋票券＋公司債＋租賃；資料＝最新一季資產負債表（排程 data/debt.json，沒有的檔讀估值時向 FinMind 補、快取 7 天）；金融股不適用。 `:'')+`<b>估值掃描</b>：""")

open(dst, 'w', encoding='utf-8').write(s)
print('ok')
