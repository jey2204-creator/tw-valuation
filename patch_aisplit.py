#!/usr/bin/env python3
"""2026-11-16 AI 晶片補 ASIC／IP 4 檔＋聯電、世界（共 10）＋新主題 icd「IC 設計」7 檔（排在 ai 後）。
市值≥100 億、依市值排序、備註「類別｜說明」（≤約 9 個中文字寬）。
用法：python3 patch_aisplit.py → data/themes_beta.json＋beta.html（唯讀預覽）；python3 patch_aisplit.py prod → data/themes.json
"""
import sys,json
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
S=json.load(open('data/summary.json',encoding='utf-8'));cap=lambda c:S['d'][c][0]*S['sh'][c]
w=lambda t:sum(1 if ord(c)>255 else .55 for c in t)
AI=[['2330','代工｜先進製程'],['2454','設計｜手機／ASIC'],['3443','ASIC｜設計服務'],['3661','ASIC｜設計服務'],['3529','IP｜記憶體 IP'],['3035','ASIC｜設計服務'],['6643','IP｜高速介面'],['6533','IP｜處理器'],['2303','代工｜成熟製程'],['5347','代工｜8 吋成熟']]
IC=[['2379','網通｜網通 IC'],['3034','驅動｜驅動 IC'],['6415','電源｜電源管理'],['6526','網通｜光通訊 IC'],['8081','電源｜電源管理'],['6719','電源｜顯卡伺服器'],['6138','電源｜風扇驅動']]
for L in(AI,IC):
    assert all(cap(r[0])>=100e8 and w(r[1])<=8.6 for r in L),[(r,w(r[1])) for r in L];L.sort(key=lambda r:-cap(r[0]))
lines=open('data/themes.json',encoding='utf-8').read().split('\n')
i=[k for k,l in enumerate(lines) if '"id": "ai"' in l];assert len(i)==1 and not any('"id": "icd"' in l for l in lines);i=i[0]
t=json.loads(lines[i].strip().rstrip(','));assert {s[0] for s in t['stocks']}<={r[0] for r in AI};t['stocks']=AI
lines[i:i+1]=['    '+json.dumps(x,ensure_ascii=False)+',' for x in(t,{'id':'icd','name':'🧩 IC 設計','stocks':IC})]
out='\n'.join(lines);d=json.loads(out);print(len(d['themes']),[x['id'] for x in d['themes']])
if prod:
    open('data/themes.json','w',encoding='utf-8').write(out);print('prod ok');sys.exit()
open('data/themes_beta.json','w',encoding='utf-8').write(out)
s=open('index.html',encoding='utf-8').read()
def rep(old,new):
    global s
    assert s.count(old)==1,(s.count(old),old[:60]);s=s.replace(old,new)
rep("fetch('data/themes.json?t='+Date.now());if(r.ok)BASE=","fetch('data/themes_beta.json?t='+Date.now());if(r.ok)BASE=")
rep("const cfgGet=()=>{const c=store.get('themeCfg')||{};return {order:c.order||[],hidden:c.hidden||[],themes:c.themes||{}}};",
    "const cfgGet=()=>({order:[],hidden:[],themes:{}});   // beta 預覽：只看預設")
rep("function cfgSave(c){store.set('themeCfg',c);applyCfg()}","function cfgSave(c){applyCfg()}   // beta 預覽：不存檔")
s=s.replace("localStorage.removeItem('themeCfg')","0").replace("store.set('themeCfg',","(()=>{})('themeCfg',")
rep('<span style="opacity:.5">v1115o</span>','<span style="opacity:.5">v1116e AI 晶片／IC 設計預覽</span>')
s=s.replace('<title>','<title>[beta] ',1)
open('beta.html','w',encoding='utf-8').write(s);print('ok')
