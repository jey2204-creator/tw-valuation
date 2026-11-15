"""2026-11-15：注意／處置名單「下個交易日才換」（原本過午夜就換）
起因：11/14（六）XQ 仍顯示 11/12 公布的名單，本站已把 11/13（五）晚上公布的當成「適用」→ 週末跟 XQ 對不上。
規則：最新名單在 applyFrom（名單日的下一個交易日，fetch_notice.py 寫進 notice.json；沒有就取下一個平日）之前都是「🆕 下個交易日」，
     前一份（prev.json）是「適用」。到了 applyFrom 當天（台北日期）才換。
字樣：下個交易日就是明天 → 「明日」；不是（週五晚上～週日、連假）→ 「週一」這種星期幾。
用法：python3 patch_nxtd.py [prod]   （預設 index.html→beta.html、notice.html→beta_notice.html、scan.html→beta_scan_nx.html）"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
def rep(s, a, b, n=1):
    assert s.count(a) == n, (s.count(a), a[:70])
    return s.replace(a, b)
AP = ("const apF=N=>{if(N.applyFrom)return N.applyFrom;const d=new Date(Date.UTC(+N.asof.slice(0,4),+N.asof.slice(4,6)-1,+N.asof.slice(6)));"
      "do{d.setUTCDate(d.getUTCDate()+1)}while(d.getUTCDay()%6===0);return d.toISOString().slice(0,10).replace(/-/g,'')};"
      "const nxLab=(af,td)=>{const D=s=>new Date(Date.UTC(+s.slice(0,4),+s.slice(4,6)-1,+s.slice(6)));return (D(af)-D(td))/864e5===1?'明日':'週'+'日一二三四五六'[D(af).getUTCDay()]};")

# ---------------- notice.html
n = open('notice.html', encoding='utf-8').read()
n = rep(n, "let PREV=null,CURD='',NEXTD='';", "let NXL='明日';   /* 下個交易日的叫法：明日／週一…（2026-11-15） */\n" + AP + "\nlet PREV=null,CURD='',NEXTD='';")
n = rep(n, "if(PREV&&D.asof>=TODAY){CURD=PREV.asof;NEXTD=D.asof}", "if(PREV&&TODAY<apF(D)){CURD=PREV.asof;NEXTD=D.asof;NXL=nxLab(apF(D),TODAY)}")
n = rep(n, '">🆕明日 ${md(NEXTD)}</option>', '">🆕${NXL} ${md(NEXTD)}</option>')
n = rep(n, "stl=`🆕 明日新增 <b>", "stl=`🆕 ${NXL}新增 <b>")
n = rep(n, '>看明日 ›</a>', '>看${NXL} ›</a>')
n = rep(n, "公布・下個交易日適用（XQ 明天才顯示）`", "公布・${NXL==='明日'?'明日':NXL+'（下個交易日）'}適用（XQ 到時才顯示）`")
n = rep(n, """'<span class="tg g">明日續列</span>':ni.mm&&x.m===ni.mm?'<span class="tg g">明日待公布</span>':'<span class="tg a">明日移出</span>'""",
        """`<span class="tg g">${NXL}續列</span>`:ni.mm&&x.m===ni.mm?`<span class="tg g">${NXL}待公布</span>`:`<span class="tg a">${NXL}移出</span>`""")
n = rep(n, "${DAY===CURD&&NEXTD?'（今日適用）':''}", "${DAY===CURD&&NEXTD?'（目前適用）':''}")
n = rep(n, "預設顯示「目前適用」的名單（前一晚公布、今天盤中適用，跟 XQ 同步）；當晚新公布的在日期選單「🆕 明日」。", "預設顯示「目前適用」的名單（前一個交易日晚上公布，跟 XQ 同步）；新公布的在日期選單「🆕 明日／週一」，到下個交易日才換成適用。")
n = rep(n, " v1113i`", " v1115a`")
open('notice.html' if prod else 'beta_notice.html', 'w', encoding='utf-8').write(n)

# ---------------- index.html
s = open('index.html', encoding='utf-8').read()
s = rep(s, "let TOP=null,NT=null,NTN=null;", "let NXL='明日';" + AP + "\nlet TOP=null,NT=null,NTN=null;")
s = rep(s, "if(NT.asof>=TD){const rp=", "if(TD<apF(NT)){const AF=apF(NT);const rp=")
s = rep(s, "if(pv&&pv.asof&&pv.asof<NT.asof){NTN=NT;NT=pv}", "if(pv&&pv.asof&&pv.asof<NT.asof){NTN=NT;NT=pv;NXL=nxLab(AF,TD)}")
s = rep(s, "o.push([NTN.asof,'🆕明日 '+ntMd(NTN.asof)])", "o.push([NTN.asof,'🆕'+NXL+' '+ntMd(NTN.asof)])")
s = rep(s, "(NTN?`今日適用（${ntMd(d)} 公布，同 XQ）`", "(NTN?`目前適用（${ntMd(d)} 公布，同 XQ）`")
s = rep(s, "isNx?`明日適用（${ntMd(d)} 公布）`", "isNx?`${NXL}適用（${ntMd(d)} 公布）`")
s = rep(s, '🆕 明日新增 ${add}・', '🆕 ${NXL}新增 ${add}・')
s = rep(s, '<a href="#" id="ntToNx">看明日 ›</a>', '<a href="#" id="ntToNx">看${NXL} ›</a>')
open('index.html' if prod else 'beta.html', 'w', encoding='utf-8').write(s)

# ---------------- scan.html
c = open('scan.html', encoding='utf-8').read()
c = rep(c, "  let NT=NT0;NXT=null;{const TD=", "  " + AP + "\n  let NT=NT0;NXT=null;{const TD=")
c = rep(c, "PV.asof<NT0.asof&&NT0.asof>=TD){NXT=NT0;NT=PV}", "PV.asof<NT0.asof&&TD<apF(NT0)){NXT=NT0;NT=PV;window.NXL=nxLab(apF(NT0),TD)}")
c = rep(c, "NXT&&d===NXT.asof?'🆕 明日':", "NXT&&d===NXT.asof?'🆕 '+(window.NXL||'明日'):")
open('scan.html' if prod else 'beta_scan_nx.html', 'w', encoding='utf-8').write(c)
print('ok', 'prod' if prod else 'beta')
