#!/usr/bin/env python3
"""2026-11-17 掃描頁「🌏 海外龍頭」改成「龍頭排序」（接在 patch_ovs.py、patch_ovus.py 之後）

用法：python3 patch_ovord.py data     → 把排序寫進 data/themes.json 各主題的 ov 欄位（可重跑，會覆蓋 ov）
      python3 patch_ovord.py          → 讀 scan.html，輸出 beta_scan_ovord.html
      python3 patch_ovord.py prod     → 直接改 scan.html（已套用過會因 assert 中止）

起因：世杰說想要的是「村田這種真正的龍頭排最前面」（不是市值、也不是 美→日→韓），選 A「22 個主題一次排好出 beta」。
做法：
  1. themes.json 主題多一個 ov 欄位＝[[鍵, 一句理由], …]，鍵＝us代號／jp代號／kr代號／cn代號，順序＝產業地位（Claude 依既有認識初擬，
     市占未逐一查證；世杰不同意就直接改這裡的 ORD 再跑 data）。沒列到的對應股照原順序接在後面。
  2. 掃描頁「全」＝照 ov 跨國混排，第 1 名標 👑；點「美／日／韓」＝同一份順序只留該國。
  3. 放大卡多一行「🌏 龍頭排序第 N・理由」。
  只有 scan 會讀 ov；首頁／其他頁不受影響。
"""
import json
import sys

ARG = sys.argv[1] if len(sys.argv) > 1 else ''
VER = 'v1117h'

ORD = {
    'leo': [('usSPCX', 'Starlink・低軌龍頭'), ('usASTS', '手機直連衛星'), ('usRKLB', '發射＋衛星製造'), ('usECHO', '衛星營運・頻譜'),
            ('usIRDM', '低軌語音／物聯網'), ('usVSAT', '衛星寬頻'), ('usGSAT', '蘋果衛星通訊夥伴')],
    'wafer': [('jp4063', '矽晶圓全球第一'), ('jp3436', '矽晶圓全球第二'), ('usWOLF', 'SiC 基板'), ('usCOHR', 'SiC／化合物基板'),
              ('jp4004', 'SiC 磊晶・材料'), ('krSKC' , ''), ('usENTG', '半導體材料耗材'), ('jp4186', '光阻'),
              ('kr357780', '蝕刻液'), ('kr005290', '光阻')],
    'ai': [('usNVDA', 'AI GPU 龍頭'), ('usAMD', 'GPU／CPU 第二'), ('usARM', '處理器架構 IP'), ('jp6526', 'ASIC 設計服務'), ('jp6723', '車用 MCU・AI 關聯低')],
    'mem': [('kr000660', 'HBM 龍頭'), ('kr005930', '記憶體產能最大'), ('usMU', 'DRAM 三強之一'), ('cn688825', 'DRAM 全球第四'), ('jp285A', 'NAND'), ('usSNDK', 'NAND')],
    'equip': [('usAMAT', '設備綜合龍頭'), ('jp8035', '塗佈顯影・蝕刻'), ('usLRCX', '蝕刻・沉積'), ('usKLAC', '檢測量測龍頭'),
              ('jp6146', '切割研磨龍頭'), ('kr042700', 'HBM 鍵合機'), ('jp6920', 'EUV 光罩檢測'), ('jp7735', '清洗龍頭'),
              ('jp6525', '成膜'), ('jp7729', '探針台・切割'), ('usONTO', '先進封裝檢測'), ('usCAMT', '先進封裝檢測'),
              ('kr403870', '高壓退火'), ('kr240810', '沉積'), ('kr036930', 'ALD'), ('kr039030', '雷射設備')],
    'pkg': [('usAMKR', '封測全球第二')],
    'probe': [('jp6857', '測試機龍頭'), ('usFORM', '探針卡龍頭'), ('kr058470', '測試探針・插座'), ('kr095340', '測試插座'), ('kr089030', '分選機')],
    'cufoil': [('jp3110', '低介電玻纖布龍頭'), ('jp2802', 'ABF 膜獨占')],
    'ccl': [('jp4062', 'ABF 載板龍頭'), ('kr011070', '載板・相機模組'), ('kr353200', '載板'), ('kr222800', '記憶體載板'), ('kr007810', '載板')],
    'pcb': [('usTTMI', '北美 PCB 龍頭'), ('kr007660', 'AI 高層板')],
    'passive': [('jp6981', 'MLCC 全球第一'), ('kr009150', 'MLCC 全球第二'), ('jp6976', 'MLCC 前段班・純度高'), ('jp6762', '電感龍頭・電池占比大'),
                ('usVSH', '電阻・分離式元件'), ('jp6971', '有 AVX・被動占比低'), ('usLFUS', '保護元件'), ('usAPH', '主業連接器')],
    'link': [('usALAB', 'Retimer 龍頭')],
    'thermal': [('usVRT', '資料中心散熱・電力龍頭')],
    'psu': [('usETN', '電力管理龍頭')],
    'cpo': [('usAVGO', 'CPO・交換晶片龍頭'), ('usMRVL', '光 DSP'), ('usLITE', '雷射光源龍頭'), ('usFN', '光模組代工'), ('usCIEN', '光網路設備'),
            ('usCRDO', 'AEC 主動電纜'), ('jp5803', '光纖・連接'), ('jp5802', '光纖・光元件'), ('jp5801', '光纖・雷射'), ('usAAOI', '光模組')],
    'net': [('usANET', '資料中心交換器龍頭')],
    'itsvc': [('usACN', 'IT 顧問龍頭'), ('usIBM', '企業 IT・AI 服務'), ('jp6702', '日本 IT 服務龍頭'), ('jp4307', '日本 IT 顧問')],
    'server': [('usSMCI', 'AI 伺服器品牌'), ('usCLS', 'AI 伺服器・交換器代工'), ('usJBL', 'EMS'), ('usSANM', 'EMS'),
               ('jp5803', '光纖線材'), ('jp4062', 'ABF 載板'), ('jp3110', '玻纖布'), ('jp5706', '高階銅箔'), ('jp6981', 'MLCC'),
               ('jp5801', '光纖'), ('jp6516', '散熱風扇'), ('jp285A', 'NAND'), ('jp6594', '馬達・水冷'), ('jp6762', '電感'),
               ('jp6963', '功率元件'), ('jp6997', '電容'), ('jp5802', '光纖')],
    'robot': [('jp6954', '工業機器人龍頭'), ('jp6506', '伺服・機器人'), ('jp6324', '諧波減速機龍頭'), ('usISRG', '手術機器人龍頭'),
              ('usROK', '工業自動化'), ('usTER', '協作機器人・測試')],
    'defense': [('usLMT', '全球最大軍工'), ('usRTX', '飛彈・引擎'), ('jp7011', '日本軍工龍頭'), ('kr012450', '韓國軍工龍頭'),
                ('usAVAV', '軍用無人機'), ('usKTOS', '無人機・靶機'), ('kr079550', '飛彈'), ('jp7012', '軍機・潛艦')],
    'power': [('usGEV', '燃氣輪機・電網龍頭'), ('jp6501', '電網・變壓器'), ('kr267260', '變壓器出口'), ('kr298040', '變壓器'),
              ('kr010120', '配電'), ('jp6503', '重電'), ('jp6504', '功率・配電'), ('kr103590', '電纜・變壓器')],
    'fhc': [('usJPM', '全球最大銀行'), ('usBAC', '美國第二大'), ('usMS', '投行・財管'), ('jp8306', '日本最大金融'),
            ('jp8316', '日本第二大'), ('kr105560', '韓國最大金控'), ('kr055550', '韓國第二大'), ('jp8750', '壽險')],
    'bank': [('usWFC', '美國大型商銀'), ('usUSB', '美國區域銀行龍頭'), ('jp8411', '日本三大行')],
    'realty': [('usDHI', '美國最大建商'), ('usLEN', '美國第二大建商'), ('jp8801', '日本最大地產'), ('jp8802', '日本地產・商辦')],
}
ORD['wafer'][5] = ('kr011790', '玻璃基板・材料')

if ARG == 'data':
    P = 'data/themes.json'
    lines = open(P, encoding='utf-8').read().split('\n')
    ids, nt, ng = set(), 0, 0
    for i, ln in enumerate(lines):          # 檔案格式＝一個主題一行，逐行改，其他行原封不動
        if not ln.startswith('    {"id"'):
            continue
        comma = ln.rstrip().endswith(',')
        t = json.loads(ln.strip().rstrip(','))
        assert '    ' + json.dumps({k: v for k, v in t.items() if k != 'ov'}, ensure_ascii=False) + (',' if comma else '') == ln or 'ov' in t, t['id']
        ids.add(t['id'])
        keys = ['us' + str(u).upper() for u in t.get('us') or []] + ['jp' + c for c, _ in t.get('jp') or []] + ['kr' + c for c, _ in t.get('kr') or []] + ['cn' + c for c, _ in t.get('cn') or []]
        o = ORD.get(t['id'])
        if not keys:
            assert not o, t['id']
            continue
        assert o, ('沒排到', t['id'])
        ks = [k for k, _ in o]
        assert len(set(ks)) == len(ks) and set(ks) == set(keys), (t['id'], sorted(set(keys) ^ set(ks)))
        assert all(len(n) <= 14 for _, n in o), (t['id'], [n for _, n in o if len(n) > 14])
        t.pop('ov', None)
        t2 = {}
        for k, v in t.items():              # ov 放在 stocks 前面
            if k == 'stocks':
                t2['ov'] = [[k2, n] for k2, n in o]
            t2[k] = v
        lines[i] = '    ' + json.dumps(t2, ensure_ascii=False) + (',' if comma else '')
        nt += 1
        ng += len(o)
    assert not (set(ORD) - ids), set(ORD) - ids
    open(P, 'w', encoding='utf-8').write('\n'.join(lines))
    json.load(open(P, encoding='utf-8'))
    print('themes.json ov:', nt, '個主題', ng, '格')
    sys.exit()

PROD = ARG == 'prod'
SRC = 'scan.html'
OUT = 'scan.html' if PROD else 'beta_scan_ovord.html'
s = open(SRC, encoding='utf-8').read()
assert 'OVMK' in s, '要先套 patch_ovus.py'
assert 'OVN' not in s, '已套用過'


def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (s.count(old), old[:80])
    s = s.replace(old, new)


# ---- ovIds：照 ov（龍頭排序）排，沒列到的照原順序接後面；OVN＝鍵 → [名次, 理由] ----
rep("  return [...(t.us||b.us||[]).map(x=>['us'+String(x).toUpperCase(),'']),...(t.jp||b.jp||[]).map(x=>['jp'+x[0],x[1]]),...(t.kr||b.kr||[]).map(x=>['kr'+x[0],x[1]])]}",
    "  const L=[...(t.us||b.us||[]).map(x=>['us'+String(x).toUpperCase(),'']),...(t.jp||b.jp||[]).map(x=>['jp'+x[0],x[1]]),...(t.kr||b.kr||[]).map(x=>['kr'+x[0],x[1]])];\n"
    "  // 2026-11-17：龍頭排序（themes.json 的 ov，依產業地位手動排）；跨國混排，第 1 名＝👑\n"
    "  OVN={};const o=t.ov||b.ov||[];o.forEach((x,i)=>{if(!OVN[x[0]])OVN[x[0]]=[i,x[1]||'']});\n"
    "  return o.length?L.map((x,i)=>[x,i]).sort((p,q)=>((OVN[p[0][0]]||[1e3+p[1]])[0])-((OVN[q[0][0]]||[1e3+q[1]])[0])).map(p=>p[0]):L}")
rep("OVB=null,OVF='a';const OVMK", "OVB=null,OVF='a',OVN={};const OVMK")
rep("return {ov:1,m:o.m,mk:OVMK[o.m]||'外',", "return {ov:1,rk:(OVN[k]||[])[0],nt:(OVN[k]||[])[1]||'',m:o.m,mk:OVMK[o.m]||'外',")
# 小卡：第 1 名標 👑
rep('''    <div class="km-h">${nmB(r.n)}${r.m==='us'?'':`<span class="cd">${esc(r.cd)}</span>`}<span class="tg fx" title="${r.mk}股">${r.mk}</span></div>''',
    '''    <div class="km-h"${r.nt?` title="龍頭排序第 ${r.rk+1}・${esc(r.nt)}"`:''}>${r.rk===0?'<span class="rk" title="這個主題的全球龍頭">👑</span>':''}${nmB(r.n)}${r.m==='us'?'':`<span class="cd">${esc(r.cd)}</span>`}<span class="tg fx" title="${r.mk}股">${r.mk}</span></div>''')
# 放大卡：多一行排序理由
rep("${r.ov?'':`<span>投信 5日", "${r.ov?(r.nt?`<span>${r.rk===0?'👑 ':'🌏 '}龍頭排序第 <b>${r.rk+1}</b>・${esc(r.nt)}</span>`:''):`<span>投信 5日")

# ---- 版本、頁尾說明 ----
rep('順序美→日→韓，標題列「全 美 日 韓」可只看一國',
    '順序＝<b>龍頭排序</b>（依產業地位手動排、跨國混排，👑＝這個主題的全球龍頭；是主觀判斷、不是市值，點小卡放大可看每檔的理由），標題列「全 美 日 韓」可只看一國')
rep('<span style="opacity:.5">v1117g</span>', '<span style="opacity:.5">' + VER + '</span>')

if not PROD:
    s = s.replace('<title>', '<title>β ', 1)
open(OUT, 'w', encoding='utf-8').write(s)
print('wrote', OUT, len(s))
