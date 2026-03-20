"""
浏览器抓取模块

使用 Camoufox（反检测 Firefox）获取微信公众号文章页面。
功能特点：
- 模拟真实浏览器，绕过微信的反爬机制
- 使用 networkidle 等待策略，而非硬编码延迟
- 支持重试和指数退避
- 自动检测验证码页面
"""

from __future__ import annotations

import asyncio

from camoufox.async_api import AsyncCamoufox

from .exceptions import CaptchaError, NetworkError
from .helpers import get_logger

# 验证码/环境异常页面的特征字符串
# 当 HTML 包含这些内容时，表示微信显示了验证页面
_CAPTCHA_INDICATORS = [
    "js_verify",           # 验证码 JavaScript 容器
    "verify_container",    # 验证码容器
    "环境异常",            # 环境异常提示
    "请完成安全验证",      # 安全验证提示
    "操作频繁",            # 操作频繁提示
]


def _is_captcha_page(html: str) -> bool:
    """
    检查页面是否为验证码/环境异常页面

    Args:
        html: 页面 HTML 内容

    Returns:
        如果是验证码页面返回 True
    """
    return any(indicator in html for indicator in _CAPTCHA_INDICATORS)


async def fetch_page_html(
    url: str,
    headless: bool = True,
    max_retries: int = 3,
    base_delay: float = 2.0,
) -> str:
    """
    使用 Camoufox 获取微信文章的渲染后 HTML

    使用 networkidle 等待策略替代硬编码的 sleep。
    对于网络/超时错误进行指数退避重试。
    验证码错误不会重试。

    Args:
        url: 微信文章 URL
        headless: 是否使用无头模式（默认 True）
        max_retries: 最大重试次数（默认 3）
        base_delay: 基础延迟秒数（默认 2.0）

    Returns:
        页面的完整 HTML 内容

    Raises:
        CaptchaError: 检测到验证码页面
        NetworkError: 所有重试均失败
    """
    logger = get_logger()
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            async with AsyncCamoufox(headless=headless) as browser:
                page = await browser.new_page()
                logger.debug(f"尝试 {attempt + 1}/{max_retries}: 正在访问 {url}")

                # 导航到页面
                await page.goto(url, wait_until="domcontentloaded")

                # 等待文章内容容器加载
                try:
                    await page.wait_for_selector("#js_content", timeout=15000)
                except Exception:
                    pass  # 超时不一定致命——内容可能仍然存在

                # 等待网络稳定（替代硬编码的 sleep）
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    # networkidle 超时不致命；有些页面有持久连接
                    await asyncio.sleep(2)

                html = await page.content()

                # 验证：是否为验证码页面？
                if _is_captcha_page(html):
                    raise CaptchaError(
                        "检测到微信验证码/环境异常。"
                        "请尝试使用 --no-headless 参数手动处理验证码。"
                    )

                # 验证：是否包含有效内容？
                if "#activity-name" not in html and "rich_media_title" not in html:
                    logger.warning("页面可能不包含有效文章（未找到标题元素）")

                return html

        except CaptchaError:
            raise  # 验证码错误不重试

        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                # 指数退避：2s, 4s, 8s
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"尝试 {attempt + 1} 失败: {e}。{delay:.0f}秒后重试..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"所有 {max_retries} 次尝试均失败: {url}")

    raise NetworkError(f"在 {max_retries} 次尝试后仍失败: {last_error}")
