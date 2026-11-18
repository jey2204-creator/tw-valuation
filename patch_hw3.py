#!/usr/bin/env python3
"""2026-11-18 全站全形括號／斜線改半形（世杰：③ 全站全形符號都換）。
只動「畫面文字」：HTML 文字與屬性、JS 字串與樣板字串的文字部分；
另在每頁 <head> 最前面插一小段 HWJ：本站 data/ 底下的 JSON 讀進來時，把字串「值」裡的全形括號／斜線也轉半形
（ai.json 說明、成份股備註、注意原因、公告原文…；鍵名不動，data 檔本身與 fetch_*.py 都不改）。
不動：JS 註解、正規表示式、<style>、KEEP 清單（拿來比對資料來源原文的字串）。
  （ → ' ('（前面已是空白／開頭符號就不加空白）   ） → ')'（後面接中文、英數就補一個空白）   ／ → '/'
用法：python3 patch_hw3.py            → 各頁的 beta（見 PAGES）
      python3 patch_hw3.py prod       → 直接改正式版各頁
      python3 patch_hw3.py report     → 只列出統計與可疑字串，不寫檔
"""
import sys,re
PAGES={'index.html':'beta.html','scan.html':'beta_scan_hw.html','notice.html':'beta_notice.html','flash.html':'beta_flash.html',
       'fstats.html':'beta_fstats.html','stats.html':'beta_stats.html','health.html':'beta_health.html','macro.html':'beta_macro.html'}
KEEP=set()   # 由 hw3_keep.txt 讀入：整個字串（去引號）完全相同就不轉
try:
    KEEP={l.rstrip('\n') for l in open('hw3_keep.txt',encoding='utf-8') if l.strip() and not l.startswith('#')}
except FileNotFoundError:pass
FW='（）／'
OPENERS=set(' \t\n　>([{「『《〈"\'`—–-/:：，、。；')
def isword(c):return c.isalnum() or '一'<=c<='鿿' or '぀'<=c<='ヿ'
def conv(seg,prev='',nxt=''):
    """prev/nxt＝片段外緊鄰的字元（''＝字串開頭／結尾）"""
    if not any(c in seg for c in FW):return seg
    o=[]
    for i,c in enumerate(seg):
        if c=='（':
            p=o[-1][-1] if o else prev
            if p=='>' and o:   # 接在結尾標籤（</b>、</strong>…）後面要空一格；開頭標籤後面不用
                t=''.join(o);k=t.rfind('<')
                if k>=0 and t[k+1:k+2]=='/':p='x'
            o.append('(' if (p!='' and p in OPENERS) else ' (')
        elif c=='）':
            n=seg[i+1] if i+1<len(seg) else nxt
            o.append(') ' if (n and isword(n)) else ')')
        elif c=='／':o.append('/')
        else:o.append(c)
    return ''.join(o)
KW={'return','typeof','case','in','of','delete','void','throw','new','else','do','instanceof','yield','await'}
class JS:
    def __init__(s,src,stats,sus):s.s=src;s.stats=stats;s.sus=sus
    def run(s,i=0,stop=None):
        """回傳 (轉換後字串, 結束位置)。stop='}' 時在對應的右大括號停。"""
        src=s.s;n=len(src);out=[];last='';word='';depth=0
        while i<n:
            c=src[i]
            if stop and c=='}' and depth==0:return ''.join(out),i
            if c in '{':depth+=1
            if c in '}':depth-=1
            if src.startswith('//',i):
                j=src.find('\n',i);j=n if j<0 else j;out.append(src[i:j]);i=j;continue
            if src.startswith('/*',i):
                j=src.find('*/',i);j=n if j<0 else j+2;out.append(src[i:j]);i=j;continue
            if c in '\'"':
                j=i+1
                while j<n and src[j]!=c:
                    j+=2 if src[j]=='\\' else 1
                body=src[i+1:j];out.append(c+s.lit(body,src,i,j)+c);i=j+1;last=c;word='';continue
            if c=='`':
                j=i+1;out.append('`');seg_start=j
                while j<n and src[j]!='`':
                    if src[j]=='\\':j+=2;continue
                    if src.startswith('${',j):
                        out.append(s.lit(src[seg_start:j],src,seg_start-1,j,tpl=True));out.append('${')
                        inner,k=JS(src,s.stats,s.sus).run(j+2,'}');out.append(inner);out.append('}');j=k+1;seg_start=j;continue
                    j+=1
                out.append(s.lit(src[seg_start:j],src,seg_start-1,j,tpl=True));out.append('`');i=j+1;last='`';word='';continue
            if c=='/':
                if last=='' or last in '(,=:[!&|?{};+-*%<>~^}' or word in KW:
                    j=i+1;cls=False
                    while j<n and (src[j]!='/' or cls):
                        if src[j]=='\\':j+=2;continue
                        if src[j]=='[':cls=True
                        elif src[j]==']':cls=False
                        elif src[j]=='\n':break
                        j+=1
                    if j<n and src[j]=='/':
                        j+=1
                        while j<n and src[j].isalpha():j+=1
                        r=src[i:j]
                        if any(x in r for x in FW):s.stats['regex']+=1;s.sus.append(('REGEX',r))
                        out.append(r);i=j;last=')';word='';continue
            out.append(c)
            if c.isalnum() or c in '_$':word=(word+c) if (last=='w') else c;last='w'
            elif not c.isspace():last=c;word=''
            i+=1
        return ''.join(out),i
    def lit(s,body,src,a,b,tpl=False):
        if not any(x in body for x in FW):return body
        if body in KEEP:s.stats['keep']+=1;return body
        s.stats['str']+=sum(body.count(x) for x in FW)
        # 可疑：短、沒有 HTML、前後像是在做比對／查表
        pre=src[max(0,a-28):a];post=src[b+1:b+10] if not tpl else src[b:b+10]
        logic=re.search(r"(===?|!==?|includes\(|indexOf\(|startsWith\(|endsWith\(|split\(|replace\(|replaceAll\(|match\(|test\(|RegExp\(|case |\[|find\(|get\(|has\(|in )\s*$",pre) or re.match(r"\s*(\]|:|===?|!==?|\.split|\.test|in )",post)
        if not tpl and len(body)<30 and '<' not in body and (logic or re.search(r",\s*$",pre)):
            s.sus.append(('STR',pre[-22:].replace('\n',' ')+'⟦'+body+'⟧'+post.replace('\n',' ')))
        pv='' ;nx=''
        if tpl:
            pv='' if src[a]=='`' else '}';nx='' if src[b:b+1]=='`' else '$'
            pv=' ' if False else pv
        return conv(body,prev=('x' if pv=='}' else ''),nxt='')
def html(src,stats,sus):
    out=[];i=0;n=len(src)
    for m in re.finditer(r'<!--.*?-->|<script\b[^>]*>(.*?)</script>|<style\b[^>]*>.*?</style>',src,re.S|re.I):
        out.append(markup(src[i:m.start()],stats))
        t=m.group(0)
        if t[:7].lower()=='<script' and m.group(1) and not re.search(r'type="application/(ld\+)?json"',t[:200]):
            a,b=m.start(1)-m.start(),m.end(1)-m.start()
            js,_=JS(m.group(1),stats,sus).run();t=t[:a]+js+t[b:]
        out.append(t);i=m.end()
    out.append(markup(src[i:],stats));return ''.join(out)
def markup(seg,stats):
    def f(m):
        t=m.group(0)
        if any(x in t for x in FW):stats['html']+=sum(t.count(x) for x in FW)
        if t.startswith('<'):   # 標籤：只轉屬性值
            return re.sub(r'(=")([^"]*)(")',lambda a:a.group(1)+conv(a.group(2))+a.group(3),t)
        return conv(t,prev='>')
    return re.sub(r'<[^>]*>|[^<]+',f,seg)
HWJ=("<script>/* hwj 2026-11-18：本站 data/ 的 JSON 文字全形括號／斜線→半形（只轉值、不轉鍵） */"
"(()=>{const O=' \\t\\n\\u3000>([{「『《〈\\\"\\'`—–-/:：，、。；',F=/[（）／]/,"
"hw=s=>F.test(s)?s.replace(/([\\s\\S]?)（/g,(m,p)=>p+(p===''||O.includes(p)?'(':' (')).replace(/）(?=[0-9A-Za-z\\u3040-\\u30ff\\u4e00-\\u9fff])/g,') ').replace(/）/g,')').replace(/／/g,'/'):s,"
"dp=o=>{if(typeof o==='string')return hw(o);if(Array.isArray(o)){for(let i=0;i<o.length;i++){const v=o[i];if(typeof v==='string'||(v&&typeof v==='object'))o[i]=dp(v)}}"
"else if(o&&typeof o==='object'){for(const k in o){const v=o[k];if(typeof v==='string'||(v&&typeof v==='object'))o[k]=dp(v)}}return o},"
"J=Response.prototype.json;window.hwText=hw;"
"Response.prototype.json=function(){let u='';try{u=new URL(this.url)}catch(e){}"
"if(!u||u.origin!==location.origin||!/\\/data\\//.test(u.pathname))return J.call(this);"
"return this.text().then(t=>{const o=JSON.parse(t);return F.test(t)?dp(o):o})}})()</script>")
def inject(o):
    if 'hwj 2026-11-18' in o:return o
    i=o.lower().find('<head');j=o.find('>',i)+1 if i>=0 else None
    if j is None:
        m=re.search(r'<meta charset[^>]*>',o);j=m.end()
    return o[:j]+HWJ+o[j:]
if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'beta'
    for src,dst in PAGES.items():
        s=open(src,encoding='utf-8').read();stats=dict(str=0,html=0,regex=0,keep=0);sus=[]
        o=html(s,stats,sus)
        left=sum(o.count(x) for x in FW);o=inject(o)
        if src=='index.html':o=o.replace('<span style="opacity:.5">v1118e</span>','<span style="opacity:.5">v1118f</span>')
        print('%-12s 轉 %4d（JS字串 %d、HTML %d） 保留 %d（正規式 %d、KEEP %d、其餘＝註解／樣式）'%(src,stats['str']+stats['html'],stats['str'],stats['html'],left,stats['regex'],stats['keep']))
        if mode=='report':
            open('/tmp/t/sus_'+src+'.txt','w',encoding='utf-8').write('\n'.join(k+' '+v for k,v in sus))
            open('/tmp/t/out_'+src,'w',encoding='utf-8').write(o);continue
        if mode!='prod':
            o=o.replace('<title>','<title>[beta] ',1)
            # beta 互相連到 beta（方便整站一起看）；prod 不做這步
            o=re.sub(r'(?<![\w/])(index|scan|notice|flash|fstats|stats|health|macro)\.html',lambda m:PAGES[m.group(1)+'.html'],o)
        open(src if mode=='prod' else dst,'w',encoding='utf-8').write(o)
