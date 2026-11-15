#!/usr/bin/env python3
"""2026-11-16「先進封裝／設備」拆三個主題：equip 半導體設備（14）→ pkg 封測（9，沿用舊 id）→ probe 測試介面（4）。
成份股依市值排序（data/summary.json 收盤×股數）、市值≥100 億、角色備註「類別｜說明」（≤約 9 個中文字寬）。
美／日／韓對應也跟著拆。
用法：python3 patch_pkgsplit.py → data/themes_beta.json＋beta.html（唯讀預覽）；python3 patch_pkgsplit.py prod → data/themes.json
"""
import sys,json
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
S=json.load(open('data/summary.json',encoding='utf-8'));cap=lambda c:S['d'][c][0]*S['sh'][c]
w=lambda t:sum(1 if ord(c)>255 else .55 for c in t)
EQ=[['2360','量測｜測試設備'],['6187','封裝｜封裝設備'],['3131','濕製程｜設備'],['7734','封裝｜除泡設備'],['2467','封裝｜貼合烘烤'],['3583','濕製程｜再生晶圓'],
    ['3680','載具｜光罩盒'],['7751','封裝｜點膠植片'],['3413','代工｜設備代工'],['6640','封裝｜黏晶挑揀'],['8027','封裝｜雷射電漿'],['6937','前段｜薄膜設備'],['5443','封裝｜檢測研磨'],['3587','檢測｜材料分析']]
PK=[['3711','封測｜龍頭'],['2449','測試｜晶圓／成品'],['3374','封裝｜晶圓級'],['6147','封測｜驅動 IC'],['3264','測試｜晶圓測試'],['6257','封測｜綜合'],['2441','封測｜力成體系'],['6271','封裝｜影像感測'],['3265','封測｜凸塊／測試']]
PB=[['6223','探針卡'],['6515','測試座'],['6510','探針卡｜測試板'],['6683','測試載板']]
for L in(EQ,PK,PB):
    assert all(cap(r[0])>=100e8 and w(r[1])<=8.6 for r in L);L.sort(key=lambda r:-cap(r[0]))
lines=open('data/themes.json',encoding='utf-8').read().split('\n')
i=[k for k,l in enumerate(lines) if '"id": "pkg"' in l];assert len(i)==1 and not any('"id": "equip"' in l or '"id": "probe"' in l for l in lines);i=i[0]
t=json.loads(lines[i].strip().rstrip(','))
assert {s[0] for s in t['stocks']}<={r[0] for r in EQ+PK+PB}
kr={k[0]:k for k in t.get('kr',[])};jp={k[0]:k for k in t.get('jp',[])}
equip={'id':'equip','name':'⚙️ 半導體設備','us':['AMAT','KLAC','ONTO','CAMT','LRCX'],'jp':[jp[k] for k in('8035','6146','6920','7735','6525','7729')],'kr':[kr[k] for k in('042700','039030','240810','036930','403870')],'stocks':EQ}
pkg={'id':'pkg','name':'🧱 封測','us':['AMKR'],'stocks':PK}
probe={'id':'probe','name':'🔬 測試介面','us':['FORM'],'jp':[jp['6857']],'kr':[kr[k] for k in('095340','058470','089030')],'stocks':PB}
lines[i:i+1]=['    '+json.dumps(x,ensure_ascii=False)+',' for x in(equip,pkg,probe)]
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
rep('<span style="opacity:.5">v1115o</span>','<span style="opacity:.5">v1116c 封裝設備拆分預覽</span>')
s=s.replace('<title>','<title>[beta] ',1)
open('beta.html','w',encoding='utf-8').write(s);print('ok')
