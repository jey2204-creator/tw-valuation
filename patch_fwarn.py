"""2026-11-15：把主力訊號統計的結論放回首頁主力訊號表（世杰選「先做推薦的那一項」）
- 每檔的「🆕新進／連 N 天」標籤：點開多一句「這個進場時機過去的勝率、超額」（data/fire_stats.json，隔天收盤買進）
- 該時機過去抱 10 日輸大盤 2 個百分點以上（且 ≥50 筆）→ 標籤變實心橘色「連N天⚠」
- 當天公布的注意名單裡有它：過去抱 5 日有超額但 10 日倒輸 → 多一顆「短線」；10 日輸大盤 2 點以上 →「⚠注意股」
- 表格上方一行摘要「⚠ N 檔…」＋統計頁連結
門檻都讀統計檔即時判斷，樣本變了會自動跟著變（統計改善就不再警示）。
用法：python3 patch_fwarn.py [prod]   （預設 index.html → beta.html）"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
s = open('index.html', encoding='utf-8').read()
assert 'fwarn' not in s
def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)

rep(".flag.fnew{color:var(--up);border-color:var(--up);margin-left:0}.flag.fstk{margin-left:0}",
    ".flag.fnew{color:var(--up);border-color:var(--up);margin-left:0}.flag.fstk{margin-left:0}\n"
    ".flag.fwarn{background:#b45309;border-color:#b45309;color:#fff;font-weight:700}.flag.fshort{color:#b45309;border-color:#b45309;margin-left:0}\n"
    "#hotWarn{font-size:12px;line-height:1.6;white-space:normal;color:var(--fg)}#hotWarn:empty{display:none}#hotWarn b{color:#b45309}")
rep('<div id="hotCtl"></div>', '<div id="hotCtl"></div><p class="foot" id="hotWarn"></p>')   # 結論先行：放在表格上方
rep("let FH=null,FHP=null,", "let FS=null,FH=null,FHP=null,")
rep("function fhLoad(){return FHP||(FHP=fetch('data/fire_hist.json?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).catch(()=>null).then(j=>{FH=j&&j.d?j:{days:[],d:{},x:{}}}))}",
    "function fhLoad(){const g=u=>fetch(u+'?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).catch(()=>null);return FHP||(FHP=Promise.all([g('data/fire_hist.json'),g('data/fire_stats.json')]).then(([j,st])=>{FH=j&&j.d?j:{days:[],d:{},x:{}};FS=st&&st.s?st:null}))}\n"
    "// 統計結論（隔天收盤買進）：fsC(分組, 鍵, 天數)；FMIN 筆以上才採用；FBAD＝抱 10 日輸大盤幾個百分點以上算警示\n"
    "const FMIN=50,FBAD=-0.02,fsP=(x,d=1)=>(x>0?'+':'')+(x*100).toFixed(d)+'%';\n"
    "function fsC(g,k,h){if(!FS)return null;const s=g==='streak'?FS.s:FS.cuts&&FS.cuts[g]&&FS.cuts[g].s,c=s&&s.e1&&s.e1[k]&&s.e1[k][h];return c&&c.n>=FMIN&&c.ex!=null?c:null}\n"
    "const fsTxt=(c,h)=>`抱 ${h} 日勝率 ${(c.win*100).toFixed(0)}%、平均 ${fsP(c.avg)}、${c.ex>=0?'贏':'輸'}大盤 ${Math.abs(c.ex*100).toFixed(1)} 個百分點`;\n"
    "const fsBk=n=>n>=6?'d6':n>=4?'d45':'d'+n;")

a = s.index("  const badge=id=>{const x=st[id];if(!x)return '';")
b = s.index("\n", a)
NEW = r'''  const per=FS?`${ymd(FS.from)}～${ymd(FS.to)}`:'',ntSet=new Set(((NTN&&NTN.asof===day?NTN:NT&&NT.asof===day?NT:null)||{att:[]}).att.map(x=>x.c));   // 跟統計同定義：事件當天公布的注意名單
  const sInfo=n=>{const k=fsBk(n),c5=fsC('streak',k,'5'),c10=fsC('streak',k,'10');return {bad:!!(c10&&c10.ex<=FBAD),txt:c5&&c10?`。📊 這個時機過去 ${c10.n} 筆（${per}，隔天收盤買）：${fsTxt(c5,5)}；${fsTxt(c10,10)}。最差 10% 的情況抱 10 日 ${fsP(c10.p10)}`:''}};
  const nInfo=(()=>{const c5=fsC('nt','att','5'),c10=fsC('nt','att','10');if(!c5||!c10)return null;const bad=c10.ex<=FBAD,short=!bad&&c5.ex>0.01&&c10.ex<0;return bad||short?{bad,txt:`當天列注意股：過去約 ${c5.n} 筆（${per}，隔天收盤買）${fsTxt(c5,5)}；但${fsTxt(c10,10)}，最差 10% 的情況 ${fsP(c10.p10)}。${bad?'過去追進去多半吃虧':'短線動能，不宜久抱'}`}:null})();
  let nBad=0,nNt=0;
  const badge=id=>{const x=st[id];let h='';
    if(x){const si=sInfo(x[0]);if(si.bad)nBad++;
      h=x[0]===1?`<span class="flag fnew${si.bad?' fwarn':''}" data-tip="🆕 新進：${ymd(prev)} 還沒有 🔥，${ymd(day)} 才符合條件（剛啟動）${si.txt}">🆕新進${si.bad?'⚠':''}</span> `
        :`<span class="flag fstk${si.bad?' fwarn':''}" data-tip="已連續 ${x[0]} 個交易日符合 🔥 條件${x[1]?'（歷史只回推到 '+ymd(days[0])+'，實際可能更久）':''}${si.txt||'。連越多天通常越接近注意股，追進的位置越晚'}">連${x[0]}天${x[1]?'+':''}${si.bad?'⚠':''}</span> `}
    if(nInfo&&ntSet.has(id)){nNt++;h+=`<span class="flag ${nInfo.bad?'fwarn':'fshort'}" data-tip="${nInfo.txt}">${nInfo.bad?'⚠注意股':'短線'}</span> `}
    return h};'''
s = s[:a] + NEW + s[b:]

rep("  const X=(FH&&FH.x&&FH.x[day])||{};",
    "  {const c=fsC('streak','d6','10'),w=[];\n"
    "   if(nBad&&c)w.push(`<b>⚠ ${nBad} 檔</b>已連太多天：過去這時才追，抱 10 日勝率 ${(c.win*100).toFixed(0)}%、輸大盤 ${Math.abs(c.ex*100).toFixed(1)} 點`);else if(nBad)w.push(`<b>⚠ ${nBad} 檔</b>的進場時機過去明顯輸大盤`);\n"
    "   if(nNt&&nInfo)w.push(`<b>${nInfo.bad?'⚠ ':''}${nNt} 檔</b>是注意股：${nInfo.bad?'過去追進去多半吃虧':'短線有超額、抱到 10 日倒輸'}`);\n"
    "   $('hotWarn').innerHTML=w.length?w.join('；')+`。點標籤看數字 <a href=\"fstats.html\">統計 ›</a>`:''}\n"
    "  const X=(FH&&FH.x&&FH.x[day])||{};")
rep("<b>🆕新進</b>＝前一個交易日還沒有 🔥；<b>連 N 天</b>＝連續符合的交易日數。",
    "<b>🆕新進</b>＝前一個交易日還沒有 🔥；<b>連 N 天</b>＝連續符合的交易日數。<b>橘底 ⚠</b>＝這個進場時機過去抱 10 日輸大盤 2 個百分點以上；<b>短線</b>＝同時是注意股，過去 5 日有超額、10 日倒輸（都依統計頁的數字即時判斷）。")
rep("<span style=\"opacity:.5\">v1115c</span>", "<span style=\"opacity:.5\">v1115d</span>")
out = 'index.html' if prod else 'beta.html'
open(out, 'w', encoding='utf-8').write(s)
print('ok →', out)
