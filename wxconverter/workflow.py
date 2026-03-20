"""
核心转换逻辑模块

提供统一的 convert_article 函数，供 CLI 和 MCP 服务器共同使用。
这是整个工具的核心，完成从微信文章 URL 到 Markdown 文件的完整转换流程。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup

from .exceptions import CaptchaError, NetworkError, ParseError, WxConverterError
from .helpers import get_logger, sanitize_filename
from .html_parser import extract_metadata, process_content
from .markdown import build_markdown, convert_html_to_markdown, replace_image_urls
from .browser import fetch_page_html
from .images import download_all_images


@dataclass
class ConversionResult:
    """
    文章转换结果

    Attributes:
        success: 转换是否成功
        title: 文章标题
        author: 作者名称
        publish_time: 发布时间
        output_path: 输出的 Markdown 文件路径
        image_count: 下载的图片数量
        char_count: Markdown 文件的字符数
        error: 错误信息（如果有）
        error_type: 错误类型 ("captcha", "network", "parse", "unknown")
    """
    success: bool
    title: str = ""
    author: str = ""
    publish_time: str = ""
    output_path: Path | None = None
    image_count: int = 0
    char_count: int = 0
    error: str | None = None
    error_type: str | None = None


async def convert_article(
    url: str,
    output_dir: Path | str = "./output",
    *,
    headless: bool = True,
    download_images: bool = True,
    concurrency: int = 5,
    force: bool = False,
    use_frontmatter: bool = True,
) -> ConversionResult:
    """
    将微信公众号文章转换为 Markdown 文件

    这是核心转换函数，CLI 和 MCP 服务器都调用此函数。

    Args:
        url: 微信公众号文章链接（必须以 https://mp.weixin.qq.com/ 开头）
        output_dir: 输出目录（默认：./output）
        headless: 是否使用无头模式（默认：True）
        download_images: 是否下载图片到本地（默认：True）
        concurrency: 图片下载并发数（默认：5）
        force: 是否覆盖已存在的输出（默认：False）
        use_frontmatter: 是否使用 YAML frontmatter（默认：True）

    Returns:
        ConversionResult: 转换结果对象，包含成功状态、元数据和错误信息
    """
    logger = get_logger()
    output_path = Path(output_dir)

    # 用于保存调试 HTML 的辅助函数
    def save_debug_html(html: str, url: str) -> Path | None:
        """保存 HTML 用于调试"""
        if not html:
            return None
        debug_dir = output_path / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        suffix = sanitize_filename(url[-30:]) if len(url) > 30 else sanitize_filename(url)
        debug_path = debug_dir / f"debug_{suffix}.html"
        debug_path.write_text(html, encoding="utf-8")
        return debug_path

    html = ""
    try:
        # 第 1 步：获取页面 HTML
        # 使用 Camoufox 浏览器获取渲染后的页面内容
        html = await fetch_page_html(url, headless=headless)

        # 第 2 步：解析元数据
        # 提取标题、作者、发布时间等基本信息
        soup = BeautifulSoup(html, "html.parser")
        meta = extract_metadata(soup, html, url=url)

        if not meta.title:
            raise ParseError(
                "无法提取文章标题。页面可能是验证码页面或无效文章。"
            )

        logger.info(f"标题: {meta.title}")
        if meta.author:
            logger.info(f"作者: {meta.author}")

        # 第 3 步：处理文章内容
        # 提取正文 HTML、代码块、图片 URL 和媒体引用
        parsed = process_content(soup)

        if not parsed.content_html.strip():
            raise ParseError("处理后文章内容为空。")

        # 第 4 步：转换为 Markdown
        md = convert_html_to_markdown(parsed.content_html, parsed.code_blocks)

        # 第 5 步：准备输出目录
        # 使用清理后的标题作为目录名
        safe_title = sanitize_filename(meta.title)
        article_dir = output_path / safe_title

        # 检查是否已存在（非 force 模式下跳过）
        if article_dir.exists() and not force:
            logger.info(f"跳过（已存在）: {article_dir}")
            logger.info("使用 --force 覆盖。")
            return ConversionResult(
                success=True,
                title=meta.title,
                author=meta.author,
                publish_time=meta.publish_time,
                output_path=article_dir / f"{safe_title}.md",
            )

        article_dir.mkdir(parents=True, exist_ok=True)

        # 第 6 步：下载图片
        # 并发下载所有图片，并建立 URL 到本地路径的映射
        if download_images and parsed.image_urls:
            img_dir = article_dir / "images"
            url_map = await download_all_images(
                parsed.image_urls, img_dir, concurrency=concurrency
            )
            # 将 Markdown 中的远程图片 URL 替换为本地路径
            md = replace_image_urls(md, url_map)

        # 第 7 步：构建最终 Markdown 文件
        # 添加元数据（frontmatter 或引用块）和媒体引用
        final_md = build_markdown(
            meta, md, parsed.media_references, use_frontmatter=use_frontmatter
        )

        # 第 8 步：写入文件
        md_path = article_dir / f"{safe_title}.md"
        md_path.write_text(final_md, encoding="utf-8")

        logger.info(f"已保存: {md_path} ({len(final_md)} 字符, {len(parsed.image_urls)} 张图片)")

        return ConversionResult(
            success=True,
            title=meta.title,
            author=meta.author,
            publish_time=meta.publish_time,
            output_path=md_path,
            image_count=len(parsed.image_urls),
            char_count=len(final_md),
        )

    except CaptchaError as e:
        logger.error(f"验证码: {e}")
        debug_path = save_debug_html(html, url)
        return ConversionResult(
            success=False,
            error=str(e),
            error_type="captcha",
        )

    except NetworkError as e:
        logger.error(f"网络错误: {e}")
        return ConversionResult(
            success=False,
            error=str(e),
            error_type="network",
        )

    except ParseError as e:
        logger.error(f"解析错误: {e}")
        debug_path = save_debug_html(html, url)
        return ConversionResult(
            success=False,
            error=str(e),
            error_type="parse",
        )

    except WxConverterError as e:
        logger.error(f"错误: {e}")
        return ConversionResult(
            success=False,
            error=str(e),
            error_type="unknown",
        )

    except Exception as e:
        logger.error(f"未知错误: {e}", exc_info=True)
        debug_path = save_debug_html(html, url)
        return ConversionResult(
            success=False,
            error=str(e),
            error_type="unknown",
        )
