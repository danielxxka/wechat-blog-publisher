# wxconverter

[English](#english) | [繁體中文](#繁體中文)

---

## English

A modular Python tool that converts WeChat Official Account articles into clean Markdown files with locally downloaded images. Designed for both human use (CLI) and AI agent integration (MCP server).

### Features

- **Anti-detection scraping** — Uses [Camoufox](https://github.com/nichochar/camoufox) (stealth Firefox) to bypass WeChat's bot detection
- **Smart page loading** — `networkidle` wait instead of hardcoded sleep
- **Retry logic** — 3× exponential backoff for page fetching, 3× linear backoff for image downloads
- **CAPTCHA detection** — Explicit detection with actionable error messages
- **Batch processing** — Multiple URLs via args or file input
- **Image localization** — Concurrent async downloads with Content-Type based extension inference
- **Code block preservation** — Language detection, CSS counter garbage filtering
- **Media extraction** — Handles WeChat's `<mpvoice>` audio and `<mpvideo>` video elements
- **YAML frontmatter** — Structured metadata (title, author, date, source)
- **MCP server** — Expose as tools for any MCP-compatible AI client

### Installation

```bash
git clone https://github.com/bzd6661/wechat-article-for-ai.git
cd wechat-article-for-ai
pip install -r requirements.txt
```

> Camoufox browser will be auto-downloaded on first run.

### Usage

#### CLI — Single Article

```bash
python main.py "https://mp.weixin.qq.com/s/ARTICLE_ID"
```

#### CLI — Batch from File

```bash
python main.py -f urls.txt -o ./output -v
```

#### CLI Options

| Flag | Description |
|------|-------------|
| `urls` | One or more WeChat article URLs |
| `-f, --file FILE` | Text file with URLs (one per line, `#` for comments) |
| `-o, --output DIR` | Output directory (default: `./output`) |
| `-c, --concurrency N` | Max concurrent image downloads (default: 5) |
| `--no-images` | Skip image download, keep remote URLs |
| `--no-headless` | Show browser window (for solving CAPTCHAs) |
| `--force` | Overwrite existing output |
| `--no-frontmatter` | Use blockquote metadata instead of YAML frontmatter |
| `-v, --verbose` | Enable debug logging |

#### MCP Server

Run as an MCP server for AI tool integration:

```bash
python server.py
```

**Tools exposed:**
- `convert_article_tool` — Convert a single WeChat article to Markdown
- `batch_convert_tool` — Convert multiple articles in one call

**MCP client configuration** (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "wxconverter": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/path/to/wxconverter"
    }
  }
}
```

### Output Structure

```
output/
  <article-title>/
    <article-title>.md
    images/
      img_001.png
      img_002.jpg
      ...
```

### Project Structure

```
wxconverter/
  __init__.py        # Package init, public API
  exceptions.py      # CaptchaError, NetworkError, ParseError
  helpers.py         # Logging, filename sanitizer, timestamp, image ext inference
  browser.py         # Camoufox + networkidle + retry with exponential backoff
  html_parser.py     # BeautifulSoup: metadata, code blocks, media, noise removal
  markdown.py        # markdownify + YAML frontmatter + image URL replacement
  images.py          # httpx async + retry per image + Content-Type inference
  workflow.py        # Core conversion logic (shared by CLI and MCP)
  cli.py             # argparse CLI with batch support
  server.py          # FastMCP server with convert_article_tool / batch_convert_tool
main.py              # CLI entry point
server.py            # MCP server entry point
```

### Troubleshooting

| Problem | Solution |
|---------|----------|
| CAPTCHA / verification page | Run with `--no-headless` to solve manually |
| Empty content | WeChat may be rate-limiting; wait and retry |
| Image download failures | Failed images keep remote URLs; re-run with `--force` |
| NS_ERROR_UNKNOWN_HOST | Temporary network issue; wait and retry |

### License

MIT

---

## 繁體中文

一個模組化的 Python 工具，將微信公眾號文章轉換為乾淨的 Markdown 檔案並下載圖片到本地。同時支援人工使用（CLI）和 AI 智能體整合（MCP 伺服器）。

### 功能特點

- **反檢測抓取** — 使用 [Camoufox](https://github.com/nichochar/camoufox)（隱身 Firefox）繞過微信的反爬機制
- **智慧頁面等待** — 使用 `networkidle` 取代硬編碼的 sleep
- **重試機制** — 頁面載入 3 次指數退避重試，圖片下載 3 次線性退避重試
- **驗證碼檢測** — 明確識別驗證碼頁面並給出可操作的錯誤提示
- **批次處理** — 支援多個 URL 參數或從檔案讀取
- **圖片本地化** — 非同步並發下載，基於 Content-Type 推斷圖片格式
- **程式碼區塊保留** — 自動檢測程式語言，過濾 CSS 計數器垃圾文字
- **媒體提取** — 處理微信的 `<mpvoice>` 音訊和 `<mpvideo>` 視訊元素
- **YAML 元資料** — 結構化的 frontmatter（標題、作者、日期、來源）
- **MCP 伺服器** — 暴露為工具，供任何 MCP 相容的 AI 用戶端呼叫

### 安裝

```bash
git clone https://github.com/bzd6661/wechat-article-for-ai.git
cd wechat-article-for-ai
pip install -r requirements.txt
```

> Camoufox 瀏覽器會在首次執行時自動下載。

### 使用方法

#### CLI — 單篇文章

```bash
python main.py "https://mp.weixin.qq.com/s/文章ID"
```

#### CLI — 批次轉換

```bash
python main.py -f urls.txt -o ./output -v
```

#### CLI 參數

| 參數 | 說明 |
|------|------|
| `urls` | 一個或多個微信文章連結 |
| `-f, --file 檔案` | 包含 URL 的文字檔（每行一個，`#` 為註解） |
| `-o, --output 目錄` | 輸出目錄（預設：`./output`） |
| `-c, --concurrency N` | 圖片下載最大並發數（預設：5） |
| `--no-images` | 跳過圖片下載，保留遠端連結 |
| `--no-headless` | 顯示瀏覽器視窗（用於手動解決驗證碼） |
| `--force` | 覆蓋已存在的輸出目錄 |
| `--no-frontmatter` | 使用引用區塊格式的元資料，而非 YAML frontmatter |
| `-v, --verbose` | 啟用除錯日誌 |

#### MCP 伺服器

作為 MCP 伺服器執行，供 AI 工具整合：

```bash
python server.py
```

**暴露的工具：**
- `convert_article_tool` — 轉換單篇微信文章為 Markdown
- `batch_convert_tool` — 批次轉換多篇文章

**MCP 用戶端設定**（如 `claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "wxconverter": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/path/to/wxconverter"
    }
  }
}
```

### 輸出結構

```
output/
  <文章標題>/
    <文章標題>.md
    images/
      img_001.png
      img_002.jpg
      ...
```

### 專案結構

```
wxconverter/
  __init__.py        # 套件初始化，公共 API
  exceptions.py      # CaptchaError, NetworkError, ParseError
  helpers.py         # 日誌、檔名清理、時間戳、圖片格式推斷
  browser.py         # Camoufox + networkidle + 指數退避重試
  html_parser.py     # BeautifulSoup：元資料、程式碼區塊、媒體、噪音移除
  markdown.py        # markdownify + YAML frontmatter + 圖片 URL 替換
  images.py          # httpx 非同步 + 逐圖重試 + Content-Type 推斷
  workflow.py        # 核心轉換邏輯（CLI 和 MCP 共用）
  cli.py             # argparse CLI，支援批次處理
  server.py          # FastMCP 伺服器
main.py              # CLI 進入點
server.py            # MCP 伺服器進入點
```

### 常見問題

| 問題 | 解決方法 |
|------|----------|
| 出現驗證碼 / 環境異常 | 使用 `--no-headless` 手動解決驗證碼 |
| 內容為空 | 微信可能在限流，等幾分鐘再試 |
| 圖片下載失敗 | 失敗的圖片會保留遠端連結，用 `--force` 重新執行 |
| NS_ERROR_UNKNOWN_HOST | 暫時性網路問題，稍後重試即可 |

### 授權條款

MIT
