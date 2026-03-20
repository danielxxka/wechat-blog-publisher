"""
工具函数模块

提供各种通用工具函数：
- 日志配置和获取
- 文件名清理
- 时间戳格式化
- 图片扩展名推断
- URL 文件读取
"""

from __future__ import annotations

import logging
import mimetypes
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# 上海时区（UTC+8），用于格式化微信文章的发布时间
SHANGHAI_TZ = timezone(timedelta(hours=8))

# 包级别的日志器名称
LOGGER_NAME = "wxconverter"


def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    配置并返回包级别的日志器

    Args:
        verbose: 是否启用调试级别日志

    Returns:
        配置好的 Logger 对象
    """
    logger = logging.getLogger(LOGGER_NAME)
    # 避免重复添加 handler
    if logger.handlers:
        return logger

    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)

    handler = logging.StreamHandler()
    handler.setLevel(level)

    # 日志格式：时间 [级别] 消息
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    handler.setFormatter(fmt)
    logger.addHandler(handler)

    return logger


def get_logger() -> logging.Logger:
    """
    获取包级别的日志器

    Returns:
        Logger 对象
    """
    return logging.getLogger(LOGGER_NAME)


def sanitize_filename(name: str, max_length: int = 80) -> str:
    """
    清理文件名，移除或替换无效字符

    Args:
        name: 原始文件名
        max_length: 最大长度限制（默认 80）

    Returns:
        清理后的安全文件名
    """
    # 替换 Windows 文件系统不允许的字符
    sanitized = re.sub(r'[\\/:*?"<>|\r\n]+', "_", name.strip())
    # 合并连续的下划线
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    # 截断到最大长度，并移除末尾的标点
    return sanitized[:max_length].rstrip("_. ")


def format_timestamp(ts: int | str) -> str:
    """
    将 Unix 时间戳转换为本地化时间字符串

    使用上海时区（UTC+8）格式化为 'YYYY-MM-DD HH:MM:SS'。

    Args:
        ts: Unix 时间戳（秒），可以是整数或字符串

    Returns:
        格式化的时间字符串，解析失败返回空字符串
    """
    try:
        ts_int = int(ts)
        dt = datetime.fromtimestamp(ts_int, tz=SHANGHAI_TZ)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueValue, TypeError, OSError):
        return ""


def infer_image_extension(url: str, content_type: str | None = None) -> str:
    """
    推断图片文件的扩展名

    按以下优先级判断：
    1. URL 中的 wx_fmt 参数（微信 CDN 特有）
    2. Content-Type 响应头
    3. URL 路径中的扩展名
    4. 默认返回 'png'

    Args:
        url: 图片 URL
        content_type: HTTP 响应的 Content-Type 头

    Returns:
        图片扩展名（不含点号）
    """
    # 1. 检查 wx_fmt 参数（微信 CDN 特有的格式参数）
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        if "wx_fmt" in params:
            fmt = params["wx_fmt"][0].lower()
            if fmt in ("png", "jpg", "jpeg", "gif", "webp", "svg", "bmp"):
                return "jpg" if fmt == "jpeg" else fmt
    except Exception:
        pass

    # 2. 从 Content-Type 推断
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext:
            ext = ext.lstrip(".")
            return "jpg" if ext == "jpeg" else ext

    # 3. 从 URL 路径推断
    match = re.search(r"\.([a-zA-Z]{3,4})(?:\?|$|#)", url)
    if match:
        ext = match.group(1).lower()
        if ext in ("png", "jpg", "jpeg", "gif", "webp", "svg", "bmp"):
            return "jpg" if ext == "jpeg" else ext

    # 4. 默认 png
    return "png"


def read_urls_from_file(filepath: Path) -> list[str]:
    """
    从文本文件读取 URL 列表

    文件格式：每行一个 URL，支持 # 开头的注释行。

    Args:
        filepath: URL 文件路径

    Returns:
        URL 列表
    """
    urls: list[str] = []
    text = filepath.read_text(encoding="utf-8")

    for line in text.splitlines():
        line = line.strip()
        # 跳过空行和注释
        if not line or line.startswith("#"):
            continue
        # 只保留 http(s) 开头的链接
        if line.startswith("http"):
            urls.append(line)

    return urls
