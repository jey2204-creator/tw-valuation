#!/usr/bin/env python3
"""2026-11-16 電力 4→9、無塵室／廠務 3→9、低軌衛星 5→8（兆赫與網通重複放、台揚未達門檻但保留）、新主題 semimat「半導體材料」4（排在 wafer 後）。
市值≥100 億、依市值排序、備註「類別｜說明」（≤約 9 個中文字寬）。
用法：python3 patch_lastsplit.py → data/themes_beta.json＋beta.html（唯讀預覽）；python3 patch_lastsplit.py prod → data/themes.json
"""
import sys,json
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
S=json.load(open('data/summary.json',encoding='utf-8'));cap=lambda c:S['d'][c][0]*S['sh'][c]
w=lambda t:sum(1 if ord(c)>255 else .55 for c in t)
KEEP={'2314'}
T={'power':[['1519','重電｜變壓器'],['1504','重電｜馬達'],['1605','電纜｜電線電纜'],['1503','重電｜綜合'],['1513','重電｜開關設備'],['2371','重電｜變壓器'],['1609','電纜｜電線電纜'],['1514','重電｜配電盤'],['1608','電纜｜電線電纜']],
   'fab':[['2404','無塵室｜工程'],['6139','無塵室｜工程'],['5536','機電｜無塵室機電'],['6196','廠務｜設備代理'],['6691','機電｜無塵室機電'],['6944','水處理｜工程'],['4770','化學｜氟素設備'],['6613','化學｜供應系統'],['6667','廠務｜供應系統']],
   'leo':[['2313','PCB｜衛星板'],['3105','代工｜砷化鎵'],['3491','元件｜微波元件'],['6285','終端｜衛星終端'],['8086','元件｜功率放大器'],['4916','系統｜航太電腦'],['2485','終端｜衛星設備'],['2314','元件｜微波通訊']]}
MAT=[['5434','通路｜材料／廠務'],['4749','材料｜特用化學'],['1785','材料｜靶材'],['3010','通路｜材料通路']]
lines=open('data/themes.json',encoding='utf-8').read().split('\n')
def chk(L):
    bad=[(r,round(cap(r[0])/1e8,1),w(r[1])) for r in L if (cap(r[0])<99.5e8 and r[0] not in KEEP) or w(r[1])>8.6];assert not bad,bad
    L.sort(key=lambda r:-cap(r[0]))
for i,L in T.items():
    chk(L);k=[n for n,l in enumerate(lines) if '"id": "%s"'%i in l];assert len(k)==1;k=k[0]
    t=json.loads(lines[k].strip().rstrip(','));assert {s[0] for s in t['stocks']}<{r[0] for r in L},i
    t['stocks']=L;lines[k]='    '+json.dumps(t,ensure_ascii=False)+(',' if lines[k].rstrip().endswith(',') else '')
chk(MAT);assert not any('"id": "semimat"' in l for l in lines)
k=[n for n,l in enumerate(lines) if '"id": "wafer"' in l][0]
lines.insert(k+1,'    '+json.dumps({'id':'semimat','name':'🧪 半導體材料','stocks':MAT},ensure_ascii=False)+',')
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
rep('<span style="opacity:.5">v1115o</span>','<span style="opacity:.5">v1116j 電力廠務衛星預覽</span>')
s=s.replace('<title>','<title>[beta] ',1)
open('beta.html','w',encoding='utf-8').write(s);print('ok')
