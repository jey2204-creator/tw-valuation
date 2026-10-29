"""每日更新各步驟的健康檢查 → data/run_status.json ＋ Telegram 通知

為什麼要有：update.yml 的抓資料步驟都設 continue-on-error（一支壞了不拖累其他），
但這樣程式當掉時整個排程仍顯示「成功」。2026/10/28～29 動能程式 IndexError 停擺兩天，
網頁只寫「排程可能延遲」，沒人發現 → 補這支：
  1. 讀 GitHub Actions 傳進來的各步驟結果（STEP_<id>=success/failure/skipped）
  2. 失敗的步驟從 $RUNNER_TEMP/<id>.log 抓最後幾行錯誤訊息
  3. 另外檢查「程式沒當掉但資料沒前進」：momentum.json 的日期落後 data/hist 最新交易日
  4. 寫 data/run_status.json（網頁橫幅讀它，改顯示「程式出錯」而不是「排程延遲」）
  5. 只在「新壞掉」或「修好了」時推 Telegram（排程一天跑 6 次以上，避免洗版）
狀態沒變就不改檔，避免每次排程都多一個 commit。
"""
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = DATA / "run_status.json"
SITE = "https://jey2204-creator.github.io/tw-valuation/"
TMP = Path(os.environ.get("RUNNER_TEMP", "/tmp"))

# 步驟 id → 顯示名稱（id 要跟 update.yml 的 steps.<id> 一致）
STEPS = {
    "sum": "全市場摘要（收盤、主題頁）",
    "sal": "員工薪資中位數",
    "hc": "員工人數",
    "mom": "動能（價量＋法人）",
    "chip": "逐日籌碼＋K 線",
    "tdcc": "集保大戶",
    "main": "個股財報",
}


def now_tpe():
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) + dt.timedelta(hours=8)


def load(p, d):
    try:
        return json.loads(Path(p).read_text("utf-8"))
    except Exception:  # noqa: BLE001
        return d


def err_tail(sid):
    """抓 log 最後一個 Traceback 的最後一行（例：IndexError: list index out of range）"""
    t = ""
    try:
        t = (TMP / f"{sid}.log").read_text("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return "（沒有錯誤紀錄）"
    lines = [x.strip() for x in t.splitlines() if x.strip()]
    hit = [x for x in lines if re.match(r"^[A-Za-z_.]*(Error|Exception|Interrupt)\b", x) or x.startswith("Traceback")]
    last = [x for x in hit if not x.startswith("Traceback")]
    msg = last[-1] if last else (lines[-1] if lines else "（沒有輸出）")
    # 錯在哪一行：Traceback 裡最後一個 File "...", line N
    loc = re.findall(r'File "[^"]*?([\w]+\.py)", line (\d+)', t)
    if loc:
        msg = f"{msg}（{loc[-1][0]} 第 {loc[-1][1]} 行）"
    return msg[:200]


def latest_trade_day():
    """data/hist 裡最新、不是休市、有收盤的那天"""
    for f in sorted((DATA / "hist").glob("*.json"), reverse=True):
        r = load(f, {})
        if not r.get("closed") and r.get("p") and not r.get("slim"):
            return f.stem
    return None


def check():
    st = {}
    t = now_tpe().strftime("%Y-%m-%d %H:%M")
    for sid, name in STEPS.items():
        o = os.environ.get(f"STEP_{sid}", "")
        if o == "failure":
            st[sid] = {"ok": False, "name": name, "err": err_tail(sid), "at": t}
        elif o == "success":
            st[sid] = {"ok": True, "name": name}
    # 資料沒前進（程式沒當掉，但 momentum.json 日期落後 hist）
    if st.get("mom", {}).get("ok"):
        mo, last = load(DATA / "momentum.json", {}).get("asof"), latest_trade_day()
        if mo and last and mo < last:
            st["mom"] = {"ok": False, "name": STEPS["mom"], "at": t,
                         "err": f"程式有跑完但資料停在 {mo[4:6]}/{mo[6:]}（已抓到 {last[4:6]}/{last[6:]} 的原始資料）"}
    return st


def tg_send(text):
    tok = os.environ.get("TELEGRAM_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID") or load(DATA / "flash" / "tg.json", {}).get("chat")
    if not tok or not chat:
        return "沒設 TELEGRAM_TOKEN 或 chat id，跳過推播"
    r = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage",
                               data=json.dumps({"chat_id": chat, "text": text, "parse_mode": "HTML",
                                                "disable_web_page_preview": True}).encode(),
                               headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            return "ok" if json.loads(resp.read().decode()).get("ok") else "失敗"
    except Exception as e:  # noqa: BLE001
        return f"失敗：{e}"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    old = load(OUT, {}).get("steps", {})
    new = check()
    if os.environ.get("TG_TEST") == "1":
        bad = [v["name"] for v in new.values() if not v["ok"]]
        print("Telegram 測試：", tg_send("🧪 健康檢查測試：之後每日更新有步驟當掉會發這種通知\n本次結果："
                                        + ("❌ " + "、".join(bad) if bad else "✅ 全部正常")))
    # 沒跑到的步驟沿用舊狀態
    merged = {**old, **new}
    # 失敗時間：連續失敗保留「第一次壞掉」的時間，另記最近一次
    for sid, v in merged.items():
        o = old.get(sid, {})
        if not v.get("ok") and not o.get("ok", True) and o.get("since"):
            v["since"] = o["since"]
        elif not v.get("ok"):
            v["since"] = v.get("at")
    broke = [s for s, v in new.items() if not v["ok"] and old.get(s, {}).get("ok", True)]
    fixed = [s for s, v in new.items() if v["ok"] and old.get(s, {}).get("ok") is False]

    def strip(d):
        return {k: {x: y for x, y in v.items() if x != "at"} for k, v in d.items()}
    if strip(merged) == strip(old) and not broke and not fixed:
        print("各步驟狀態沒變，不改檔")
        return
    msg = []
    if broke:
        msg.append("❌ <b>台股網站每日更新出錯</b>")
        msg += [f"・{esc(merged[s]['name'])}：{esc(merged[s]['err'])}" for s in broke]
        msg.append("網頁資料會停在上次成功那天，請找 Claude 修。")
    if fixed:
        msg.append("✅ <b>已恢復正常</b>：" + "、".join(esc(merged[s]["name"]) for s in fixed))
    res = None
    if msg:
        res = tg_send("\n".join(msg + [f'<a href="{SITE}">開網站</a>']))
    OUT.write_text(json.dumps({"updated": now_tpe().strftime("%Y-%m-%d %H:%M"), "steps": merged},
                              ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"run_status.json 已更新；新壞掉 {broke}，修好 {fixed}，推播：{res}")


if __name__ == "__main__":
    main()
