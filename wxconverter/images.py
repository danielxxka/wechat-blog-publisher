"""
图片下载模块

使用 httpx 异步并发下载微信文章中的图片。
功能特点：
- 并发控制（使用信号量）
- 单图重试机制
- 自动推断图片格式
- 支持协议相对 URL
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import httpx

from .helpers import get_logger, infer_image_extension

# 请求头，模拟正常浏览器访问微信 CDN
_HEADERS = {
    "Referer": "https://mp.weixin.qq.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
}


@dataclass
class DownloadResult:
    """
    单个图片的下载结果

    Attributes:
        remote_url: 原始远程 URL
        local_path: 本地相对路径（如 "images/img_001.png"），失败时为 None
        error: 错误信息（失败时）
    """
    remote_url: str
    local_path: str | None = None
    error: str | None = None


async def download_single_image(
    client: httpx.AsyncClient,
    img_url: str,
    img_dir: Path,
    index: int,
    semaphore: asyncio.Semaphore,
    max_retries: int = 3,
) -> DownloadResult:
    """
    下载单张图片（带重试逻辑）

    Args:
        client: httpx 异步客户端
        img_url: 图片 URL
        img_dir: 图片保存目录
        index: 图片序号（用于命名）
        semaphore: 并发控制信号量
        max_retries: 最大重试次数

    Returns:
        DownloadResult 对象
    """
    logger = get_logger()

    # 处理协议相对 URL（// 开头）
    url = img_url if not img_url.startswith("//") else f"https:{img_url}"

    async with semaphore:
        last_error: str = ""
        for attempt in range(max_retries):
            try:
                # 发起请求
                resp = await client.get(url, timeout=15.0)
                resp.raise_for_status()

                # 根据响应推断图片格式
                content_type = resp.headers.get("content-type")
                ext = infer_image_extension(url, content_type)
                filename = f"img_{index:03d}.{ext}"
                filepath = img_dir / filename

                # 写入文件
                filepath.write_bytes(resp.content)

                return DownloadResult(
                    remote_url=img_url,
                    local_path=f"images/{filename}",
                )

            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    # 线性退避：1s, 2s, 3s
                    delay = (attempt + 1) * 1.0
                    logger.debug(
                        f"图片下载尝试 {attempt + 1} 失败 "
                        f"img_{index:03d}: {e}。{delay:.0f}秒后重试..."
                    )
                    await asyncio.sleep(delay)

        logger.warning(f"图片下载失败 {index}: {last_error}")
        return DownloadResult(remote_url=img_url, error=last_error)


async def download_all_images(
    img_urls: list[str],
    img_dir: Path,
    concurrency: int = 5,
    max_retries: int = 3,
) -> dict[str, str]:
    """
    并发下载所有图片

    Args:
        img_urls: 图片 URL 列表
        img_dir: 图片保存目录
        concurrency: 最大并发数
        max_retries: 单图最大重试次数

    Returns:
        {远程URL: 本地相对路径} 映射（仅包含成功的下载）
    """
    logger = get_logger()

    if not img_urls:
        return {}

    # 创建目录
    img_dir.mkdir(parents=True, exist_ok=True)

    # 创建并发控制信号量
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(headers=_HEADERS, follow_redirects=True) as client:
        # 创建所有下载任务
        tasks = [
            download_single_image(client, url, img_dir, i + 1, semaphore, max_retries)
            for i, url in enumerate(img_urls)
        ]
        # 并发执行
        results = await asyncio.gather(*tasks)

    # 统计结果
    url_map: dict[str, str] = {}
    succeeded = 0
    failed = 0

    for result in results:
        if result.local_path:
            url_map[result.remote_url] = result.local_path
            succeeded += 1
        else:
            failed += 1

    logger.info(f"图片: {succeeded} 张下载成功, {failed} 张失败 (共 {len(img_urls)} 张)")
    return url_map
