#!/usr/bin/env python3
"""2026-11-16 新增產業主題：robot「🤖 機器人」10 檔、defense「🚀 軍工／無人機」7 檔（排在 ipc 工業電腦後）。
市值≥100 億（和大 100 億壓線）、依市值排序、備註「類別｜說明」（≤約 9 個中文字寬）；不重複放已在其他產業主題的股票。
用法：python3 patch_robodef.py → data/themes_beta.json＋beta.html（唯讀預覽）；python3 patch_robodef.py prod → data/themes.json
"""
import sys,json,re
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
S=json.load(open('data/summary.json',encoding='utf-8'));cap=lambda c:S['d'][c][0]*S['sh'][c]
w=lambda t:sum(1 if ord(c)>255 else .55 for c in t)
G=[('robot','🤖 機器人',['ROK','TER','ISRG'],[['6954','發那科'],['6506','安川電機'],['6324','哈默納科']],[],
    [['1590','傳動｜氣動元件'],['2049','傳動｜線性滑軌'],['7750','控制｜控制器'],['2464','整合｜自動化系統'],['4583','傳動｜減速機'],
     ['4576','傳動｜直驅馬達'],['6166','控制｜機器人主機'],['2359','視覺｜AI 視覺'],['6188','本體｜協作手臂'],['1536','傳動｜齒輪']]),
   ('defense','🚀 軍工／無人機',['LMT','RTX','AVAV','KTOS'],[['7011','三菱重工'],['7012','川崎重工']],[['012450','韓華航太'],['079550','LIG Nex1']],
    [['2645','航太｜引擎維修'],['2634','航太｜軍機'],['2312','無人機｜代工'],['8033','無人機｜整機'],['2208','造船｜潛艦國造'],
     ['3718','無人機｜光學'],['6753','造船｜艦艇']])]
d=json.load(open('data/themes.json',encoding='utf-8'));lines=open('data/themes.json',encoding='utf-8').read().split('\n')
used={c for t in d['themes'] if t['id'] not in {'fpg','hh','umc','asus','wal'} for c,_ in t['stocks']}
for i,nm,us,jp,kr,L in G:
    bad=[(r,round(cap(r[0])/1e8,1),w(r[1])) for r in L if cap(r[0])<99.5e8 or w(r[1])>8.6 or r[0] in used];assert not bad,bad
    L.sort(key=lambda r:-cap(r[0]));assert not any('"id": "%s"'%i in l for l in lines)
k=[n for n,l in enumerate(lines) if l.lstrip().startswith('{"id": "ipc"')][0]
def obj(i,nm,us,jp,kr,L):
    o={'id':i,'name':nm,'us':us,'jp':jp}
    if kr:o['kr']=kr
    o['stocks']=L;return '    '+json.dumps(o,ensure_ascii=False)+','
lines[k+1:k+1]=[obj(*g) for g in G]
out='\n'.join(lines);d=json.loads(out);print(len(d['themes']),[x['id'] for x in d['themes']])
for i,nm,us,jp,kr,L in G: print(nm,[(r[0],round(cap(r[0])/1e8)) for r in L])
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
rep('<span style="opacity:.5">%s</span>'%v,'<span style="opacity:.5">%s 機器人／軍工預覽</span>'%v)
s=s.replace('<title>','<title>[beta] ',1)
open('beta.html','w',encoding='utf-8').write(s);print('ok')
