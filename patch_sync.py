#!/usr/bin/env python3
"""2026-11-21 batch17 美股站產業主題跟台股站同步（台股 data/themes.json 當唯一主檔）
台股端（Q2／Q3）：themes.json 的 us 欄補美股、新增 🏭 晶圓代工主題（2330 2303 5347 6770 ↔ TSM INTC GFS TSEM）
美股端：內建主題＝台股主題裡有 us 欄的（同 id、同名、同順序；台股站在同一個瀏覽器排過的順序／改過的成份股也跟著），
        後面接美股獨有：🏛️ 費城半導體（指數）、☁️ 雲端資本支出（需求層）。對應台股＝台股主題的全部成份股（名稱讀 ../data/list.json）。
        美股自訂主題固定排最上面、可拖曳；內建主題 🔒 不能拖（要排就到台股站排）。
用法：python3 patch_sync.py      → data/themes_beta_sync.json＋beta_sync.html（台股測試頁）＋us/index_test.html（美股測試頁，讀 beta 對照表）
     python3 patch_sync.py prod → data/themes.json＋us/index.html＋us/fetch_us.py（每日追蹤名單改由 themes.json 產生）
"""
import sys,json,os
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
# ---------- 台股 themes.json ----------
ADD={'power':['CEG','VST'],'equip':['ASML'],'cpo':['MTSI'],'icd':['TXN','ADI','NXPI','MCHP','ON','LSCC','SITM'],
     'itsvc':['PLTR','NOW','CRM','APP'],'ai':['CRWV']}
FOUNDRY={"id":"foundry","name":"🏭 晶圓代工","us":["TSM","INTC","GFS","TSEM"],
  "ov":[["usTSM","晶圓代工龍頭"],["usINTC","CPU＋晶圓代工"],["usGFS","成熟製程代工"],["usTSEM","特殊製程代工"]],
  "stocks":[["2330","代工｜先進製程"],["2303","代工｜成熟製程"],["5347","代工｜8 吋成熟"],["6770","代工｜記憶體／邏輯"]]}
lines=open('data/themes.json',encoding='utf-8').read().split('\n');done=set();ai_at=None
for k,l in enumerate(lines):
    s=l.strip()
    if not s.startswith('{"id"'):continue
    t=json.loads(s.rstrip(','))
    if t['id']=='ai':ai_at=k
    if t['id']=='foundry':sys.exit('themes.json 已經有 foundry，不要重跑')
    if t['id'] not in ADD:continue
    t['us']=t.get('us',[])+[u for u in ADD[t['id']] if u not in t.get('us',[])]
    lines[k]='    '+json.dumps(t,ensure_ascii=False)+(',' if s.endswith(',') else '');done.add(t['id'])
assert done==set(ADD),set(ADD)-done
lines.insert(ai_at+1,'    '+json.dumps(FOUNDRY,ensure_ascii=False)+',')
out='\n'.join(lines);TH=json.loads(out)['themes']
for u in {x for t in TH for x in t.get('us',[])}:assert os.path.exists(f'us/data/all/{u}.json') or os.path.exists(f'us/data/{u}.json'),u
# ---------- 美股前端 ----------
s=open('us/index.html',encoding='utf-8').read()
def rep(old,new,n=1):
    global s
    assert s.count(old)==n,(s.count(old),old[:70]);s=s.replace(old,new)
TWF='../data/themes.json' if prod else '../data/themes_beta_sync.json'
rep("let SOX={w:{}};","// 產業主題跟台股站同步（batch17）：TWT＝台股 themes.json（讀不到就退回舊版：依 index.json 分組）、TWN＝台股代號→名稱（../data/list.json）\nlet TWT=null,TWN={};const TWF='"+TWF+"';\nlet SOX={w:{}};")
rep("  BASE=baseThemes();applyCfg();syStat();syncRun();",
    "  try{const [a,b]=await Promise.all([fetch(TWF+'?t='+Date.now()).then(r=>r.ok?r.json():null),fetch('../data/list.json?d='+new Date().toISOString().slice(0,10)).then(r=>r.ok?r.json():null)]);\n"
    "    if(b)b.forEach(r=>TWN[r[0]]=r[1]);if(a&&Array.isArray(a.themes))TWT=a.themes}catch(e){}\n"
    "  BASE=baseThemes();applyCfg();syStat();syncRun();")
rep("function baseThemes(){const g=[];IDX.forEach(s=>{const id=TID[s.theme];",
    "function baseThemes(){if(!TWT)return baseThemesOld();\n"
    "  let tc={};try{tc=JSON.parse(localStorage.getItem('themeCfg'))||{}}catch(e){}   // 台股站在同一個瀏覽器的設定：排序、改過的成份股、自訂主題\n"
    "  const tth=tc.themes||{},bm=Object.fromEntries(TWT.map(t=>[t.id,t])),g=[];\n"
    "  [...(Array.isArray(tc.order)?tc.order:[]),...TWT.map(t=>t.id),...Object.keys(tth)].filter((v,i,a)=>a.indexOf(v)===i).forEach(id=>{\n"
    "    const src=tth[id]||bm[id];if(!src||!Array.isArray(src.us)||!src.us.length)return;\n"
    "    const ov=Object.fromEntries((src.ov||(bm[id]||{}).ov||[]).filter(x=>/^us/.test(x[0])).map(x=>[x[0].slice(2),x[1]]));\n"
    "    g.push({id,name:src.name||(bm[id]||{}).name||id,stocks:src.us.map(u=>[u,ROLE[u]||ov[u]||'']),tw:(src.stocks||[]).map(x=>[x[0],TWN[x[0]]||x[0]]),dem:false})});\n"
    "  // 美股獨有（台股沒有對應主題）：放最後\n"
    "  const sw=Object.keys(SOX.w).sort((a,b)=>SOX.w[b]-SOX.w[a]);if(sw.length)g.push({id:'sox',name:'🏛️ 費城半導體',stocks:sw.map(u=>[u,ROLE[u]||'']),tw:[],dem:false,idx:true,uso:true});\n"
    "  g.push({id:'cloud',name:'☁️ 雲端資本支出',stocks:['MSFT','GOOGL','AMZN','META','ORCL'].map(u=>[u,ROLE[u]||'']),tw:[],dem:true,uso:true});\n"
    "  // 每檔的「本籍」主題＝第一個有它的產業主題：個股頁對應台股、搜尋分組用（同一檔可以同時在好幾個主題）\n"
    "  const hm={};g.forEach(t=>{if(!t.idx)t.stocks.forEach(([u])=>{if(!hm[u])hm[u]=t})});\n"
    "  Object.keys(TID).forEach(k=>delete TID[k]);g.forEach(t=>TID[t.name]=t.id);\n"
    "  IDX.forEach(x=>{const t=hm[x.id];if(t){x.theme=t.name;x.tw=t.tw}else x.theme='其他'});\n"
    "  return g}\n"
    "function baseThemesOld(){const g=[];IDX.forEach(s=>{const id=TID[s.theme];")
rep("  const ids=[...c.order,...BASE.map(t=>t.id),...Object.keys(c.themes)].filter((v,i,a)=>a.indexOf(v)===i&&(bm[v]||c.themes[v]));",
    "  // 同步模式：美股自訂主題排最上面（照自己拖的順序），內建主題照台股站順序\n"
    "  const ids=(TWT?[...[...c.order,...Object.keys(c.themes)].filter(i=>!bm[i]&&c.themes[i]),...BASE.map(t=>t.id)]:[...c.order,...BASE.map(t=>t.id),...Object.keys(c.themes)]).filter((v,i,a)=>a.indexOf(v)===i&&(bm[v]||c.themes[v]));")
# 編輯頁：內建主題鎖順序
rep('<span class="drag" aria-hidden="true">⠿</span></div>`}).join(\'\');',
    '${TWT&&!t.custom?\'<span class="lk" title="順序跟台股站：要調整請到台股站排">🔒</span>\':\'<span class="drag" aria-hidden="true">⠿</span>\'}</div>`}).join(\'\');\n'
    '  $(\'oNote\').hidden=!TWT;')
rep('  <div class="panel" id="olist"></div>','  <p class="foot" id="oNote" hidden>🔒 內建主題跟台股站同步：主題、順序、成份股都照台股站（到台股站排序或改「對應美股」，這裡隔次打開就跟著變）。自訂主題固定排在最上面，可以按住 ⠿ 拖曳。</p>\n  <div class="panel" id="olist"></div>')
rep(".tlt tr:last-child td{border-bottom:0}",".tlt tr:last-child td{border-bottom:0}\n#olist .lk{flex:none;width:28px;text-align:center;font-size:13px;opacity:.55}")
# 台股同主題 →：美股獨有主題沒有
rep("(!t.custom&&t.id!=='cloud'&&t.id!=='foundry'?","(!t.custom&&!t.uso&&t.id!=='cloud'&&(TWT||t.id!=='foundry')?")
rep("const al=$('twAll');al.hidden=!!t.custom||t.id==='cloud';","const al=$('twAll');al.hidden=!!t.custom||!!t.uso||t.id==='cloud';")
# 個股頁「← 主題」與上下檔：剛看的主題 → 內建產業主題 → 自訂主題 → 指數主題（自訂主題排最上面後，不要搶走本籍）
rep("const themeOfStock=id=>THEMES.find(t=>t.id===LAST_T&&t.stocks.some(x=>x[0]===id))||THEMES.find(t=>!t.idx&&t.stocks.some(x=>x[0]===id))||",
    "const themeOfStock=id=>THEMES.find(t=>t.id===LAST_T&&t.stocks.some(x=>x[0]===id))||THEMES.find(t=>!t.idx&&!t.custom&&t.stocks.some(x=>x[0]===id))||THEMES.find(t=>!t.idx&&t.stocks.some(x=>x[0]===id))||")
# 個股頁對應台股：跟本籍主題（台股站）一致
rep("    D=await loadAny(id);await injectFlash(D);","    D=await loadAny(id);await injectFlash(D);if(TWT){const x=IDX.find(z=>z.id===D.id);if(x&&x.tw)D.tw=x.tw}")
rep("  SMCI:'AI 伺服器',","  ACN:'IT 顧問',IBM:'混合雲＋顧問',CSCO:'企業網通',DELL:'AI 伺服器＋PC',HPQ:'PC／印表機',COHU:'測試分選機',NVT:'機櫃／液冷',VICR:'48V 電源模組',RMBS:'記憶體介面晶片',SYNA:'人機介面 IC',\n"
    "  HUBB:'電網設備',PWR:'電網工程',ROK:'工業自動化',ISRG:'手術機器人',LMT:'軍工龍頭',RTX:'飛彈／引擎',AVAV:'軍用無人機',KTOS:'無人機／靶機',\n"
    "  JPM:'綜合金控',BAC:'商業銀行',MS:'投資銀行／財管',WFC:'商業銀行',USB:'區域銀行',DHI:'住宅建商',LEN:'住宅建商',\n  SMCI:'AI 伺服器',")
if prod:
    open('data/themes.json','w',encoding='utf-8').write(out)
    open('us/index.html','w',encoding='utf-8').write(s)
    f=open('us/fetch_us.py',encoding='utf-8').read()
    old='CFG = {t: dict(theme=th, flags=f, tw=tw, cn=CN.get(t, "")) for th, items, tw in THEMES for t, f in items}'
    assert f.count(old)==1
    f=f.replace(old,'''# 2026-11-21 batch17：追蹤名單與主題改由台股 data/themes.json 產生（有 us 欄的主題；一檔的本籍＝第一個出現的主題、對應台股＝該主題全部成份股），
# 再加美股獨有的雲端資本支出；上面的 THEMES 只在讀不到 themes.json 時備用。旗標 C＝循環股、D＝需求層（個股頁 CapEx 圖）
FLAGS = {"WOLF": "C", "VSH": "C", "AMAT": "C", "LRCX": "C", "MU": "C", "SNDK": "C",
         "MSFT": "D", "GOOGL": "D", "AMZN": "D", "META": "D", "ORCL": "D", "CRWV": "D"}
US_ONLY = [("☁️ 雲端資本支出", ["MSFT", "GOOGL", "AMZN", "META", "ORCL"])]


def _sync_themes():
    root = Path(__file__).resolve().parent.parent / "data"
    th = json.loads((root / "themes.json").read_text("utf-8"))["themes"]
    try:
        nm = {r[0]: r[1] for r in json.loads((root / "list.json").read_text("utf-8"))}
    except Exception:
        nm = {}
    out, seen = [], set()
    for t in th:
        us = [u for u in t.get("us") or [] if u not in seen]
        if not us:
            continue
        seen.update(us)
        out.append((t["name"], [(u, FLAGS.get(u, "")) for u in us], [(c, nm.get(c, c)) for c, *_ in t["stocks"]]))
    for name, us in US_ONLY:
        us = [u for u in us if u not in seen]
        seen.update(us)
        if us:
            out.append((name, [(u, FLAGS.get(u, "")) for u in us], []))
    return out


try:
    THEMES = _sync_themes()
except Exception as e:   # 讀不到台股 themes.json：用上面寫死的舊清單
    print("themes.json 讀取失敗，改用內建清單：", e, file=sys.stderr)
'''+old)
    open('us/fetch_us.py','w',encoding='utf-8').write(f);print('prod ok');sys.exit()
open('data/themes_beta_sync.json','w',encoding='utf-8').write(out)
tw=open('index.html',encoding='utf-8').read()
assert tw.count("fetch('data/themes.json?t='")==1
tw=tw.replace("fetch('data/themes.json?t='","fetch('data/themes_beta_sync.json?t='").replace('<title>','<title>[測試] ',1)
open('beta_sync.html','w',encoding='utf-8').write(tw)
s=s.replace('<title>','<title>[測試] ',1)
open('us/index_test.html','w',encoding='utf-8').write(s)
for t in TH:
    if t['id'] in ADD or t['id']=='foundry':print(t['id'],t['name'],t['us'])
print('test ok')
