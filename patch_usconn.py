#!/usr/bin/env python3
"""2026-11-18 美股站新增兩主題：🪢 連接器／線材（APH、TEL）、🧪 半導體材料（ENTG、LIN、Q），跟台股站 batch14 對齊。
APH 從被動元件搬出、ENTG 從矽晶圓搬出；貿聯、嘉澤從被動元件的對應台股搬到連接器。CRDO 留在矽光子（資料層一檔只能屬一個主題）。
用法：python3 patch_usconn.py → us/index_test.html（預覽：TEL／LIN／Q 還是全市場股，沒有本益比、日 K）
     python3 patch_usconn.py prod → 改 us/index.html＋us/fetch_us.py（之後要 dispatch update_us 抓 APH ENTG VSH LFUS TEL LIN Q）
"""
import sys,json
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
NM={r[0]:r[1] for r in json.load(open('data/list.json',encoding='utf-8'))}
tw=lambda *c:[[x,NM[x]] for x in c]
CONN,SEMI,PASS=tw('3665','3533','3023','6290','6197'),tw('5434','4749','1785','3010'),tw('2327','2492','3026')
s=open('us/index.html',encoding='utf-8').read()
def rep(old,new):
    global s
    assert s.count(old)==1,(s.count(old),old[:60]);s=s.replace(old,new)
rep("'⚡ 被動元件':'passive',","'⚡ 被動元件':'passive','🪢 連接器／線材':'conn','🧪 半導體材料':'semimat',")
rep("'power','passive','wafer','leo','cloud']","'power','passive','conn','wafer','semimat','leo','cloud']")
rep("APH:'連接器',","APH:'連接器',TEL:'連接器／感測器',LIN:'工業／電子氣體',Q:'CMP／光阻材料',")
if prod:
    open('us/index.html','w',encoding='utf-8').write(s)
    f=open('us/fetch_us.py',encoding='utf-8').read()
    def frep(old,new):
        global f
        assert f.count(old)==1,(f.count(old),old[:60]);f=f.replace(old,new)
    py=lambda L:'['+', '.join(f'("{a}", "{b}")' for a,b in L)+']'
    frep('''    ("💿 矽晶圓／基板", [("WOLF", "C"), ("COHR", ""), ("ENTG", "")],''','''    ("💿 矽晶圓／基板", [("WOLF", "C"), ("COHR", "")],''')
    frep('''    ("⚡ 被動元件", [("VSH", "C"), ("LFUS", ""), ("APH", "")],
     [("2327", "國巨"), ("2492", "華新科"), ("3026", "禾伸堂"), ("3533", "嘉澤"), ("3665", "貿聯-KY")]),''',
     f'''    ("⚡ 被動元件", [("VSH", "C"), ("LFUS", "")],
     {py(PASS)}),
    ("🪢 連接器／線材", [("APH", ""), ("TEL", "")],
     {py(CONN)}),
    ("🧪 半導體材料", [("ENTG", ""), ("LIN", ""), ("Q", "")],
     {py(SEMI)}),''')
    frep('''"VSH": "威世", "LFUS": "力特", "APH": "安費諾",''','''"VSH": "威世", "LFUS": "力特", "APH": "安費諾", "TEL": "泰科電子", "LIN": "林德", "Q": "Qnity 電子材料",''')
    open('us/fetch_us.py','w',encoding='utf-8').write(f);print('prod ok');sys.exit()
# 測試頁：index.json 還沒重跑，載入後在瀏覽器裡把主題／對應台股改成新版；TEL／LIN／Q 以全市場股掛進新主題
rep("function baseThemes(){const g=[];","function baseThemes(){const g=[];const _o={APH:['🪢 連接器／線材',%s],ENTG:['🧪 半導體材料',%s],VSH:['⚡ 被動元件',%s],LFUS:['⚡ 被動元件',%s]};IDX.forEach(s=>{const o=_o[s.id];if(o){s.theme=o[0];s.tw=o[1]}});"%tuple(json.dumps(x,ensure_ascii=False) for x in (CONN,SEMI,PASS,PASS)))
rep("const r=id=>{const i=DEF_ORDER.indexOf(id);return i<0?99:i};return g.sort(","const _a=(i,l)=>{const t=g.find(x=>x.id===i);if(t)l.forEach(u=>t.stocks.push([u,ROLE[u]||'']))};_a('conn',['TEL']);_a('semimat',['LIN','Q']);const r=id=>{const i=DEF_ORDER.indexOf(id);return i<0?99:i};return g.sort(")
s=s.replace('<title>','<title>[測試] ',1)
open('us/index_test.html','w',encoding='utf-8').write(s);print('ok',CONN,SEMI)
