#!/usr/bin/env python3
"""2026-11-16 記憶體拆兩個主題：mem「記憶體」（製造／IC 設計／模組，13 檔）＋ mempkg「記憶體封測／通路」（5 檔）。
成份股依市值排序（data/summary.json 收盤×股數），角色備註＝「類別｜說明」。
用法：python3 patch_memsplit.py → data/themes_beta.json＋beta.html（唯讀預覽：不套用也不寫回手機 themeCfg）
      python3 patch_memsplit.py prod → 寫回 data/themes.json
"""
import sys,json
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
S=json.load(open('data/summary.json',encoding='utf-8'));cap=lambda c:S['d'][c][0]*S['sh'][c]
MEM=[['2408','製造｜DRAM'],['2344','製造｜利基 DRAM'],['6770','製造｜記憶體代工'],['2337','製造｜NOR Flash'],
     ['8299','設計｜NAND 控制'],['6531','設計｜利基記憶體'],['3006','設計｜利基 DRAM'],['5351','設計｜利基 DRAM'],
     ['3260','模組｜記憶體模組'],['2451','模組｜工控比重高'],['5289','模組｜工控記憶體'],['4967','模組｜記憶體模組'],['8271','模組｜記憶體模組']]
PKG=[['6239','封測｜封測龍頭'],['8150','封測｜記憶體／驅動'],['8131','封測｜南亞科體系'],['8110','封測｜華邦電體系'],['8112','通路｜記憶體通路']]
for L in(MEM,PKG):
    assert all(cap(r[0])>=100e8 for r in L);L.sort(key=lambda r:-cap(r[0]))
lines=open('data/themes.json',encoding='utf-8').read().split('\n')
i=[k for k,l in enumerate(lines) if '"id": "mem"' in l];assert len(i)==1 and not any('"id": "mempkg"' in l for l in lines);i=i[0]
t=json.loads(lines[i].strip().rstrip(','));t['stocks']=MEM
lines[i]='    '+json.dumps(t,ensure_ascii=False)+','
lines.insert(i+1,'    '+json.dumps({'id':'mempkg','name':'📀 記憶體封測／通路','stocks':PKG},ensure_ascii=False)+',')
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
rep('<span style="opacity:.5">v1115o</span>','<span style="opacity:.5">v1116b 記憶體拆分預覽</span>')
s=s.replace('<title>','<title>[beta] ',1)
open('beta.html','w',encoding='utf-8').write(s);print('ok')
