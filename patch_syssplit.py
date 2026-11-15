#!/usr/bin/env python3
"""2026-11-16 矽光子／CPO 6→17（含大立光、玉晶光、采鈺，備註標手機為主）、網通 4→10（啟碁與低軌衛星重複放）、伺服器 7→9、品牌／板卡 3→6、新主題 ipc「工業電腦」5（排在 brand 後）。
市值≥100 億、依市值排序、備註 ≤約 9 個中文字寬。
用法：python3 patch_syssplit.py → data/themes_beta.json＋beta.html（唯讀預覽）；python3 patch_syssplit.py prod → data/themes.json
"""
import sys,json
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
S=json.load(open('data/summary.json',encoding='utf-8'));cap=lambda c:S['d'][c][0]*S['sh'][c]
w=lambda t:sum(1 if ord(c)>255 else .55 for c in t)
T={'cpo':[['3081','磊晶｜雷射'],['6442','被動｜光纖元件'],['2455','磊晶｜光電子'],['4979','模組｜光收發'],['3450','封裝｜光通訊'],['3163','被動｜光纖元件'],['4991','晶片｜光通訊代工'],['3363','被動｜光纖／CPO'],
          ['6451','封裝｜光收發模組'],['4971','磊晶｜磊晶'],['3234','元件｜光收發'],['4977','模組｜光收發'],['4908','模組｜光收發'],['6426','元件｜濾光片'],['3008','手機鏡頭為主'],['3406','手機鏡頭為主'],['6789','手機感測為主']],
   'net':[['2345','交換器｜資料中心'],['6285','網通｜衛星終端'],['3596','寬頻｜寬頻設備'],['5388','寬頻｜寬頻設備'],['4906','無線｜無線網通'],['3380','交換器｜網通設備'],['3704','網通｜網通設備'],['6245','網安｜硬體平台'],['2332','品牌｜網通品牌'],['2485','寬頻｜衛星設備']],
   'server':[['2317','代工｜伺服器'],['2382','代工｜伺服器'],['6669','代工｜伺服器'],['3231','代工｜伺服器'],['4938','代工｜綜合'],['2356','代工｜伺服器'],['2324','代工｜綜合'],['3706','品牌｜伺服器'],['7711','板卡｜伺服器板']],
   'brand':[['2357','品牌｜伺服器'],['2376','板卡｜伺服器'],['2377','板卡｜伺服器'],['2353','品牌｜電腦'],['3515','板卡｜主機板'],['2465','板卡｜顯卡工作站']]}
IPC=[['2395','工控｜龍頭'],['3005','工控｜強固電腦'],['6414','工控｜系統整合'],['6579','工控｜嵌入式'],['8050','工控｜嵌入式']]
lines=open('data/themes.json',encoding='utf-8').read().split('\n')
def chk(L):
    bad=[(r,round(cap(r[0])/1e8,1),w(r[1])) for r in L if cap(r[0])<99.5e8 or w(r[1])>8.6];assert not bad,bad
    L.sort(key=lambda r:-cap(r[0]))
for i,L in T.items():
    chk(L);k=[n for n,l in enumerate(lines) if '"id": "%s"'%i in l];assert len(k)==1;k=k[0]
    t=json.loads(lines[k].strip().rstrip(','));assert {s[0] for s in t['stocks']}<{r[0] for r in L},i
    t['stocks']=L;lines[k]='    '+json.dumps(t,ensure_ascii=False)+','
chk(IPC);assert not any('"id": "ipc"' in l for l in lines)
k=[n for n,l in enumerate(lines) if '"id": "brand"' in l][0]
lines.insert(k+1,'    '+json.dumps({'id':'ipc','name':'🏭 工業電腦','stocks':IPC},ensure_ascii=False)+',')
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
rep('<span style="opacity:.5">v1115o</span>','<span style="opacity:.5">v1116i 系統端預覽</span>')
s=s.replace('<title>','<title>[beta] ',1)
open('beta.html','w',encoding='utf-8').write(s);print('ok')
