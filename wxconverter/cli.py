"""
命令行接口模块

提供完整的命令行工具，支持：
- 单文章/批量转换
- 多种参数配置
- 详细的日志输出
- 错误统计
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from .helpers import get_logger, read_urls_from_file, setup_logging
from .workflow import convert_article, ConversionResult


def build_parser() -> argparse.ArgumentParser:
    """
    构建命令行参数解析器

    Returns:
        配置好的 ArgumentParser 对象
    """
    parser = argparse.ArgumentParser(
        prog="wxconverter",
        description="将微信公众号文章转换为 Markdown 文件，并下载图片到本地。",
    )

    parser.add_argument(
        "urls",
        nargs="*",
        help="一个或多个微信文章链接。",
    )
    parser.add_argument(
        "-f", "--file",
        type=Path,
        help="包含 URL 的文本文件（每行一个，# 开头为注释）。",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("./output"),
        help="输出目录（默认：./output）。",
    )
    parser.add_argument(
        "-c", "--concurrency",
        type=int,
        default=5,
        help="图片下载并发数（默认：5）。",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="跳过图片下载，保留远程 URL。",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="显示浏览器窗口（用于手动处理验证码）。",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="覆盖已存在的输出。",
    )
    parser.add_argument(
        "--no-frontmatter",
        action="store_true",
        help="使用引用块格式的元数据，而非 YAML frontmatter。",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="启用调试日志。",
    )

    return parser


def validate_url(url: str) -> bool:
    """
    验证 URL 是否为微信公众号文章链接

    Args:
        url: 待验证的 URL

    Returns:
        如果是有效的微信文章链接返回 True
    """
    return url.startswith("https://mp.weixin.qq.com/")


async def process_single_article(
    url: str,
    output_dir: Path,
    headless: bool = True,
    download_images: bool = True,
    concurrency: int = 5,
    force: bool = False,
    use_frontmatter: bool = True,
) -> bool:
    """
    处理单篇文章

    调用共享的 workflow.convert_article 函数完成转换。

    Args:
        url: 微信文章 URL
        output_dir: 输出目录
        headless: 是否使用无头模式
        download_images: 是否下载图片
        concurrency: 图片下载并发数
        force: 是否覆盖已存在的内容
        use_frontmatter: 是否使用 YAML frontmatter

    Returns:
        转换成功返回 True，失败返回 False
    """
    logger = get_logger()
    logger.info(f"正在处理: {url}")

    result = await convert_article(
        url=url,
        output_dir=output_dir,
        headless=headless,
        download_images=download_images,
        concurrency=concurrency,
        force=force,
        use_frontmatter=use_frontmatter,
    )

    if result.success:
        logger.info(
            f"完成: {result.output_path} "
            f"({result.char_count} 字符, {result.image_count} 张图片)"
        )
    else:
        error_type = result.error_type or "unknown"
        logger.error(f"[{error_type}] {result.error}")

    return result.success


async def async_main(args: argparse.Namespace) -> int:
    """
    异步主函数

    Args:
        args: 解析后的命令行参数

    Returns:
        退出码（0 表示成功，1 表示有错误）
    """
    logger = get_logger()

    # 收集 URL
    urls: list[str] = list(args.urls) if args.urls else []
    if args.file:
        if not args.file.exists():
            logger.error(f"文件不存在: {args.file}")
            return 1
        urls.extend(read_urls_from_file(args.file))

    if not urls:
        logger.error("未提供 URL。请使用位置参数或 -f <文件>。")
        return 1

    # 验证 URL
    valid_urls: list[str] = []
    for url in urls:
        if validate_url(url):
            valid_urls.append(url)
        else:
            logger.warning(f"跳过无效 URL: {url}")

    if not valid_urls:
        logger.error("未找到有效的微信文章链接。")
        return 1

    logger.info(f"准备处理 {len(valid_urls)} 篇文章...")

    # 顺序处理每篇文章
    results: list[tuple[str, bool]] = []
    for url in valid_urls:
        success = await process_single_article(
            url=url,
            output_dir=args.output,
            headless=not args.no_headless,
            download_images=not args.no_images,
            concurrency=args.concurrency,
            force=args.force,
            use_frontmatter=not args.no_frontmatter,
        )
        results.append((url, success))

    # 统计结果
    total = len(results)
    succeeded = sum(1 for _, s in results if s)
    failed_urls = [u for u, s in results if not s]

    if total > 1:
        logger.info(f"处理完成: {succeeded}/{total} 篇文章")
        if failed_urls:
            logger.warning("失败的链接:")
            for u in failed_urls:
                logger.warning(f"  - {u}")

    return 0 if not failed_urls else 1


def main() -> None:
    """
    同步入口点

    解析命令行参数并启动异步主函数。
    """
    parser = build_parser()
    args = parser.parse_args()

    # 如果没有提供 URL 或文件，显示帮助信息
    if not args.urls and not args.file:
        parser.print_help()
        sys.exit(1)

    # 配置日志
    setup_logging(verbose=args.verbose)

    # 运行异步主函数
    exit_code = asyncio.run(async_main(args))
    sys.exit(exit_code)
