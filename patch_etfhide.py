#!/usr/bin/env python3
"""2026-11-22 20:42 📦 ETF 手動隱藏個別 ETF（世杰選方案 ①：ETF 主題頁「✏️ 編輯」→ 逐檔「隱藏／顯示」）。
儲存：localStorage 'etfHide'＝[代號…]（只存這支手機；雲端同步目前只同步 fav/themeCfg/favMeta，沒有同步這個）。
首頁：
  etfTheme() 排除隱藏的 → 主題表中位數、主題頁、分類膠囊檔數、分組標題、上下切換都不含；
  主題頁「✏️ 編輯」打開（ETF 以外的自動主題仍隱藏）→ 編輯模式：依類別列出全部 ETF，每檔「隱藏／顯示」，上方「全部顯示」「✓ 完成」；
  一般模式說明列多一行「👁️ 已隱藏 N 檔：…（編輯）」。
掃描頁：ETF 名單排除隱藏的（同一個 localStorage）。
用法：python3 patch_etfhide.py       → beta_etfh.html＋beta_scan_etfh.html（獨立檔名）
      python3 patch_etfhide.py prod  → index.html＋scan.html
頁尾版本用正規式換成 v1122u；其餘錨點都要剛好出現一次。
"""
import re, sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'

EDIT = r"""
function etfEditor(){const el=$('tTbl'),H=new Set(store.get('etfHide')||[]),L=(ETFJ&&ETFJ.stocks)||[],nm=c=>(ETFJ.nm&&ETFJ.nm[c]||[c])[0];
  $('tSum').innerHTML=`<span class="asof">✏️ 編輯 ETF 顯示・${L.length} 檔・已隱藏 <b>${H.size}</b> 檔</span><br>按「隱藏」把暫時不看的 ETF 藏起來，首頁主題表、這一頁、分類按鈕、掃描頁都不會出現；資料照常每天更新，之後按「顯示」就回來。設定只存在這支手機。`
    +`<div class="ecb" style="margin-top:8px"><button type="button" data-eh="all">全部顯示</button><button type="button" data-eh="done" aria-pressed="true">✓ 完成</button></div>`;
  $('tUS').innerHTML='';const eb=document.getElementById('ecb');if(eb)eb.remove();
  el.classList.remove('mo');let last='';
  el.innerHTML='<thead><tr><th>ETF</th><th style="text-align:right">顯示</th></tr></thead><tbody>'+L.map(([c,role])=>{const k=(role||'').split('｜')[0],h=H.has(c);
    const g=k!==last?`<tr class="egh"><td colspan="2">${k}</td></tr>`:'';last=k;
    return g+`<tr data-eh="${c}" style="${h?'opacity:.45':''}"><td><span class="nm">${esc(nm(c))}</span><span class="cd">${c}</span><div class="role">${esc((role||'').replace(/^[^｜]*｜/,''))}</div></td>`
      +`<td style="text-align:right"><button type="button" class="ib" data-eh="${c}" style="height:30px;padding:0 12px;font-size:13px">${h?'顯示':'隱藏'}</button></td></tr>`}).join('')+'</tbody>';
  el.onclick=e=>{const b=e.target.closest('button[data-eh]');if(!b)return;etfHideSet(b.dataset.eh)};
  $('tSum').onclick=e=>{const b=e.target.closest('button[data-eh]');if(!b)return;if(b.dataset.eh==='done'){ETFED=0;etfPage()}else etfHideSet('all')};
  $('tFoot').innerHTML='隱藏只影響顯示，不會改名單；名單要增減請告訴 Claude。';
}
function etfHideSet(c){let H=store.get('etfHide')||[];if(c==='all')H=[];else H=H.includes(c)?H.filter(x=>x!==c):[...H,c];store.set('etfHide',H);
  const i=BASE.findIndex(t=>t.id==='etf');if(i>=0){const n=etfTheme()[0];if(n)BASE[i]=n}applyCfg();etfPage()}
"""

I = [
    ("let ETS='',ETC='a',EXD=null,NAVJ=null;", "let ETS='',ETC='a',EXD=null,NAVJ=null,ETFED=0;"),
    ("stocks:ETFJ.stocks.map(([c,n])=>[c,n])}]}",
     "stocks:(()=>{const H=new Set(store.get('etfHide')||[]);return ETFJ.stocks.filter(([c])=>!H.has(c)).map(([c,n])=>[c,n])})()}]}" + EDIT),
    ("function etfPage(){const t0=THEMES.find(x=>x.id==='etf');if(!t0||!ETFJ)return;",
     "function etfPage(){const t0=THEMES.find(x=>x.id==='etf');if(!t0||!ETFJ)return;"
     "{const te=$('tEdit');te.hidden=false;te.textContent=ETFED?'✓ 完成':'✏️ 編輯';te.onclick=e=>{e.preventDefault();ETFED=ETFED?0:1;etfPage()}}"
     "$('tSum').onclick=e=>{const a=e.target.closest('a[data-eh=open]');if(a){e.preventDefault();ETFED=1;etfPage()}};if(ETFED)return etfEditor();"),
    ("點一列看 K 線 (掃描頁)。${(()=>{const U=",
     "點一列看 K 線 (掃描頁)。${(()=>{const H=store.get('etfHide')||[];return H.length?`<br>👁️ <b>已隱藏 ${H.length} 檔</b>：${H.join('、')} (<a href=\"#\" data-eh=\"open\">編輯</a>)`:''})()}${(()=>{const U="),
    ("{const _st=showTheme;showTheme=function(tid){_st(tid);if(tid!=='etf')ETC='a';if(tid==='etf')etfPage();",
     "{const _st=showTheme;showTheme=function(tid){_st(tid);if(tid!=='etf'){ETC='a';ETFED=0;const te=$('tEdit');te.onclick=null;te.textContent='✏️ 編輯'}"
     "if(tid==='etf')etfPage();"),
]

S = [
    ("T.themes=[{id:'etf',name:`📦 ETF${a?` (${+a.slice(4,6)}/${+a.slice(6)})`:''}`,stocks:ETFJ.stocks.map(x=>[x[0],''])},...(T.themes||[])]}",
     "const EH=new Set(store.get('etfHide')||[]);   // 2026-11-22：首頁 ETF 編輯頁隱藏的不顯示\n"
     "  T.themes=[{id:'etf',name:`📦 ETF${a?` (${+a.slice(4,6)}/${+a.slice(6)})`:''}`,stocks:ETFJ.stocks.filter(x=>!EH.has(x[0])).map(x=>[x[0],''])},...(T.themes||[])]}"),
]

I_BETA = [("$('tScan').href='scan.html#'+encodeURIComponent(t.id);", "$('tScan').href=(t.id==='etf'?'beta_scan_etfh.html?v=1#':'scan.html#')+encodeURIComponent(t.id);"),
          ("location.href='scan.html#etf'", "location.href='beta_scan_etfh.html?v=1#etf'")]


def patch(src, dst, edits, extra):
    s = open(src, encoding='utf-8').read()
    for a, b in list(edits) + ([] if prod else list(extra)):
        assert s.count(a) == 1, (src, s.count(a), a[:70])
        s = s.replace(a, b)
    s, nv = re.subn(r'<span style="opacity:\.5">v11\d\d[a-z]</span>', '<span style="opacity:.5">v1122u</span>', s)
    assert nv == 1, (src, nv)
    if not prod:
        s = s.replace('<title>', '<title>[beta] ', 1)
    open(dst, 'w', encoding='utf-8').write(s)
    print('ok', dst)


patch('index.html', 'index.html' if prod else 'beta_etfh.html', I, I_BETA)
patch('scan.html', 'scan.html' if prod else 'beta_scan_etfh.html', S, [])
