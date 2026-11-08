#!/usr/bin/env python3
"""2026-11-08 估值掃描方案②：小卡雙分位＋循環股自動換尺。
- 每檔決定「主尺」main：循環股＝淨值比（PB），其他＝本益比（PE）。小卡主尺顯示倍數＋分位、副尺只顯示分位（變淡）；紅框＝主尺分位 ≥80%。
- 河流選擇加「自動」（預設）：循環股畫淨值比河流、其他畫本益比；仍可強制本益比／淨值比。
- 循環股判定＝手動名單（data/<id>.json cyclical、手機裡的 cycCfg 覆寫）或自動：
    A 近 6 年近四季 EPS 曾從高峰回落 ≥50%、或曾有近四季虧損（本益比缺月）
    B EPS 下滑時本益比反而上升：近四季 EPS 與月本益比 Pearson r < -0.3（實測 2330 +0.14、2344 -0.56、6488 -0.66）
    C 證交所產業屬景氣循環（航運／鋼鐵／塑膠／水泥／玻璃／造紙／橡膠／油電燃氣／化學／紡織／光電）
  A+B 成立、或 (A 或 B)+C 成立 → 循環股；放大卡寫出理由，可一鍵「標為／取消循環股」（存手機，覆寫自動判定）。
- 排序改為 貴／便宜（主尺分位）＋ PE貴／PB貴；篩選改為 貴≥80%／便宜≤20%／PE≥80%／PB≥80%。
- 放大卡加「近四季 ROE ≈ EPS ÷ 每股淨值」，<5% 提醒淨值比低可能是價值陷阱。
用法：python3 patch_val2.py scan.html beta_scan.html
"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:90])
    s = s.replace(old, new)

# ---- 控制列 ----
rep('''<span class="rv" style="display:contents" hidden><button data-r="pe" aria-pressed="true">本益比</button><button data-r="pb">淨值比</button></span>''',
    '''<span class="rv" style="display:contents" hidden><button data-r="auto" aria-pressed="true" title="循環股畫淨值比、其他畫本益比">自動</button><button data-r="pe">本益比</button><button data-r="pb">淨值比</button></span>''')
rep('''<button data-k="peh" class="vs" hidden title="本益比歷史分位 高→低">PE貴</button><button data-k="pel" class="vs" hidden title="本益比歷史分位 低→高">PE便宜</button><button data-k="pbh" class="vs" hidden title="淨值比歷史分位 高→低">PB貴</button><button data-k="pbl" class="vs" hidden title="淨值比歷史分位 低→高">PB便宜</button>''',
    '''<button data-k="mh" class="vs" hidden title="主尺分位 高→低（循環股用淨值比、其他用本益比）">貴</button><button data-k="ml" class="vs" hidden title="主尺分位 低→高">便宜</button><button data-k="peh" class="vs" hidden title="本益比歷史分位 高→低">PE貴</button><button data-k="pbh" class="vs" hidden title="淨值比歷史分位 高→低">PB貴</button>''')
rep('''<button class="f vs" data-vf="pe80" hidden title="本益比分位 ≥80%（歷史偏貴）">PE≥80%</button><button class="f vs" data-vf="pe20" hidden title="本益比分位 ≤20%（歷史偏便宜）">PE≤20%</button><button class="f vs" data-vf="pb80" hidden title="淨值比分位 ≥80%">PB≥80%</button><button class="f vs" data-vf="pb20" hidden title="淨值比分位 ≤20%">PB≤20%</button>''',
    '''<button class="f vs" data-vf="m80" hidden title="主尺分位 ≥80%（歷史偏貴）">貴≥80%</button><button class="f vs" data-vf="m20" hidden title="主尺分位 ≤20%（歷史偏便宜）">便宜≤20%</button><button class="f vs" data-vf="pe80" hidden title="本益比分位 ≥80%">PE≥80%</button><button class="f vs" data-vf="pb80" hidden title="淨值比分位 ≥80%">PB≥80%</button>''')

# ---- 狀態 ----
rep('''let MODE='k',RV='pe',SK_K='chg',SK_V='peh';const VSK=new Set(['peh','pel','pbh','pbl']),VF={pe80:false,pe20:false,pb80:false,pb20:false};''',
    '''let MODE='k',RV='auto',SK_K='chg',SK_V='mh';const VSK=new Set(['mh','ml','peh','pbh']),VF={m80:false,m20:false,pe80:false,pb80:false};
const CYC_IND=new Set(['航運業','鋼鐵工業','塑膠工業','水泥工業','玻璃陶瓷','造紙工業','橡膠工業','油電燃氣業','化學工業','紡織纖維','光電業']);let INDOF={};
const cycCfg=()=>store.get('cycCfg')||{add:[],del:[]};
// 循環股判定：手動（覆寫）→ data 檔 cyclical → 自動（A 獲利大起大落、B 本益比與淨值比反向、C 景氣循環產業）
function cycJudge(c,riv,flag){const cfg=cycCfg();if(cfg.del.includes(c))return {cyc:false,why:'手動取消'};if(cfg.add.includes(c))return {cyc:true,why:'手動標記'};if(flag)return {cyc:true,why:'網站名單'};
  // A：近四季 EPS 曾從高峰回落 ≥50%、或曾虧損（本益比缺月）——成長股一路往上不算
  const e=riv.map(r=>r[2]);let peak=0,dd=0,loss=0;e.forEach(v=>{if(v==null||v<=0){loss++;dd=1;return}peak=Math.max(peak,v);if(peak)dd=Math.max(dd,1-v/peak)});const A=loss>=3||dd>=0.5;
  // B：EPS 下滑時本益比反而上升（EPS 與本益比負相關 r<-0.3）＝本益比被 EPS 波動主導；成長股兩者不相關或同向
  const pr=riv.filter(r=>r[2]>0&&r[4]>0);let B=false,rr=null;if(pr.length>=24){const x=pr.map(r=>r[2]),y=pr.map(r=>r[4]),mx=x.reduce((a,b)=>a+b)/x.length,my=y.reduce((a,b)=>a+b)/y.length;let sxy=0,sx=0,sy=0;x.forEach((v,i)=>{sxy+=(v-mx)*(y[i]-my);sx+=(v-mx)**2;sy+=(y[i]-my)**2});rr=sx&&sy?sxy/Math.sqrt(sx*sy):null;B=rr!=null&&rr<-0.3}
  const C=CYC_IND.has(INDOF[c]);const cyc=(A&&B)||((A||B)&&C);
  const why=[A?(loss>=3?`近 6 年有 ${loss} 個月近四季虧損`:`近四季 EPS 曾從高峰回落 ${Math.round(dd*100)}%`):null,B?`EPS 下滑時本益比反而上升（r=${rr.toFixed(2)}）`:null,C?`${INDOF[c]}屬景氣循環產業`:null].filter(Boolean).join('、');
  return {cyc,why:why||'EPS 沒有大幅回落、本益比不被 EPS 波動主導',A,B,C}}
function cycToggle(c){const cfg=cycCfg(),v=VAL[c];if(!v)return;const now=v.cyc;cfg.add=cfg.add.filter(x=>x!==c);cfg.del=cfg.del.filter(x=>x!==c);(now?cfg.del:cfg.add).push(c);store.set('cycCfg',cfg);
  const j=cycJudge(c,v.riv,v.flag);v.cyc=j.cyc;v.why=j.why;v.main=v.cyc?'pb':'pe';v.mainPct=v.cyc?v.pbPct:v.pePct;fillSheet();const top=scrollY;renderV();scrollTo(0,top)}
const mainRv=v=>RV==='auto'?(v&&v.cyc?'pb':'pe'):RV;''')
# INDOF 建表
rep('''  L.forEach(([c,n,m,i])=>{NAME[c]=n;MKT[c]=m;(IND[i]=IND[i]||[]).push(c)});''',
    '''  L.forEach(([c,n,m,i])=>{NAME[c]=n;MKT[c]=m;INDOF[c]=i;(IND[i]=IND[i]||[]).push(c)});''')
rep('''const rv=localStorage.getItem('scanRv');if(rv==='pb')RV='pb'}''', '''const rv=localStorage.getItem('scanRv');if(rv==='pb'||rv==='pe')RV=rv}''')
# valGet：cyc 改用 cycJudge，加 main／mainPct／roe
rep('''  return VAL[c]={c,riv,cyc,src,px,pe,pb,pem:vBands(pes),pbm:vBands(pbs),pePct:pe?vPct(pes,pe):null,pbPct:pb?vPct(pbs,pb):null,yrs:(riv.length/12).toFixed(1)}}''',
    '''  const j=cycJudge(c,riv,cyc),pePct=pe?vPct(pes,pe):null,pbPct=pb?vPct(pbs,pb):null,roe=last[2]!=null&&last[3]>0?+(last[2]/last[3]*100).toFixed(1):null;
  return VAL[c]={c,riv,flag:cyc,cyc:j.cyc,why:j.why,src,px,pe,pb,pem:vBands(pes),pbm:vBands(pbs),pePct,pbPct,main:j.cyc?'pb':'pe',mainPct:j.cyc?pbPct:pePct,roe,yrs:(riv.length/12).toFixed(1)}}''')
# 小卡數字：主尺在前（倍數＋分位），副尺只分位變淡
rep('''  return one('PE',v.pe,v.pePct,RV==='pe')+one('PB',v.pb,v.pbPct,RV==='pb')}''',
    '''  const m=v.main==='pb';return m?one('PB',v.pb,v.pbPct,true)+one('PE',v.pe,v.pePct,false):one('PE',v.pe,v.pePct,true)+one('PB',v.pb,v.pbPct,false)}''')
# 排序／篩選
rep('''function rowsV(){let R=ROWS.filter(r=>{const v=VAL[r.c];if(!VF.pe80&&!VF.pe20&&!VF.pb80&&!VF.pb20)return true;if(!v)return false;
    return (!VF.pe80||(v.pePct!=null&&v.pePct>=80))&&(!VF.pe20||(v.pePct!=null&&v.pePct<=20))&&(!VF.pb80||(v.pbPct!=null&&v.pbPct>=80))&&(!VF.pb20||(v.pbPct!=null&&v.pbPct<=20))});
  const ck=CHGK(),g=(r,k)=>{const v=VAL[r.c];return v&&v[k]!=null?v[k]:null};
  const key={li:r=>-r.li,chg:r=>(r[ck]??-9),peh:r=>g(r,'pePct')??-1,pel:r=>{const p=g(r,'pePct');return p==null?-1:100-p},pbh:r=>g(r,'pbPct')??-1,pbl:r=>{const p=g(r,'pbPct');return p==null?-1:100-p}}[sortK]||(r=>g(r,'pePct')??-1);''',
    '''function rowsV(){let R=ROWS.filter(r=>{const v=VAL[r.c];if(!VF.m80&&!VF.m20&&!VF.pe80&&!VF.pb80)return true;if(!v)return false;
    return (!VF.m80||(v.mainPct!=null&&v.mainPct>=80))&&(!VF.m20||(v.mainPct!=null&&v.mainPct<=20))&&(!VF.pe80||(v.pePct!=null&&v.pePct>=80))&&(!VF.pb80||(v.pbPct!=null&&v.pbPct>=80))});
  const ck=CHGK(),g=(r,k)=>{const v=VAL[r.c];return v&&v[k]!=null?v[k]:null};
  const key={li:r=>-r.li,chg:r=>(r[ck]??-9),mh:r=>g(r,'mainPct')??-1,ml:r=>{const p=g(r,'mainPct');return p==null?-1:100-p},peh:r=>g(r,'pePct')??-1,pbh:r=>g(r,'pbPct')??-1}[sortK]||(r=>g(r,'mainPct')??-1);''')
rep('''  $('cnt').innerHTML=all?`<b>${rows().length}</b>／${all} 檔${wait?`・已讀 <b>${n}</b>${bad?`・${bad} 檔讀不到`:''}・<span class="miss">${wait} 檔${VERR?'停止':'讀取中'}</span>${more}`:bad?`・${bad} 檔讀不到`:''}${VERR?`・<span class="miss">${esc(VERR)}</span>`:''}・PE≥80% <b class="up">${cntP('pePct',p=>p>=80)}</b> 檔・PE≤20% <b class="dn">${cntP('pePct',p=>p<=20)}</b> 檔・PB≥80% <b class="up">${cntP('pbPct',p=>p>=80)}</b> 檔・點小卡放大`:'';''',
    '''  const nc=ROWS.filter(r=>VAL[r.c]&&VAL[r.c].cyc).length;
  $('cnt').innerHTML=all?`<b>${rows().length}</b>／${all} 檔${wait?`・已讀 <b>${n}</b>${bad?`・${bad} 檔讀不到`:''}・<span class="miss">${wait} 檔${VERR?'停止':'讀取中'}</span>${more}`:bad?`・${bad} 檔讀不到`:''}${VERR?`・<span class="miss">${esc(VERR)}</span>`:''}・貴≥80% <b class="up">${cntP('mainPct',p=>p>=80)}</b> 檔・便宜≤20% <b class="dn">${cntP('mainPct',p=>p<=20)}</b> 檔${nc?`・循環股 <b>${nc}</b> 檔（用淨值比）`:''}・點小卡放大`:'';''')
# renderV：紅框＝主尺、循 標籤帶理由、畫哪張河流
rep('''return `<article class="km${v?'':' vld'}${v&&(RV==='pe'?v.pePct:v.pbPct)>=80?' hot':''}" data-i="${i}" data-c="${esc(r.c)}" role="button" tabindex="0">
    <div class="km-h"><span class="rk">${i+1}</span><b>${esc(r.n)}</b><span class="cd">${esc(r.c)}</span>${v&&v.cyc?'<span class="tg cy" style="margin-left:auto" title="循環股：EPS 高峰時本益比偏低、谷底時偏高，請看淨值比">循</span>':''}${nbadge(r.c)}</div>''',
    '''return `<article class="km${v?'':' vld'}${v&&v.mainPct>=80?' hot':''}" data-i="${i}" data-c="${esc(r.c)}" role="button" tabindex="0">
    <div class="km-h"><span class="rk">${i+1}</span><b>${esc(r.n)}</b><span class="cd">${esc(r.c)}</span>${v&&v.cyc?`<span class="tg cy" style="margin-left:auto" title="循環股（${esc(v.why)}）：以淨值比為主尺">循</span>`:''}${nbadge(r.c)}</div>''')
rep('''if(!cv.dataset.done&&v){drawRiver(cv,v,{mini:true,kind:RV});cv.dataset.done=1}''', '''if(!cv.dataset.done&&v){drawRiver(cv,v,{mini:true,kind:mainRv(v)});cv.dataset.done=1}''')
rep('''if(VAL[c]&&cv.clientWidth){drawRiver(cv,VAL[c],{mini:true,kind:RV});cv.dataset.done=1}}''', '''if(VAL[c]&&cv.clientWidth){drawRiver(cv,VAL[c],{mini:true,kind:mainRv(VAL[c])});cv.dataset.done=1}}''')
# 頁尾
rep('''  $('foot').innerHTML=`<b>估值掃描</b>：小卡＝近 3 年的<b>${RV==='pe'?'本益比':'淨值比'}河流圖</b>''',
    '''  $('foot').innerHTML=`<b>估值掃描</b>：小卡＝近 3 年的<b>${RV==='auto'?'本益比河流圖（循環股自動改畫淨值比）':RV==='pe'?'本益比河流圖':'淨值比河流圖'}</b>''')
rep('''<b>循</b>＝循環股（目前只標 2344、6488）：EPS 谷底時本益比會偏高，請以淨值比為主。排序 <b>PE貴</b>／<b>PB貴</b>＝分位高→低，<b>PE便宜</b>／<b>PB便宜</b>＝低→高；篩選可疊加。''',
    '''每檔有一把<b>主尺</b>：一般股＝本益比、<b>循環股＝淨值比</b>（EPS 谷底時本益比反而最高，拿本益比排會把最便宜的循環股排成最貴）；小卡第一個數字＝主尺（倍數＋分位），第二個淡色＝另一把尺的分位；紅框＝主尺分位 ≥80%。<b>循</b>＝循環股，自動判定：A 近 6 年近四季 EPS 曾從高峰回落 ≥50% 或曾虧損、B EPS 下滑時本益比反而上升（兩者負相關）、C 證交所產業屬景氣循環（航運／鋼鐵／塑膠／水泥／玻璃／造紙／橡膠／油電燃氣／化學／紡織／光電）——A＋B 或 (A 或 B)＋C 成立；放大卡會寫理由，可一鍵改標（存在手機，覆寫自動判定）。排序 <b>貴</b>／<b>便宜</b>＝主尺分位高→低／低→高，<b>PE貴</b>／<b>PB貴</b>＝固定用本益比／淨值比；篩選可疊加。⚠ 淨值比低不一定便宜：淨值持續被虧損侵蝕的公司（面板、記憶體慘業期）PB 分位低也可能是價值陷阱，放大卡的「近四季 ROE」<5% 會提醒。''')
# 放大卡：主尺在前、理由、ROE、改標鈕
rep('''    ${v?`${line('本益比',v.pe,v.pePct,v.pem)}<canvas class="sh-cv rv" id="shPe"></canvas><div class="leg" style="margin-bottom:6px"><span>色帶＝近四季 EPS × ${v.pem.join('／')} 倍</span></div>
    ${line('淨值比',v.pb,v.pbPct,v.pbm)}<canvas class="sh-cv rv" id="shPb"></canvas><div class="leg"><span>色帶＝每股淨值 × ${v.pbm.join('／')} 倍</span>${S&&S[4]!=null?`<span>殖利率 ${S[4]}%</span>`:''}${S&&S[5]!=null?`<span>營收年增 ${S[5]}%</span>`:''}</div>
    ${v.cyc?'<div class="sh-t" style="color:var(--muted)">循環股：EPS 高峰時本益比會偏低、谷底時偏高，請以淨值比河流圖為主</div>':''}<div class="sh-t" style="color:var(--muted);font-size:11px">資料：''',
    '''    ${v?(()=>{const PE=`${line('本益比',v.pe,v.pePct,v.pem)}<canvas class="sh-cv rv" id="shPe"></canvas><div class="leg" style="margin-bottom:6px"><span>色帶＝近四季 EPS × ${v.pem.join('／')} 倍</span></div>`,
      PB=`${line('淨值比',v.pb,v.pbPct,v.pbm)}<canvas class="sh-cv rv" id="shPb"></canvas><div class="leg" style="margin-bottom:6px"><span>色帶＝每股淨值 × ${v.pbm.join('／')} 倍</span>${S&&S[4]!=null?`<span>殖利率 ${S[4]}%</span>`:''}${S&&S[5]!=null?`<span>營收年增 ${S[5]}%</span>`:''}</div>`;
      return (v.cyc?PB+PE:PE+PB)+`<div class="sh-t" style="color:var(--muted)">${v.cyc?`<b style="color:var(--warm)">循環股</b>（${esc(v.why)}）：主尺用淨值比，EPS 高峰時本益比會偏低、谷底時偏高`:`一般股（${esc(v.why)}）：主尺用本益比`}・近四季 ROE ≈ <b class="${v.roe!=null&&v.roe<5?'dn':''}">${v.roe==null?'—':v.roe+'%'}</b>${v.roe!=null&&v.roe<5?'（淨值報酬低，淨值比低可能是價值陷阱）':''} <button id="cycBtn" style="color:var(--accent);font-weight:700">${v.cyc?'取消循環股':'標為循環股'}</button></div>`})()+`<div class="sh-t" style="color:var(--muted);font-size:11px">資料：''')
rep('''  if(v){drawRiver($('shPe'),v,{kind:'pe'});drawRiver($('shPb'),v,{kind:'pb'})}''',
    '''  if(v){drawRiver($('shPe'),v,{kind:'pe'});drawRiver($('shPb'),v,{kind:'pb'});$('cycBtn').onclick=()=>cycToggle(r.c)}''')
open(dst, 'w', encoding='utf-8').write(s)
print('ok', len(s))
