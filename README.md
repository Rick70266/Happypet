# 寵物好事門市營運數據報告（Streamlit 版）

作品示範頁：用 Streamlit 把 14 間門市的月至今／年至今營運報告做成可互動的網頁。
**所有營運數字皆為作品示範數據，非寵物好事實際營運數據。**

## 這個資料夾裡有什麼

- `app.py`：Streamlit 主程式，**部署時的主檔案一定要選它**。
- `requirements.txt`：Streamlit Cloud 安裝用的套件清單（streamlit、pandas、Pillow、plotly，可點地圖需要 plotly）。
- v2 改動：電腦版地圖縮小為 340px 寬、用 Plotly 疊在台灣圖上可點圖釘切換報告，下方另有 1-14 號按鈕備援；手機版用頂部「手機版」開關完全隱藏地圖、直接看數據；排行不再用可點欄位排序的表格，改用上方「排序依據」下拉重算排名，第 1 名永遠在最上面，手機版排行改為卡片式。
- `stores.csv`：14 間門市的地址、經緯度與示範數據。要換數字、增減門市，改這個檔案就好。
- `assets/taiwan-map.jpg`：台灣地圖底圖，上傳時要保留 `assets/` 資料夾結構。
- `.streamlit/config.toml`：紅色主題設定，可有可無。

## 是不是一定要 app.py？

對，Streamlit 的運作方式就是這樣：

1. GitHub 上放一個 repo，裡面有 `app.py`。
2. Streamlit Cloud 去讀那個 repo，用 `requirements.txt` 安裝套件，再執行 `app.py`。
3. `app.py` 跑起來就是一個網頁，不用另外寫 HTML。

所以你不能只上傳一張 HTML 就叫 Streamlit 跑，**一定要有 `app.py` 當入口**，而且 `app.py` 要放在 repo 的根目錄（最外層），不要包在第二層資料夾裡。

## 上傳到 GitHub 的步驟

1. 到 GitHub 新增一個 repo，例如 `pet-good-report`，先不要勾選 README（避免衝突），或建好後再覆蓋。
2. 把這個資料夾裡的**全部檔案**，照原來的資料夾結構上傳，確認根目錄有 `app.py`、`requirements.txt`、`stores.csv`，而且有 `assets/taiwan-map.jpg`。
   - 網頁上傳：GitHub repo 頁面按 `Add file` → `Upload files`，把檔案拖進去，記得 `assets/` 也要一起上傳。
   - 或用 Git 指令（在這個資料夾裡執行）：
     ```bash
     git init
     git add .
     git commit -m "Pet Good store report"
     git branch -M main
     git remote add origin https://github.com/你的帳號/pet-good-report.git
     git push -u origin main
     ```
3. 上傳完成後，檢查 GitHub 上 `app.py` 是在根目錄，不是 `pet-good-streamlit/app.py` 這種第二層。

## 部署到 Streamlit Cloud 的步驟

1. 打開 https://share.streamlit.io ，用 GitHub 帳號登入。
2. 按 `Create app`（或 `New app`）。
3. 選你的 repo（`pet-good-report`）、branch（`main`）、主檔案填 `app.py`。
4. 按 `Deploy`，等它安裝完成，畫面會給你一個 `https://xxx.streamlit.app` 的網址，那就是可以分享的網頁。
5. 之後只要在 GitHub 上改 `stores.csv` 或 `app.py` 並 push，Streamlit Cloud 就會自動重新部署，不用重走一次流程。

## 在自己電腦先試跑（可選）

```bash
pip install -r requirements.txt
streamlit run app.py
```

瀏覽器會自動開 `http://localhost:8501`。

## 常見問題

- **Deploy 失敗說找不到 app.py**：通常是 `app.py` 不在根目錄，檢查 GitHub 上的路徑。
- **地圖破圖**：通常是 `assets/taiwan-map.jpg` 沒一起上傳，或資料夾名稱打錯。
- **改了 CSV 但畫面沒變**：等 Streamlit 重新部署完成再重新整理，或按右上角 `Reboot app`。
- **免費版會休眠**：Streamlit Cloud 免費版久沒人開會休眠，下次點開要等它喚醒一下，這是正常的。
- **想要純靜態網頁、不用 Python**：那就不要走 Streamlit，改用 GitHub Pages 放 HTML 版；Streamlit 的優點是可以用 Python、CSV 直接做篩選、排序和計算，比較適合展示數據整理邏輯。
