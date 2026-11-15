#!/usr/bin/env python3
"""2026-11-16 PCB 鏈拆四個主題：cufoil「PCB 材料」9 → ccl「銅箔基板／載板」8（新 id）→ pcbeq「PCB 設備」8（新 id）→ pcb「PCB」16（板廠，華通與低軌衛星重複放）。
市值≥100 億、依市值排序、備註「類別｜說明」（≤約 9 個中文字寬）；日／韓對應跟著拆。
用法：python3 patch_pcbsplit.py → data/themes_beta.json＋beta.html（唯讀預覽）；python3 patch_pcbsplit.py prod → data/themes.json
"""
import sys,json
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
S=json.load(open('data/summary.json',encoding='utf-8'));cap=lambda c:S['d'][c][0]*S['sh'][c]
w=lambda t:sum(1 if ord(c)>255 else .55 for c in t)
MAT=[['1303','一條龍｜本業塑化'],['1802','玻纖｜玻纖布'],['8358','銅箔｜高階銅箔'],['1815','玻纖｜紗／布'],['1717','化學｜乾膜光阻'],['5475','玻纖｜玻纖布'],['5340','玻纖｜玻纖布'],['4722','化學｜樹脂'],['4989','銅箔｜銅箔']]
CCL=[['2383','CCL｜銅箔基板'],['3037','載板｜ABF'],['8046','載板｜ABF'],['3189','載板｜IC 載板'],['6274','CCL｜銅箔基板'],['6213','CCL｜銅箔基板'],['8039','CCL｜軟性基板'],['6672','CCL｜銅箔基板']]
EQ=[['3167','設備｜鑽孔量測'],['8021','耗材｜鑽針'],['3030','檢測｜檢測設備'],['3563','檢測｜光學檢測'],['2493','設備｜濕製程'],['6664','設備｜烘烤'],['6438','設備｜自動化'],['3455','檢測｜光學檢測']]
PCB=[['2368','硬板｜伺服器'],['4958','綜合｜PCB 龍頭'],['3044','硬板｜伺服器車用'],['2313','硬板｜衛星／HDI'],['6191','硬板｜綜合'],['3715','硬板｜車用伺服器'],['5469','硬板｜筆電伺服器'],['2367','硬板｜HDI'],
     ['2355','硬板｜車用'],['6269','軟板｜手機'],['2316','硬板｜綜合'],['8155','硬板｜伺服器'],['5439','硬板｜伺服器網通'],['4927','硬板｜綜合'],['8213','硬板｜面板筆電'],['6153','軟板｜手機']]
for L in(MAT,CCL,EQ,PCB):
    assert all(cap(r[0])>=100e8 and w(r[1])<=8.6 for r in L),[(r,w(r[1])) for r in L if w(r[1])>8.6];L.sort(key=lambda r:-cap(r[0]))
lines=open('data/themes.json',encoding='utf-8').read().split('\n')
def idx(i):
    k=[n for n,l in enumerate(lines) if '"id": "%s"'%i in l];assert len(k)==1,i;return k[0]
assert not any('"id": "ccl"' in l or '"id": "pcbeq"' in l for l in lines)
ic,ip=idx('cufoil'),idx('pcb');assert ip==ic+1
tc=json.loads(lines[ic].strip().rstrip(','));tp=json.loads(lines[ip].strip().rstrip(','))
assert {s[0] for s in tc['stocks']+tp['stocks']}<={r[0] for r in MAT+CCL+PCB}
jp={k[0]:k for k in tp.get('jp',[])};kr={k[0]:k for k in tp.get('kr',[])}
mat={'id':'cufoil','name':'🧵 PCB 材料','jp':[jp['3110'],jp['2802']],'stocks':MAT}
ccl={'id':'ccl','name':'📗 銅箔基板／載板','jp':[jp['4062']],'kr':[kr[k] for k in('011070','353200','222800','007810')],'stocks':CCL}
eq={'id':'pcbeq','name':'🛠️ PCB 設備','stocks':EQ}
pcb={'id':'pcb','name':'🟩 PCB','us':tp.get('us',[]),'kr':[kr['007660']],'stocks':PCB}
lines[ic:ip+1]=['    '+json.dumps(x,ensure_ascii=False)+',' for x in(mat,ccl,eq,pcb)]
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
rep('<span style="opacity:.5">v1115o</span>','<span style="opacity:.5">v1116f PCB 拆分預覽</span>')
s=s.replace('<title>','<title>[beta] ',1)
open('beta.html','w',encoding='utf-8').write(s);print('ok')
