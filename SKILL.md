---
name: wxconverter
description: 將微信公眾號文章轉換為 Markdown 檔案，支援圖片下載和 YAML 元資料。
---

# 微信文章轉 Markdown 轉換器

## 功能說明

將微信公眾號文章轉換為乾淨的 Markdown 檔案：
- YAML frontmatter（標題、作者、日期、來源）
- 本地下載的圖片
- 保留程式碼區塊和語言標籤
- 音視訊引用提取
- 清理微信 UI 噪音

## 系統需求

- Python 3.10+
- 安裝依賴：`pip install -r requirements.txt`
- 首次執行時會自動下載 Camoufox 瀏覽器

## 使用方法

### CLI（單篇文章）

```bash
python main.py "https://mp.weixin.qq.com/s/文章ID"
```

### CLI（批次處理）

```bash
python main.py -f urls.txt -o ./output -v
```

### CLI 參數

| 參數 | 說明 |
|------|------|
| `-f 檔案` | 包含 URL 的文字檔（每行一個，# 為註解） |
| `-o 目錄` | 輸出目錄（預設：./output） |
| `-c N` | 圖片下載並發數（預設：5） |
| `--no-images` | 跳過圖片下載，保留遠端連結 |
| `--no-headless` | 顯示瀏覽器視窗（用於處理驗證碼） |
| `--force` | 覆蓋已存在的輸出 |
| `--no-frontmatter` | 使用引用區塊格式的元資料 |
| `-v` | 啟用除錯日誌 |

### MCP 伺服器

作為 MCP 伺服器執行，供 AI 工具整合：

```bash
python server.py
```

提供的工具：
- `convert_article_tool` — 轉換單篇文章
- `batch_convert_tool` — 批次轉換多篇文章

### MCP 設定（claude_desktop_config.json）

```json
{
  "mcpServers": {
    "wxconverter": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "<專案路徑>"
    }
  }
}
```

## 輸出結構

```
output/
  <文章標題>/
    <文章標題>.md    # Markdown 檔案（含 YAML frontmatter）
    images/
      img_001.png
      img_002.jpg
      ...
```

## 常見問題

- **驗證碼/環境異常**：使用 `--no-headless` 參數手動處理驗證碼
- **內容為空**：微信可能在限流，稍等幾分鐘再試
- **圖片下載失敗**：失敗的圖片會保留遠端連結，使用 `--force` 重試
- **NS_ERROR_UNKNOWN_HOST**：暫時性網路問題，稍後重試即可
