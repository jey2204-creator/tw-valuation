#!/usr/bin/env python3
"""2026-11-18 掃描頁小卡第二行：放不下時自動讓位，不再把「投／外」標切一半

用法：python3 patch_fit.py            → 讀 scan.html，輸出 beta_scan_fit.html
      python3 patch_fit.py prod       → 直接改 scan.html（已套用過會因 assert 中止）

起因：世杰 11/18 貼記憶體（週模式）截圖，台股小卡第二行「▼2.7% 週▼8.8% 量0.7× 投1▲ 外1▲」放不下，
     右邊的「投1▲／外1▲」被切一半（原本就有，不是海外龍頭造成的）。他說「要，做給我看」。
做法：畫完小卡後量每張第二行有沒有超出；只要有一張超出，**整面小卡一起**依序讓位（樣式一致；都沒超出就完全不變）：
  ① 投／外標拿掉箭頭（紅底＝買、綠底＝賣，顏色本來就看得出方向）；
  ② 還是放不下 → 拿掉量比／值／量那一格；但如果現在正照「量比 值 量」排序，改成拿掉當日漲跌（週／月模式才有兩格漲跌）；
  ③ 還是放不下 → 字縮小一點（9.5→8.6px）；④ 再不行才兩個都拿掉。最後：②③ 讓位後如果箭頭放得回去，就把箭頭放回去。
  字型載入完成、視窗改變大小時會重算。
"""
import sys

PROD = len(sys.argv) > 1 and sys.argv[1] == 'prod'
SRC = 'scan.html'
OUT = 'scan.html' if PROD else 'beta_scan_fit.html'
VER = 'v1118g'
OLDV = sys.argv[2] if len(sys.argv) > 2 else None

s = open(SRC, encoding='utf-8').read()
assert 'fitS(' not in s, '已套用過'


def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (s.count(old), old[:80])
    s = s.replace(old, new)


# 箭頭包一層，方便收起
rep("return `<span class=\"tg ${v>0?'b':'s'}\">${who}${Math.min(Math.abs(v),9)}${v>0?'▲':'▼'}</span>`}",
    "return `<span class=\"tg ${v>0?'b':'s'}\">${who}${Math.min(Math.abs(v),9)}<i class=\"ar\">${v>0?'▲':'▼'}</i></span>`}")
# 台股小卡：週／月模式時當日漲跌那格加 dch（可被讓位）
rep('''<div class="km-s"><span class="${cls(r.chg)}${r.stale?' st':''}" title="${r.stale?'昨天收盤的漲跌幅':''}">''',
    '''<div class="km-s"><span class="${cls(r.chg)}${r.stale?' st':''}${CHGP!=='d'?' dch':''}" title="${r.stale?'昨天收盤的漲跌幅':''}">''')
rep('.km-s .vr{color:var(--muted)}',
    '/* 2026-11-18 第二行放不下時依序讓位（fitS） */\n'
    '.km-s .ar{font-style:normal}.km-s.c1 .ar{display:none}.km-s.c2 .vr{display:none}.km-s.c3 .dch{display:none}.km-s.c5{font-size:8.6px;letter-spacing:-.05em;gap:1px}\n'
    '.km-s .vr{color:var(--muted)}')
# 量測＋讓位
rep("// ---- 2026-11-17：🌏 海外龍頭小卡",
    "// ---- 2026-11-18：小卡第二行放不下時依序讓位：① 投／外標去箭頭 ② 去量比（正照量比／值／量排序時改去當日漲跌）③ 兩個都去 ----\n"
    "function fitS(){const L=[...document.querySelectorAll('#grid .km-s')];if(!L.length||MODE==='v')return;const set=(k,on)=>L.forEach(e=>e.classList.toggle(k,on)),cut=()=>L.some(e=>e.scrollWidth>e.clientWidth);\n"
    "  set('c1',false);set('c2',false);set('c3',false);set('c5',false);if(!cut())return;      // 整面一起讓位（同一面小卡樣式一致）\n"
    "  set('c1',true);if(!cut())return;\n"
    "  const k=sortK==='vr'&&CHGP!=='d'?'c3':'c2';set(k,true);\n"
    "  if(cut()){set('c5',true);if(cut()){set('c5',false);set('c2',true);set('c3',true)}return}   // 還放不下 → 字縮一點；再不行才兩格都拿掉\n"
    "  set('c1',false);if(cut())set('c1',true)}                                  // 讓位後箭頭全部放得回去就放回去\n"
    "if(document.fonts&&document.fonts.ready)document.fonts.ready.then(()=>{try{fitS()}catch(e){}});\n"
    "// ---- 2026-11-17：🌏 海外龍頭小卡")
rep("    <canvas class=\"km-cv\"></canvas></article>`).join('');\n  const io=new IntersectionObserver(",
    "    <canvas class=\"km-cv\"></canvas></article>`).join('');fitS();\n  const io=new IntersectionObserver(")

import re
m = re.findall(r'<span style="opacity:.5">(v\d{4}[a-z])</span>', s)
assert len(m) == 1, m
s = s.replace('<span style="opacity:.5">%s</span>' % m[0], '第二行放不下時會自動讓位：先拿掉投/外標的箭頭 (紅底＝買、綠底＝賣)，再拿掉量比。 <span style="opacity:.5">%s</span>' % VER)

if not PROD:
    s = s.replace('<title>', '<title>β ', 1)
open(OUT, 'w', encoding='utf-8').write(s)
print('wrote', OUT, len(s), 'from', m[0])
