#!/usr/bin/env python3
"""2026-11-16 新增產業主題：itsvc「☁️ 資訊服務／軟體」10 檔（排在 net 網通後）。
依市值排序、備註「類別｜說明」（≤約 9 個中文字寬）。通路股（零壹、邁達特、大綜）也放（世杰 11/16 23:58 改決定）。
門檻例外（世杰指定）：宏碁資訊 6811（邊緣）、資通 2471（未達 100 億）。
用法：python3 patch_itsvc.py → data/themes_beta.json＋beta.html（唯讀預覽）；python3 patch_itsvc.py prod → data/themes.json
"""
import sys,json,re
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
S=json.load(open('data/summary.json',encoding='utf-8'));cap=lambda c:S['d'][c][0]*S['sh'][c]
w=lambda t:sum(1 if ord(c)>255 else .55 for c in t)
EXC={'6811','2471'}
G=[('itsvc','☁️ 資訊服務／軟體',['ACN','IBM'],[['6702','富士通'],['4307','野村總研']],[],
    [['6214','整合｜資服龍頭'],['8099','整合｜大同集團'],['2480','整合｜企業資訊'],['6183','軟體｜通關金流'],
     ['7765','資安｜中華電'],['3029','通路｜資安雲端'],['3147','整合｜伺服器'],['6112','通路｜雲端軟體'],['6811','整合｜宏碁集團'],['2471','軟體｜ERP金融']])]
d=json.load(open('data/themes.json',encoding='utf-8'));lines=open('data/themes.json',encoding='utf-8').read().split('\n')
used={c for t in d['themes'] if t['id'] not in {'fpg','hh','umc','asus','wal'} for c,_ in t['stocks']}
for i,nm,us,jp,kr,L in G:
    bad=[(r,round(cap(r[0])/1e8,1),w(r[1])) for r in L if (cap(r[0])<99.5e8 and r[0] not in EXC) or w(r[1])>8.6 or r[0] in used];assert not bad,bad
    L.sort(key=lambda r:-cap(r[0]));assert not any('"id": "%s"'%i in l for l in lines)
k=[n for n,l in enumerate(lines) if l.lstrip().startswith('{"id": "net"')][0]
def obj(i,nm,us,jp,kr,L):
    o={'id':i,'name':nm,'us':us,'jp':jp}
    if kr:o['kr']=kr
    o['stocks']=L;return '    '+json.dumps(o,ensure_ascii=False)+','
lines[k+1:k+1]=[obj(*g) for g in G]
out='\n'.join(lines);d=json.loads(out);print(len(d['themes']),[x['id'] for x in d['themes']])
for i,nm,us,jp,kr,L in G: print(nm,len(L),[(r[0],round(cap(r[0])/1e8,1),w(r[1])) for r in L])
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
v=re.search(r'<span style="opacity:.5">(v\d+[a-z])</span>',s).group(1)
rep('<span style="opacity:.5">%s</span>'%v,'<span style="opacity:.5">%s 資訊服務預覽</span>'%v)
s=s.replace('<title>','<title>[beta] ',1)
open('beta.html','w',encoding='utf-8').write(s);print('ok')
