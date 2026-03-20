"""
MCP 服务器模块

将微信公众号文章转换功能暴露为 MCP 工具，
支持任何 MCP 兼容的 AI 客户端调用。

提供的工具：
- convert_article: 转换单篇文章
- batch_convert: 批量转换多篇文章
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .helpers import setup_logging
from .workflow import convert_article, ConversionResult

# 创建 MCP 服务器实例
mcp = FastMCP(name="wxconverter")


def _format_result(result: ConversionResult) -> str:
    """
    格式化转换结果为可读字符串

    Args:
        result: 转换结果对象

    Returns:
        格式化的结果字符串
    """
    if result.success:
        return (
            f"转换成功！\n"
            f"  标题: {result.title}\n"
            f"  作者: {result.author}\n"
            f"  时间: {result.publish_time}\n"
            f"  输出: {result.output_path}\n"
            f"  图片: {result.image_count} 张\n"
            f"  大小: {result.char_count} 字符"
        )
    else:
        error_type = result.error_type or "unknown"
        return f"[{error_type}] 转换失败: {result.error}"


@mcp.tool()
async def convert_article_tool(
    url: str,
    output_dir: str = "./output",
    download_images: bool = True,
    concurrency: int = 5,
    use_frontmatter: bool = True,
) -> str:
    """
    将微信公众号文章转换为 Markdown 文件

    Args:
        url: 微信文章链接（必须以 https://mp.weixin.qq.com/ 开头）
        output_dir: 输出目录路径（默认：./output）
        download_images: 是否下载图片到本地（默认：True）
        concurrency: 图片下载并发数（默认：5）
        use_frontmatter: 是否使用 YAML frontmatter（默认：True）

    Returns:
        转换结果摘要
    """
    setup_logging()

    # 验证 URL
    if not url.startswith("https://mp.weixin.qq.com/"):
        return f"错误: 无效的 URL。必须以 https://mp.weixin.qq.com/ 开头。收到: {url}"

    # 调用共享的转换函数
    result = await convert_article(
        url=url,
        output_dir=output_dir,
        headless=True,
        download_images=download_images,
        concurrency=concurrency,
        force=True,  # MCP 模式默认覆盖
        use_frontmatter=use_frontmatter,
    )

    return _format_result(result)


@mcp.tool()
async def batch_convert_tool(
    urls: list[str],
    output_dir: str = "./output",
    download_images: bool = True,
    concurrency: int = 5,
) -> str:
    """
    批量转换多篇微信公众号文章

    Args:
        urls: 微信文章链接列表
        output_dir: 输出目录路径（默认：./output）
        download_images: 是否下载图片到本地（默认：True）
        concurrency: 图片下载并发数（默认：5）

    Returns:
        批量转换结果摘要
    """
    results: list[str] = []
    succeeded = 0
    failed = 0

    for i, url in enumerate(urls, 1):
        result = await convert_article(
            url=url,
            output_dir=output_dir,
            headless=True,
            download_images=download_images,
            concurrency=concurrency,
            force=True,
            use_frontmatter=True,
        )

        # 格式化单条结果
        status = "成功" if result.success else "失败"
        results.append(f"[{i}/{len(urls)}] {url}\n  {status}: {result.title or result.error}")

        if result.success:
            succeeded += 1
        else:
            failed += 1

    summary = f"\n批量转换完成: {succeeded}/{len(urls)} 成功, {failed} 失败。\n"
    return summary + "\n".join(results)


def run_server() -> None:
    """
    启动 MCP 服务器

    使用 stdio 传输协议，适合与 AI 客户端集成。
    """
    setup_logging()
    mcp.run(transport="stdio")
