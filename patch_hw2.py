#!/usr/bin/env python3
"""2026-11-18 全形→半形第二批：
(1) 13 個內建主題名稱的「／」→「/」（data/themes.json 只改 name，成份股備註不動）
(2) 注意／處置主題頁日期選單與名單日說明的全形括號 →半形：「11/16（一）」→「11/16 (一)」
疊在 patch_tno.py、patch_hw.py 之上。
用法：python3 patch_tno.py && python3 patch_hw.py && python3 patch_hw2.py → beta.html＋data/themes_beta.json
      python3 patch_tno.py prod && python3 patch_hw.py prod && python3 patch_hw2.py prod → index.html＋data/themes.json
"""
import sys,json,re
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
# (1) 主題名稱：逐行改，維持原檔排版
raw=open('data/themes.json',encoding='utf-8').read();n=0
def fix(m):
    global n
    if '／' in m.group(2):n+=1
    return m.group(1)+m.group(2).replace('／','/')+m.group(3)
out=re.sub(r'("name":\s*")([^"]*)(")',fix,raw)
assert n==13,n
a,b=json.loads(raw)['themes'],json.loads(out)['themes']
assert [t['id'] for t in a]==[t['id'] for t in b] and all(x['stocks']==y['stocks'] for x,y in zip(a,b))
open('data/themes.json' if prod else 'data/themes_beta.json','w',encoding='utf-8').write(out)
# (2) index
f='index.html' if prod else 'beta.html'
s=open(f,encoding='utf-8').read()
def rep(old,new,n=1):
    global s
    assert s.count(old)==n,(s.count(old),old[:60]);s=s.replace(old,new)
rep("+(NTN?'':'（'+ntWk(NT.asof)+'）')]);","+(NTN?'':' ('+ntWk(NT.asof)+')')]);")
rep("o.push([d,ntMd(d)+'（'+ntWk(d)+'）'])","o.push([d,ntMd(d)+' ('+ntWk(d)+')'])")
rep("`目前適用（${ntMd(d)} 公布，同 XQ）`:`名單日 ${ntMd(d)}（${ntWk(d)}）`):isNx?`${NXL}適用（${ntMd(d)} 公布）`:`歷史名單 ${ntMd(d)}（${ntWk(d)}）`",
    "`目前適用 (${ntMd(d)} 公布，同 XQ)`:`名單日 ${ntMd(d)} (${ntWk(d)})`):isNx?`${NXL}適用 (${ntMd(d)} 公布)`:`歷史名單 ${ntMd(d)} (${ntWk(d)})`")
if not prod:rep("fetch('data/themes.json?t='+Date.now());if(r.ok)BASE=","fetch('data/themes_beta.json?t='+Date.now());if(r.ok)BASE=")
rep('<span style="opacity:.5">v1118d</span>','<span style="opacity:.5">v1118e</span>')
open(f,'w',encoding='utf-8').write(s);print('ok',f,n)
