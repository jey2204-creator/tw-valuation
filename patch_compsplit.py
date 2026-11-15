#!/usr/bin/env python3
"""2026-11-16 零組件三主題：passive 被動元件 3→14、bmc＋link 合併成 link「BMC／傳輸 IC」4 檔（移除 <100 億的威鋒電子、創惟，bmc id 取消）、conn 連接器／線材 3→10。
市值≥100 億、依市值排序、備註「類別｜說明」（≤約 9 個中文字寬）。
用法：python3 patch_compsplit.py → data/themes_beta.json＋beta.html（唯讀預覽）；python3 patch_compsplit.py prod → data/themes.json
"""
import sys,json
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
S=json.load(open('data/summary.json',encoding='utf-8'));cap=lambda c:S['d'][c][0]*S['sh'][c]
w=lambda t:sum(1 if ord(c)>255 else .55 for c in t)
PA=[['2327','綜合｜電阻電容'],['2492','電容｜MLCC'],['3026','電容｜MLCC'],['3042','頻率｜石英元件'],['3090','通路｜被動元件'],['6173','電容｜MLCC／粉末'],['2472','電容｜鋁質電容'],
    ['2428','保護｜保護元件'],['3357','電感｜電感'],['8042','電容｜鋁質電容'],['2478','電阻｜晶片電阻'],['6449','電容｜固態電容'],['3624','電阻｜薄膜電阻'],['2375','電容｜鋁質電容']]
LK=[['5274','BMC｜龍頭'],['5269','傳輸｜高速介面'],['4919','BMC｜遠端管理'],['4966','傳輸｜高速介面']]
CN=[['3665','線材｜高速線材'],['3533','連接器｜CPU 插槽'],['3023','線材｜線束'],['6290','線材｜電源線'],['6197','線材｜高速連接線'],['3605','連接器｜綜合'],['2392','連接器｜綜合'],['3526','連接器｜伺服器'],['6190','線材｜綜合'],['6279','連接器｜車用端子']]
for L in(PA,LK,CN):
    assert all(cap(r[0])>=100e8 and w(r[1])<=8.6 for r in L),[(r,w(r[1])) for r in L if w(r[1])>8.6];L.sort(key=lambda r:-cap(r[0]))
lines=open('data/themes.json',encoding='utf-8').read().split('\n')
def idx(i):
    k=[n for n,l in enumerate(lines) if '"id": "%s"'%i in l];assert len(k)==1,i;return k[0]
def setst(i,rows,name=None):
    k=idx(i);t=json.loads(lines[k].strip().rstrip(','));assert len(rows)>len(t['stocks']) or i=='link'
    t['stocks']=rows
    if name:t['name']=name
    lines[k]='    '+json.dumps(t,ensure_ascii=False)+','
setst('passive',PA);setst('conn',CN);setst('link',LK,'🎛️ BMC／傳輸 IC')
del lines[idx('bmc')]
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
rep('<span style="opacity:.5">v1115o</span>','<span style="opacity:.5">v1116g 零組件預覽</span>')
s=s.replace('<title>','<title>[beta] ',1)
open('beta.html','w',encoding='utf-8').write(s);print('ok')
