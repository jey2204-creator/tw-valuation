#!/usr/bin/env python3
"""2026-11-15 內建主題改「上游→下游」排序＋成份股依市值排序＋補 7 個細產業（beta 預覽）。
- 產生 data/themes_beta.json（由 data/themes.json＋data/summary.json 的 收盤×股數 算市值）
- beta.html 改讀 themes_beta.json，並且「不套用手機裡的手動排序／改過的成份股、也不存檔」，
  這樣在已手動排序過的 iPhone 上也看得到新的預設順序；正式版資料完全不動。
用法：python3 patch_thord.py → data/themes_beta.json＋beta.html
      python3 patch_thord.py prod → 把 themes_beta.json 蓋到 data/themes.json（index.html 不用改）
"""
import sys,json
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
T=json.load(open('data/themes.json',encoding='utf-8'));S=json.load(open('data/summary.json',encoding='utf-8'))
def cap(c):
    d=S['d'].get(c);sh=S['sh'].get(c)
    return d[0]*sh if d and sh and d[0] else -1
bm={t['id']:t for t in T['themes']}
def mv(src,codes):
    out=[s for s in bm[src]['stocks'] if s[0] in codes];bm[src]['stocks']=[s for s in bm[src]['stocks'] if s[0] not in codes];return out
def add(tid,rows):
    have={s[0] for s in bm[tid]['stocks']};bm[tid]['stocks']+=[r for r in rows if r[0] not in have]
NEW={
 'cufoil':('🧵 銅箔／玻纖布',[['1802','玻纖布'],['8358','銅箔'],['1815','玻纖紗／布']]),
 'bmc':('🎛️ BMC',[['5274','BMC 龍頭'],['4919','BMC']]),
 'conn':('🪢 連接器／線材',mv('passive',{'3533','3665'})+[['3023','線束／連接線']]) if 'conn' not in bm else None,
 'bbu':('🪫 BBU',[['6781','BBU 電池模組'],['3211','BBU 電池模組'],['4931','BBU 電池模組']]),
 'chassis':('🗄️ 機殼／滑軌',[['2059','伺服器滑軌'],['8210','伺服器機殼'],['6584','伺服器滑軌'],['3013','伺服器機殼']]),
 'brand':('🏷️ 品牌／板卡',[['2357','品牌／AI 伺服器'],['2376','板卡／AI 伺服器'],['2377','板卡／AI 伺服器']]),
 'fab':('🏗️ 無塵室／廠務',[['2404','無塵室工程'],['6139','無塵室工程'],['6196','廠務／設備代理']]),
}
for k,v in NEW.items():
    if k not in bm and v:bm[k]={'id':k,'name':v[0],'stocks':v[1]}
add('wafer',[['3532','矽晶圓']]);add('pcb',[['6213','CCL 銅箔基板']])
ORDER=['wafer','ai','mem','pkg','cufoil','pcb','passive','bmc','link','conn','thermal','psu','bbu','chassis','cpo','net','server','brand','power','fab','leo']
assert set(ORDER)==set(bm),set(ORDER)^set(bm)
for t in bm.values():t['stocks'].sort(key=lambda s:-cap(s[0]))
T['themes']=[bm[i] for i in ORDER]
T['說明']=T['說明']+' 主題順序＝上游→下游；成份股順序＝市值大→小（%s 收盤）。'%S.get('pxAsof','') if '上游→下游' not in T['說明'] else T['說明']
txt='{\n  "說明": %s,\n  "themes": [\n%s\n  ]\n}\n'%(json.dumps(T['說明'],ensure_ascii=False),',\n'.join('    '+json.dumps(t,ensure_ascii=False) for t in T['themes']))
json.loads(txt)
if prod:
    open('data/themes.json','w',encoding='utf-8').write(txt);print('prod ok');sys.exit()
open('data/themes_beta.json','w',encoding='utf-8').write(txt)
s=open('index.html',encoding='utf-8').read()
def rep(old,new):
    global s
    assert s.count(old)==1,(s.count(old),old[:60]);s=s.replace(old,new)
rep("fetch('data/themes.json?t='+Date.now());if(r.ok)BASE=","fetch('data/themes_beta.json?t='+Date.now());if(r.ok)BASE=")
# beta 預覽：不套手機裡的排序／改過的成份股，也不寫回 localStorage
rep("const cfgGet=()=>{const c=store.get('themeCfg')||{};return {order:c.order||[],hidden:c.hidden||[],themes:c.themes||{}}};",
    "const cfgGet=()=>({order:[],hidden:[],themes:{}});   // beta 預覽：只看預設順序")
rep("function cfgSave(c){store.set('themeCfg',c);applyCfg()}","function cfgSave(c){applyCfg()}   // beta 預覽：不存檔")
# 其餘會寫／刪 themeCfg 的地方（還原預設、復原）在 beta 一律不動手機資料
assert s.count("localStorage.removeItem('themeCfg')")>=1 and s.count("store.set('themeCfg',")>=1
s=s.replace("localStorage.removeItem('themeCfg')","0").replace("store.set('themeCfg',","(()=>{})('themeCfg',")
rep('<span style="opacity:.5">v1115n</span>','<span style="opacity:.5">v1115o 主題排序預覽</span>')
s=s.replace('<title>','<title>[beta] ',1)
open('beta.html','w',encoding='utf-8').write(s);print('ok')
