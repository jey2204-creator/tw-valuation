#!/usr/bin/env python3
"""2026-11-18 台股主題補「對應美股」（方案 A）：4 個空白主題補同業、7 個單檔主題補到 2～3 檔。
APH 被動元件→連接器、ENTG 矽晶圓→半導體材料（各只放一處）。代號都在 us/data/all/ 查得到。
用法：python3 patch_usmap.py → data/themes_beta_usmap.json＋beta_usmap.html（唯讀預覽）；python3 patch_usmap.py prod → data/themes.json
"""
import sys,json,os
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
US={'icd':['QCOM','MPWR','SYNA'],'conn':['APH','TEL','CRDO'],'semimat':['ENTG','LIN','Q'],'brand':['DELL','HPQ'],
    'passive':['VSH','LFUS'],'wafer':['WOLF','COHR'],
    'probe':['FORM','COHU','TER'],'pcb':['TTMI','SANM'],'link':['ALAB','RMBS'],'thermal':['VRT','NVT'],
    'psu':['ETN','VRT','VICR'],'net':['ANET','CLS','CSCO'],'power':['GEV','HUBB','PWR']}
for u in {x for v in US.values() for x in v}:assert os.path.exists(f'us/data/all/{u}.json'),u
lines=open('data/themes.json',encoding='utf-8').read().split('\n');done=set()
for k,l in enumerate(lines):
    s=l.strip()
    if not s.startswith('{"id"'):continue
    t=json.loads(s.rstrip(','))
    if t['id'] not in US:continue
    n={}
    for a,b in t.items():   # us 放在 stocks 後面（跟其他主題同順序）；原本就有 us 的留在原位
        n[a]=US[t['id']] if a=='us' else b
        if a=='stocks' and 'us' not in t:n['us']=US[t['id']]
    lines[k]='    '+json.dumps(n,ensure_ascii=False)+(',' if s.endswith(',') else '');done.add(t['id'])
assert done==set(US),set(US)-done
out='\n'.join(lines);d=json.loads(out)
for t in d['themes']:
    if t['id'] in US:print(t['id'],t['name'],t['us'])
if prod:
    open('data/themes.json','w',encoding='utf-8').write(out);print('prod ok');sys.exit()
open('data/themes_beta_usmap.json','w',encoding='utf-8').write(out)
s=open('index.html',encoding='utf-8').read()
def rep(old,new):
    global s
    assert s.count(old)==1,(s.count(old),old[:60]);s=s.replace(old,new)
rep("fetch('data/themes.json?t='+Date.now());if(r.ok)BASE=","fetch('data/themes_beta_usmap.json?t='+Date.now());if(r.ok)BASE=")
rep("const cfgGet=()=>{const c=store.get('themeCfg')||{};return {order:c.order||[],hidden:c.hidden||[],themes:c.themes||{}}};",
    "const cfgGet=()=>({order:[],hidden:[],themes:{}});   // beta 預覽：只看預設")
rep("function cfgSave(c){store.set('themeCfg',c);applyCfg()}","function cfgSave(c){applyCfg()}   // beta 預覽：不存檔")
s=s.replace("localStorage.removeItem('themeCfg')","0").replace("store.set('themeCfg',","(()=>{})('themeCfg',")
rep('<span style="opacity:.5">v1117c</span>','<span style="opacity:.5">v1118 對應美股預覽</span>')
s=s.replace('<title>','<title>[beta] ',1)
open('beta_usmap.html','w',encoding='utf-8').write(s);print('ok')
