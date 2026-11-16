#!/usr/bin/env python3
"""2026-11-16 新增集團主題第二批：umc「聯電集團」8、asus「華碩／和碩集團」5、wal「華新麗華集團」9（排在 hh 後）。
集團主題與產業主題本來就會重複（例：南亞科同時在記憶體），這是刻意的。
市值≥100 億、依市值排序、備註「類別｜說明」（≤約 9 個中文字寬）。
用法：python3 patch_group2.py → data/themes_beta.json＋beta.html（唯讀預覽）；python3 patch_group2.py prod → data/themes.json
"""
import sys,json
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
S=json.load(open('data/summary.json',encoding='utf-8'));cap=lambda c:S['d'][c][0]*S['sh'][c]
w=lambda t:sum(1 if ord(c)>255 else .55 for c in t)
G=[('umc','🔷 聯電集團',[['2303','代工｜成熟製程'],['3037','PCB｜ABF載板'],['3034','設計｜驅動IC'],['6147','封測｜驅動IC'],['3035','設計｜ASIC'],['3227','設計｜感測IC'],['2363','設計｜MEMS'],['3014','設計｜PC晶片']]),
   ('asus','💻 華碩／和碩集團',[['2357','品牌｜PC伺服器'],['3189','PCB｜ABF載板'],['4938','EMS｜組裝'],['5269','設計｜高速介面'],['3515','品牌｜主機板']]),
   ('wal','🔌 華新麗華集團',[['2344','記憶體｜利基型'],['1605','電纜｜不鏽鋼'],['2492','被動｜MLCC'],['4919','設計｜MCU／BMC'],['6191','PCB｜伺服器板'],['5469','PCB｜伺服器板'],['6116','面板｜中小尺寸'],['8110','封測｜記憶體'],['3049','面板｜觸控模組']])]
d=json.load(open('data/themes.json',encoding='utf-8'));lines=open('data/themes.json',encoding='utf-8').read().split('\n')
for i,nm,L in G:
    bad=[(r,round(cap(r[0])/1e8,1),w(r[1])) for r in L if cap(r[0])<99.5e8 or w(r[1])>8.6];assert not bad,bad
    L.sort(key=lambda r:-cap(r[0]));assert not any('"id": "%s"'%i in l for l in lines)
k=max(n for n,l in enumerate(lines) if l.strip().startswith('{"id"'))
assert not lines[k].rstrip().endswith(',');lines[k]=lines[k].rstrip()+','
new=['    '+json.dumps({'id':i,'name':nm,'us':[],'stocks':L},ensure_ascii=False) for i,nm,L in G]
lines[k+1:k+1]=[x+',' for x in new[:-1]]+[new[-1]]
out='\n'.join(lines);d=json.loads(out);print(len(d['themes']),[x['id'] for x in d['themes']][-4:])
for i,nm,L in G: print(nm,[(r[0],round(cap(r[0])/1e8)) for r in L])
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
import re
v=re.search(r'<span style="opacity:.5">(v\d+[a-z])</span>',s).group(1)
rep('<span style="opacity:.5">%s</span>'%v,'<span style="opacity:.5">%s 集團主題預覽</span>'%v)
s=s.replace('<title>','<title>[beta] ',1)
open('beta.html','w',encoding='utf-8').write(s);print('ok')
