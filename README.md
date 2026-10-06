# 台股估值看板

iPhone 用的個股估值頁：月營收、三率、EPS、預估 EPS、本益比河流圖、股價淨值比河流圖。
資料由 GitHub Actions 每個交易日 18:40（台北）從 FinMind 自動抓取，存成 `data/*.json`，
網頁放在 GitHub Pages。

## 檔案
| 檔案 | 用途 |
|---|---|
| `index.html` | 網頁本體（讀 `data/{代號}.json`） |
| `fetch.py` | 抓資料腳本（只用 Python 標準函式庫） |
| `.github/workflows/update.yml` | 每日排程 |
| `data/` | 資料檔，Actions 自動更新 |
| `manifest.json`、`icon-*.png` | 加到 iPhone 主畫面用 |

## 新增追蹤股票
編輯 `fetch.py` 第一段的 `STOCKS = ["2330"]`，例如 `["2330", "2344", "6488"]`，
存檔後到 Actions 手動執行一次。網頁左上角的股名可以切換。

## 本機測試
```
python fetch.py 2330
python -m http.server 8000   # 開 http://localhost:8000
```
