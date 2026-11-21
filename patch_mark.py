#!/usr/bin/env python3
"""2026-11-22 batch18 兩站都有的產業主題做記號（方案 A）
台股站：首頁主題表第二行小字加 🇺🇸（有對應美股的主題；點了直接開美股同主題），卡片模式主題名後加 🇺🇸
美股站：反過來只標「美股獨有」（費城半導體、雲端資本支出：台股沒有對應主題）——同步主題太多，全標等於沒標
用法：python3 patch_mark.py → beta_mark.html＋us/index_test.html；python3 patch_mark.py prod → index.html＋us/index.html
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
def patch(path,R):
    s=open(path,encoding='utf-8').read()
    for a,b in R:
        assert s.count(a)==1,(path,s.count(a),a[:70]);s=s.replace(a,b)
    return s
# ---------- 台股站 ----------
tw=patch('index.html',[
 (".tlt .tm{display:block;font-size:10.5px;color:var(--muted);font-family:var(--f-num);white-space:nowrap}",
  ".tlt .tm{display:block;font-size:10.5px;color:var(--muted);font-family:var(--f-num);white-space:nowrap}\n"
  "/* 🇺🇸＝這個主題美股站也有（themes.json 有 us 欄），點了開美股同主題 */\n.usf{text-decoration:none;font-size:11px;margin-left:4px;padding:0 2px;vertical-align:0}.tcard b .usf{font-size:12px;margin-left:3px}"),
 ("${nf?` 🔥${nf}`:''}`;",
  "${nf?` 🔥${nf}`:''}${(t.us||[]).length?`<a class=\"usf\" href=\"us/index.html#t/${t.id}\" title=\"美股站也有這個主題（${t.us.length} 檔對應美股），點了開美股同主題\" aria-label=\"美股同主題\">🇺🇸</a>`:''}`;"),
 ("    const r=e.target.closest('tr[data-t]');if(r)location.hash='#t/'+r.dataset.t};\n}\nfunction calHome(){",
  "    if(e.target.closest('a.usf'))return;   // 🇺🇸 連到美股站，不要當成點這一列\n"
  "    const r=e.target.closest('tr[data-t]');if(r)location.hash='#t/'+r.dataset.t};\n}\nfunction calHome(){"),
 ('return `<a class="tcard" href="#t/${t.id}"><b>${t.name}</b>',
  'return `<a class="tcard" href="#t/${t.id}"><b>${t.name}${(t.us||[]).length?\'<span class="usf" title="美股站也有這個主題">🇺🇸</span>\':\'\'}</b>'),
])
# ---------- 美股站 ----------
us=patch('us/index.html',[
 (".sgl{font-size:10px;vertical-align:1px}",
  ".uso{font-family:var(--f-body);font-size:9.5px;color:var(--muted);border:1px solid var(--line);border-radius:4px;padding:0 3px;margin-left:4px;vertical-align:1px;font-weight:500}\n.sgl{font-size:10px;vertical-align:1px}"),
 ("${sg.lt?` <span class=\"sgl\" title=\"${sg.tip}\">${sg.lt}</span>`:''}`;",
  "${sg.lt?` <span class=\"sgl\" title=\"${sg.tip}\">${sg.lt}</span>`:''}${t.uso?'<span class=\"uso\" title=\"台股沒有對應主題\">美股獨有</span>':''}`;"),
 ("return `<a class=\"tcard\" href=\"#t/${t.id}\"><b>${esc(t.name)}${sg.lt?` <span class=\"sgl\" title=\"${sg.tip}\">${sg.lt}</span>`:''}</b>`+",
  "return `<a class=\"tcard\" href=\"#t/${t.id}\"><b>${esc(t.name)}${sg.lt?` <span class=\"sgl\" title=\"${sg.tip}\">${sg.lt}</span>`:''}${t.uso?'<span class=\"uso\">美股獨有</span>':''}</b>`+"),
 (":(t.dem?'<span class=\"lb\">對應台股：全供應鏈（需求層）</span>':'');",
  ":(t.dem?'<span class=\"lb\">對應台股：全供應鏈（需求層）・美股獨有主題</span>':t.uso?'<span class=\"lb\">美股獨有主題：台股沒有對應</span>':'');"),
])
if prod:
    open('index.html','w',encoding='utf-8').write(tw);open('us/index.html','w',encoding='utf-8').write(us);print('prod ok');sys.exit()
open('beta_mark.html','w',encoding='utf-8').write(tw.replace('<title>','<title>[測試] ',1))
open('us/index_test.html','w',encoding='utf-8').write(us.replace('<title>','<title>[測試] ',1))
print('test ok')
