#!/usr/bin/env python3
"""2026-11-16 新增產業主題：fhc「🏦 金控」13、bank「🏛️ 銀行」9、realty「🏠 營建／房地產」22（排在 fab 無塵室／廠務後、集團主題前）。
市值≥100 億、依市值排序、備註「類別｜說明」（≤約 9 個中文字寬）。證券／保險／票券公司、國產、鼎固-KY、水泥不放。
用法：python3 patch_finre.py → data/themes_beta.json＋beta.html（唯讀預覽）；python3 patch_finre.py prod → data/themes.json
"""
import sys,json,re
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
S=json.load(open('data/summary.json',encoding='utf-8'));cap=lambda c:S['d'][c][0]*S['sh'][c]
w=lambda t:sum(1 if ord(c)>255 else .55 for c in t)
G=[('fhc','🏦 金控',['JPM','BAC','MS'],[['8306','三菱日聯'],['8316','三井住友'],['8750','第一生命']],[['105560','KB金融'],['055550','新韓金融']],
    [['2881','壽險型｜富邦人壽'],['2882','壽險型｜國泰人壽'],['2891','銀行型｜中信銀'],['2887','綜合型｜銀行壽險'],['2885','證券型｜元大證'],
     ['2884','銀行型｜玉山銀'],['2886','銀行型｜公股'],['2880','銀行型｜公股'],['2890','銀行型｜銀行證券'],['2892','銀行型｜公股'],
     ['2883','壽險型｜凱基人壽'],['5880','銀行型｜公股'],['2889','票券型｜票券證券']]),
   ('bank','🏛️ 銀行',['WFC','USB'],[['8411','瑞穗']],[],
    [['2801','公股｜企金'],['5876','民營｜海外比重高'],['2834','公股｜中小企業'],['2812','民營｜中部'],['2838','民營｜房貸'],
     ['2845','民營｜遠東集團'],['2849','民營｜企金'],['2897','民營｜數位'],['2836','公股｜南部']]),
   ('realty','🏠 營建／房地產',['DHI','LEN'],[['8801','三井不動產'],['8802','三菱地所']],[],
    [['2542','建商｜全台'],['2597','營造｜潤泰集團'],['5522','建商｜北部'],['2539','建商｜中部'],['2540','建商｜代銷起家'],
     ['2548','建商｜雙北'],['2535','營造｜廠辦'],['2501','建商｜國泰集團'],['6177','建商｜高雄'],['5534','建商｜雙北'],
     ['2520','建商｜雙北'],['3703','營造｜大陸工程'],['2515','營造｜公共工程'],['2530','建商｜雙北'],['2543','營造｜公共工程'],
     ['5213','建商｜新北'],['2546','營造｜冠德集團'],['2511','建商｜統一集團'],['2545','建商｜雙北'],['2524','建商｜高雄'],
     ['2527','建商｜日月光集團'],['5508','建商｜高雄']])]
d=json.load(open('data/themes.json',encoding='utf-8'));lines=open('data/themes.json',encoding='utf-8').read().split('\n')
used={c for t in d['themes'] if t['id'] not in {'fpg','hh','umc','asus','wal'} for c,_ in t['stocks']}
for i,nm,us,jp,kr,L in G:
    bad=[(r,round(cap(r[0])/1e8,1),w(r[1])) for r in L if cap(r[0])<99.5e8 or w(r[1])>8.6 or r[0] in used];assert not bad,bad
    L.sort(key=lambda r:-cap(r[0]));assert not any('"id": "%s"'%i in l for l in lines)
k=[n for n,l in enumerate(lines) if l.lstrip().startswith('{"id": "fab"')][0]
def obj(i,nm,us,jp,kr,L):
    o={'id':i,'name':nm,'us':us,'jp':jp}
    if kr:o['kr']=kr
    o['stocks']=L;return '    '+json.dumps(o,ensure_ascii=False)+','
lines[k+1:k+1]=[obj(*g) for g in G]
out='\n'.join(lines);d=json.loads(out);print(len(d['themes']),[x['id'] for x in d['themes']])
for i,nm,us,jp,kr,L in G: print(nm,len(L),[(r[0],round(cap(r[0])/1e8)) for r in L])
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
rep('<span style="opacity:.5">%s</span>'%v,'<span style="opacity:.5">%s 金融／營建預覽</span>'%v)
s=s.replace('<title>','<title>[beta] ',1)
open('beta.html','w',encoding='utf-8').write(s);print('ok')
