#!/usr/bin/env python3
"""2026-11-21 美股站新增「🏛️ 費城半導體」指數主題（30 檔，us/data/sox.json 權重表）＋兩個產業主題：
🏭 晶圓代工（TSM INTC GFS TSEM）、🧩 類比／IC 設計（TXN ADI QCOM NXPI MPWR MCHP ON LSCC SITM）；ASML、TER 進先進封裝／設備、MTSI 進矽光子／CPO。
費半是「指數主題」：成份股可跟產業主題重疊，主題頁多權重（股票欄連點：權重 → 市值 → 薪酬）、權重加權漲跌與上漲家數；
個股頁的「← 主題」與上下檔優先用產業主題，從費半頁點進去才用費半。
用法：python3 patch_sox.py → us/index_test.html（ASML／TER／MTSI 在瀏覽器裡改掛到正式主題）
     python3 patch_sox.py prod → 改 us/index.html＋us/fetch_us.py（之後要 dispatch update_us 抓 ASML TER MTSI，index.json 的主題才會換）
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
s=open('us/index.html',encoding='utf-8').read()
def rep(old,new,n=1):
    global s
    assert s.count(old)==n,(s.count(old),old[:70]);s=s.replace(old,new)
# 主題代號與預設順序：費半放最前面（總覽），兩個新產業主題接在先進封裝後面
rep("'🔌 電力':'power'};","'🔌 電力':'power','🏭 晶圓代工':'foundry','🧩 類比／IC 設計':'icd'};")
rep("const DEF_ORDER=['pcb','ai','cpo','pkg',","const DEF_ORDER=['sox','pcb','ai','cpo','pkg','foundry','icd',")
rep("SMCI:'AI 伺服器',","TSM:'晶圓代工龍頭',INTC:'CPU＋晶圓代工',GFS:'成熟製程代工',TSEM:'特殊製程代工',TXN:'類比 IC 龍頭',ADI:'類比／訊號鏈',QCOM:'手機 SoC／數據機',NXPI:'車用 MCU',MPWR:'電源管理 IC',MCHP:'MCU／類比',ON:'功率／SiC',LSCC:'低功耗 FPGA',SITM:'MEMS 時脈',ASML:'微影（EUV）',TER:'測試機',MTSI:'類比／光通訊晶片',\n  SMCI:'AI 伺服器',")
# 權重表
rep("let BASE=[],THEMES=[],ORDER_IDS=[],ALLM={};","let BASE=[],THEMES=[],ORDER_IDS=[],ALLM={};\n// 費城半導體指數（data/sox.json，手動維護）：w＝{代號:權重%}。指數主題 idx:true，成份股可跟產業主題重疊\nlet SOX={w:{}};const soxW=id=>SOX.w[id];")
rep("  const r=id=>{const i=DEF_ORDER.indexOf(id);return i<0?99:i};return g.sort(",
    "  const sw=Object.keys(SOX.w).sort((a,b)=>SOX.w[b]-SOX.w[a]);if(sw.length)g.push({id:'sox',name:'🏛️ 費城半導體',stocks:sw.map(u=>[u,ROLE[u]||'']),tw:[],dem:false,idx:true});\n  const r=id=>{const i=DEF_ORDER.indexOf(id);return i<0?99:i};return g.sort(")
rep("  BASE=baseThemes();applyCfg();syStat();syncRun();","  try{const r=await fetch('data/sox.json?t='+Date.now());if(r.ok){const j=await r.json();if(j&&j.w)SOX=j}}catch(e){}\n  BASE=baseThemes();applyCfg();syStat();syncRun();")
# 個股頁的主題：剛看的主題 → 第一個產業主題 → 指數主題
rep("const themeOfStock=id=>THEMES.find(t=>t.id===LAST_T&&t.stocks.some(x=>x[0]===id))||THEMES.find(t=>t.stocks.some(x=>x[0]===id))||null;",
    "const themeOfStock=id=>THEMES.find(t=>t.id===LAST_T&&t.stocks.some(x=>x[0]===id))||THEMES.find(t=>!t.idx&&t.stocks.some(x=>x[0]===id))||THEMES.find(t=>t.stocks.some(x=>x[0]===id))||null;")
# 台股沒有同名主題的不給「台股同主題 →」
rep("(!t.custom&&t.id!=='cloud'?`<a class=\"all\"","(!t.custom&&t.id!=='cloud'&&t.id!=='foundry'?`<a class=\"all\"")
# 主題頁摘要：指數主題加權重集中度、權重加權本月至今、上漲家數＋中位數提醒
rep("    (lqs.length>1?`<br>最新季 ${lqs[0]}～${lqs[lqs.length-1]}：",
    "    (t.idx?(()=>{const w=ids.map(soxW),top=w.slice().sort((a,b)=>b-a).slice(0,5).reduce((a,b)=>a+b,0);let sw=0,sm2=0,up=0,nn=0;\n"
    "      ids.forEach(i=>{const m=(ST[i]||{}).mtd,c=stockOf(i).chg;if(m!=null&&soxW(i)){sw+=soxW(i);sm2+=soxW(i)*m}if(c!=null){nn++;if(c>0)up++}});const wm=sw?sm2/sw:null;\n"
    "      return `<br>指數權重（Nasdaq ${SOX.asof?+SOX.asof.slice(5,7)+'/'+ +SOX.asof.slice(8):''}）：前 5 大合計 <b>${fmt(top,1)}%</b>・權重加權本月至今 ${wm==null?'—':`<b class=\"${sgc(wm)}\">${pct(wm,1)}</b>`}・最新交易日上漲 <b>${up}</b>／${nn} 檔`+\n"
    "        `<br><span style=\"color:var(--warm)\">⚠️ 30 檔混了 AI、類比、設備、代工不同循環，上面的本益比／PEG 中位數只當參考；估值請回各產業主題看。</span>`})():'')+\n"
    "    (lqs.length>1?`<br>最新季 ${lqs[0]}～${lqs[lqs.length-1]}：")
rep("  if(LAST_TS!==tid){TS=tsGet(tid);LAST_TS=tid}loadPx(t);","  if(LAST_TS!==tid){TS=tsGet(tid);LAST_TS=tid}if(t.idx&&!TS)TS='w:-1';loadPx(t);")
rep("（本益比連點：本益比 → EPS年增 → PEG；股票連點：市值 → 薪酬中位數）。","（本益比連點：本益比 → EPS年增 → PEG；股票連點：${t.idx?'權重 → ':''}市值 → 薪酬中位數）。${t.idx?`權重＝Nasdaq 公布的指數權重（${SOX.asof||''}，手動更新）。`:''}")
# 主題表：權重排序與顯示
rep("const TSORT={cap:capM,","const TSORT={w:id=>soxW(id),cap:capM,")
rep("const TCAP=['cap:-1','sal:-1',''],TCAPL={cap:'市值',sal:'薪酬中位'};","const TCAP=['cap:-1','sal:-1',''],TCAPL={cap:'市值',sal:'薪酬中位',w:'權重'},TCAPX=['w:-1','cap:-1','sal:-1'];")
rep("else if(nk==='cap'){const i=TCAP.indexOf(TS);TS=TCAP[i<0?0:(i+1)%TCAP.length]}","else if(nk==='cap'){const C=t.idx?TCAPX:TCAP,i=C.indexOf(TS);TS=C[i<0?0:(i+1)%C.length]}")
# 緊湊：第二行顯示權重（依市值／薪酬排序時照舊）；名次 # 也給權重排序
rep("sv=k==='sal'&&sal(id,'med')!=null?'薪'+salK(sal(id,'med')).replace('≈',''):cm?capT(cm).replace('≈',''):'';",
    "sv=k==='sal'&&sal(id,'med')!=null?'薪'+salK(sal(id,'med')).replace('≈',''):t.idx&&k!=='cap'&&soxW(id)!=null?fmt(soxW(id),2)+'%':cm?capT(cm).replace('≈',''):'';")
# 指數主題依市值／薪酬排序時名次會到兩位數：短名再縮一點，表格才不會超出手機寬度（依權重排序本身就是名次，不另外標 #）
rep("function tTable(t){const el=$('tList'),[k,dir]=TS.split(':');","function tTable(t){const el=$('tList'),[k,dir]=TS.split(':');el.classList.toggle('ix',!!t.idx&&(k==='cap'||k==='sal'));")
rep("body.dense .lst .sub{font-size:10.5px}","body.dense #tList.ix td.sk .cd{max-width:2.4em}body.dense .lst .sub{font-size:10.5px}")
# 完整：市值前面多一個權重
rep("${k==='cap'&&capM(id)!=null?`<span class=\"rk\">#${++RK}</span>`:''}<span class=\"nmw\"><span class=\"nm\">${id}</span><span class=\"cd\" title=\"${esc(s.name||'')}\">${esc(shortOf(s))}</span></span>${cm?",
    "${k==='cap'&&capM(id)!=null?`<span class=\"rk\">#${++RK}</span>`:''}<span class=\"nmw\"><span class=\"nm\">${id}</span><span class=\"cd\" title=\"${esc(s.name||'')}\">${esc(shortOf(s))}</span></span>${t.idx&&soxW(id)!=null?`<span class=\"cap\">權重 ${fmt(soxW(id),2)}%</span>`:''}${cm?")
if prod:
    open('us/index.html','w',encoding='utf-8').write(s)
    f=open('us/fetch_us.py',encoding='utf-8').read()
    def frep(old,new):
        global f
        assert f.count(old)==1,(f.count(old),old[:60]);f=f.replace(old,new)
    frep('("CAMT", ""), ("LRCX", "C"), ("FORM", "")],','("CAMT", ""), ("LRCX", "C"), ("FORM", ""), ("ASML", ""), ("TER", "")],')
    frep('("CIEN", ""), ("AAOI", "")],','("CIEN", ""), ("AAOI", ""), ("MTSI", "")],')
    a=f.index('    # 暫放：ASML、TER');b=f.index(']\n',f.index('("🏛️ 費半補檔"'))
    f=f[:a]+f[b:]
    open('us/fetch_us.py','w',encoding='utf-8').write(f);print('prod ok');sys.exit()
# 測試頁：ASML／TER／MTSI 在 index.json 還掛在「費半補檔」，載入後改掛到正式主題（對應台股跟該主題其他檔一樣）
rep("function baseThemes(){const g=[];","function baseThemes(){const g=[];const _o={ASML:'🧱 先進封裝／設備',TER:'🧱 先進封裝／設備',MTSI:'💡 矽光子／CPO'};IDX.forEach(s=>{const o=_o[s.id];if(o){const b=IDX.find(x=>x.theme===o);s.theme=o;if(b)s.tw=b.tw}});")
s=s.replace('<title>','<title>[測試] ',1)
open('us/index_test.html','w',encoding='utf-8').write(s);print('test ok')
