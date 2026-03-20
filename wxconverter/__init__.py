"""
微信公众号文章转 Markdown 转换器

将微信公众号文章转换为干净的 Markdown 文件，
并下载图片到本地。

使用方法：
    from wxconverter import convert_article

    result = await convert_article("https://mp.weixin.qq.com/s/xxx")
    if result.success:
        print(f"已保存到: {result.output_path}")
"""

__version__ = "2.1.0"

# 核心转换函数
from .workflow import convert_article, ConversionResult

# Markdown 转换
from .markdown import (
    build_markdown,
    convert_html_to_markdown,
    replace_image_urls,
)

# 图片下载
from .images import download_all_images

# 异常类
from .exceptions import (
    WxConverterError,
    CaptchaError,
    NetworkError,
    ParseError,
)

# 数据类
from .html_parser import (
    ArticleMetadata,
    CodeBlock,
    MediaReference,
    ParsedContent,
    extract_metadata,
    process_content,
)

# 浏览器抓取
from .browser import fetch_page_html

# 向后兼容：保留旧的异常类名
WechatToMdError = WxConverterError

# 公开的 API
__all__ = [
    # 版本
    "__version__",
    # 核心转换
    "convert_article",
    "ConversionResult",
    # Markdown
    "build_markdown",
    "convert_html_to_markdown",
    "replace_image_urls",
    # 图片
    "download_all_images",
    # 异常
    "WxConverterError",
    "CaptchaError",
    "NetworkError",
    "ParseError",
    # 向后兼容
    "WechatToMdError",
    # 数据类
    "ArticleMetadata",
    "CodeBlock",
    "MediaReference",
    "ParsedContent",
    "extract_metadata",
    "process_content",
    # 浏览器
    "fetch_page_html",
]
