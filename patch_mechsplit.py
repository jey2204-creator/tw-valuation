#!/usr/bin/env python3
"""2026-11-16 散熱 6→10、電源 5→9、BBU 3→4、機殼／滑軌 4→7。
市值≥100 億（例外：世杰指定保留尼得科超眾 6230、全漢 3015）、依市值排序、備註「類別｜說明」（≤約 9 個中文字寬）。
用法：python3 patch_mechsplit.py → data/themes_beta.json＋beta.html（唯讀預覽）；python3 patch_mechsplit.py prod → data/themes.json
"""
import sys,json
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
S=json.load(open('data/summary.json',encoding='utf-8'));cap=lambda c:S['d'][c][0]*S['sh'][c]
w=lambda t:sum(1 if ord(c)>255 else .55 for c in t)
KEEP={'6230','3015'}
T={'thermal':[['3017','模組｜水冷板'],['3653','均熱片｜龍頭'],['6805','水冷｜快接頭'],['8996','水冷｜熱交換器'],['3324','模組｜水冷'],['2486','均熱片｜散熱片'],['2421','風扇｜散熱風扇'],['6831','模組｜散熱模組'],['6125','水冷｜液冷機櫃'],['6230','模組｜散熱模組']],
   'psu':[['2308','電源｜龍頭'],['2301','電源｜伺服器'],['6409','UPS｜逆變器'],['6282','電源｜伺服器'],['3617','UPS｜不斷電'],['6412','電源｜供應器'],['5309','UPS｜不斷電'],['8109','電源｜轉換器'],['3015','電源｜供應器']],
   'bbu':[['6781','BBU｜電池模組'],['6121','電池｜模組龍頭'],['3211','BBU｜電池模組'],['4931','BBU｜電池模組']],
   'chassis':[['2059','滑軌｜伺服器'],['2474','機殼｜筆電手機'],['8210','機殼｜伺服器'],['2354','機殼｜機殼散熱'],['3693','機殼｜伺服器儲存'],['6584','滑軌｜伺服器'],['3013','機殼｜伺服器']]}
lines=open('data/themes.json',encoding='utf-8').read().split('\n')
for i,L in T.items():
    bad=[(r,round(cap(r[0])/1e8,1),w(r[1])) for r in L if (cap(r[0])<99.5e8 and r[0] not in KEEP) or w(r[1])>8.6];assert not bad,bad
    L.sort(key=lambda r:-cap(r[0]))
    k=[n for n,l in enumerate(lines) if '"id": "%s"'%i in l];assert len(k)==1;k=k[0]
    t=json.loads(lines[k].strip().rstrip(','));assert {s[0] for s in t['stocks']}<{r[0] for r in L},i
    t['stocks']=L;lines[k]='    '+json.dumps(t,ensure_ascii=False)+','
out='\n'.join(lines);d=json.loads(out);print(len(d['themes']))
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
rep('<span style="opacity:.5">v1115o</span>','<span style="opacity:.5">v1116h 散熱電源預覽</span>')
s=s.replace('<title>','<title>[beta] ',1)
open('beta.html','w',encoding='utf-8').write(s);print('ok')
