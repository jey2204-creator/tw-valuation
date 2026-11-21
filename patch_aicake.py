#!/usr/bin/env python3
"""2026-11-21 AI 五層蛋糕補追蹤：8 檔分進主題
  CEG、VST → 🔌 電力；CRWV、ORCL → ☁️ 雲端資本支出（D 旗標：個股頁有 CapEx 圖）；PLTR、NOW、CRM、APP → 新主題 🧠 AI 應用軟體（id aisw，台股無對應）
  首頁「四大雲端資本支出」合計圖固定只算 MSFT GOOGL AMZN META，不受 D 旗標新增影響。
用法：python3 patch_aicake.py → us/index_test.html（8 檔在 index.json 還在「🧺 追蹤暫放」，載入後在瀏覽器裡改掛）
     python3 patch_aicake.py prod → 改 us/index.html＋us/fetch_us.py（之後 dispatch update_us 抓這 8 檔，index.json 的主題／D 旗標才會換）
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
s=open('us/index.html',encoding='utf-8').read()
def rep(old,new,n=1):
    global s
    assert s.count(old)==n,(s.count(old),old[:70]);s=s.replace(old,new)
rep("'🧩 類比／IC 設計':'icd'};","'🧩 類比／IC 設計':'icd','🧠 AI 應用軟體':'aisw'};")
rep("'semimat','leo','cloud'];","'semimat','leo','cloud','aisw'];")
rep("  SMCI:'AI 伺服器',","  CEG:'核電',VST:'電力供應（天然氣＋核電）',CRWV:'GPU 雲（Neocloud）',ORCL:'OCI 雲＋資料庫',PLTR:'AI 決策平台',NOW:'企業工作流程',CRM:'CRM＋AI 代理',APP:'AI 廣告投放',\n  SMCI:'AI 伺服器',")
# 四大雲端合計圖：固定四檔（雲端主題多了 CRWV／ORCL，也有 D 旗標）
rep("  const ids=IDX.filter(s=>s.dem).map(s=>s.id);if(!ids.length)return;",
    "  const ids=['MSFT','GOOGL','AMZN','META'].filter(id=>IDX.some(s=>s.id===id));if(!ids.length)return;   // 只算四大；雲端主題其他 D 旗標股（CRWV、ORCL）不併進來")
if prod:
    open('us/index.html','w',encoding='utf-8').write(s)
    f=open('us/fetch_us.py',encoding='utf-8').read()
    def frep(old,new):
        global f
        assert f.count(old)==1,(f.count(old),old[:60]);f=f.replace(old,new)
    frep('("🔌 電力", [("GEV", "")],','("🔌 電力", [("GEV", ""), ("CEG", ""), ("VST", "")],')
    frep('("☁️ 雲端資本支出", [("MSFT", "D"), ("GOOGL", "D"), ("AMZN", "D"), ("META", "D")], []),',
         '("☁️ 雲端資本支出", [("MSFT", "D"), ("GOOGL", "D"), ("AMZN", "D"), ("META", "D"), ("CRWV", "D"), ("ORCL", "D")], []),')
    a=f.index('    # 2026-11-21 AI 五層蛋糕補追蹤');b=f.index(']\n',f.index('("🧺 追蹤暫放"'))
    f=f[:a]+'''    ("🧠 AI 應用軟體", [("PLTR", ""), ("NOW", ""), ("CRM", ""), ("APP", "")], []),
'''+f[b:]
    open('us/fetch_us.py','w',encoding='utf-8').write(f);print('prod ok');sys.exit()
# 測試頁：index.json 還是「🧺 追蹤暫放」→ 載入後改掛；CRWV／ORCL 個股頁當 D 旗標（CapEx 圖）
rep("function baseThemes(){const g=[];",
    "function baseThemes(){const g=[];const _o={CEG:'🔌 電力',VST:'🔌 電力',CRWV:'☁️ 雲端資本支出',ORCL:'☁️ 雲端資本支出',PLTR:'🧠 AI 應用軟體',NOW:'🧠 AI 應用軟體',CRM:'🧠 AI 應用軟體',APP:'🧠 AI 應用軟體'};"
    "IDX.forEach(s=>{const o=_o[s.id];if(o){const b=IDX.find(x=>x.theme===o&&!_o[x.id]);s.theme=o;s.tw=b?b.tw:[];if(o.startsWith('☁️'))s.dem=true}});"
    "const _w=IDX.filter(s=>_o[s.id]);IDX=IDX.filter(s=>!_o[s.id]).concat(_w);")
s=s.replace('D.demand','(D.demand||_DEM.has(D.id))')
rep("let IDX=[],","const _DEM=new Set(['CRWV','ORCL']);let IDX=[],")
s=s.replace('<title>','<title>[測試] ',1)
open('us/index_test.html','w',encoding='utf-8').write(s);print('test ok')
