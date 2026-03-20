"""
HTML 解析模块

从微信公众号文章页面中提取：
- 元数据（标题、作者、发布时间）
- 代码块（带语言标签）
- 图片 URL
- 音视频引用
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag

from .helpers import format_timestamp, get_logger

# CSS 计数器垃圾文本的正则匹配
# 微信代码块有时会混入 CSS counter 相关的垃圾文本
_CSS_COUNTER_RE = re.compile(r"^(?:[a-z]*ounter|content)\s*\(", re.IGNORECASE)
# 纯行号匹配
_LINE_NUMBER_RE = re.compile(r"^\s*\d+\s*$")

# 发布时间提取正则
# 微信将发布时间存储在 JavaScript 变量中
_TIME_PATTERNS = [
    re.compile(r"""create_time\s*[:=]\s*['"](\d{10})['"]"""),
    re.compile(r"""create_time\s*[:=]\s*JsDecode\(\s*['"](\d{10})['"]\s*\)"""),
]

# 需要从文章内容中移除的噪音元素
_NOISE_SELECTORS = [
    "script",                  # 脚本
    "style",                   # 样式
    ".qr_code_pc",             # PC 端二维码
    ".reward_area",            # 打赏区域
    ".rich_media_tool",        # 工具栏
    ".like_a_look_info",       # 点赞信息
    "#js_pc_qr_code",          # PC 端二维码
    ".share_notice",           # 分享提示
    ".reward_qrcode_area",     # 打赏二维码
    ".js_underline_link_tooltip",  # 链接提示
]


@dataclass
class ArticleMetadata:
    """
    文章元数据

    Attributes:
        title: 文章标题
        author: 作者/公众号名称
        publish_time: 发布时间（格式化后的字符串）
        source_url: 原文链接
    """
    title: str = ""
    author: str = ""
    publish_time: str = ""
    source_url: str = ""


@dataclass
class CodeBlock:
    """
    代码块

    Attributes:
        lang: 编程语言（如 "python", "javascript"）
        code: 代码内容
    """
    lang: str
    code: str


@dataclass
class MediaReference:
    """
    媒体引用（音频或视频）

    Attributes:
        media_type: 媒体类型（'audio' 或 'video'）
        name: 媒体名称
        src: 媒体源 URL（如果有）
    """
    media_type: str  # 'audio' 或 'video'
    name: str
    src: str = ""


@dataclass
class ParsedContent:
    """
    解析后的文章内容

    Attributes:
        content_html: 处理后的正文 HTML
        code_blocks: 提取的代码块列表
        image_urls: 图片 URL 列表（去重，保持顺序）
        media_references: 媒体引用列表
    """
    content_html: str = ""
    code_blocks: list[CodeBlock] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)
    media_references: list[MediaReference] = field(default_factory=list)


def extract_publish_time(html: str) -> str:
    """
    从页面 HTML 中提取发布时间戳

    微信文章的发布时间存储在 script 变量中，
    需要通过正则匹配提取。

    Args:
        html: 页面完整 HTML

    Returns:
        格式化的时间字符串，提取失败返回空字符串
    """
    for pattern in _TIME_PATTERNS:
        match = pattern.search(html)
        if match:
            return format_timestamp(match.group(1))
    return ""


def extract_metadata(soup: BeautifulSoup, html: str, url: str = "") -> ArticleMetadata:
    """
    提取文章元数据（标题、作者、发布时间）

    Args:
        soup: BeautifulSoup 解析对象
        html: 原始 HTML（用于提取时间戳）
        url: 文章 URL

    Returns:
        ArticleMetadata 对象
    """
    # 标题在 #activity-name 元素中
    title_el = soup.select_one("#activity-name")
    # 作者/公众号名称在 #js_name 元素中
    author_el = soup.select_one("#js_name")

    return ArticleMetadata(
        title=title_el.get_text(strip=True) if title_el else "",
        author=author_el.get_text(strip=True) if author_el else "",
        publish_time=extract_publish_time(html),
        source_url=url,
    )


def _is_css_garbage(line: str) -> bool:
    """
    检查代码行是否为 CSS 计数器垃圾文本或纯行号

    Args:
        line: 代码行

    Returns:
        如果是垃圾文本返回 True
    """
    stripped = line.strip()
    if not stripped:
        return False
    if _CSS_COUNTER_RE.match(stripped):
        return True
    if _LINE_NUMBER_RE.match(stripped):
        return True
    return False


def _extract_code_blocks(content_el: Tag, bs_obj: BeautifulSoup) -> list[CodeBlock]:
    """
    从微信的 .code-snippet__fix 元素中提取代码块

    微信使用自定义的 HTML 结构展示代码块，
    需要特殊处理：
    1. 移除行号元素
    2. 提取语言标签
    3. 过滤 CSS 计数器垃圾

    Args:
        content_el: 文章内容容器元素
        bs_obj: BeautifulSoup 对象（用于创建占位符）

    Returns:
        CodeBlock 列表
    """
    logger = get_logger()
    blocks: list[CodeBlock] = []

    for snippet in content_el.select(".code-snippet__fix"):
        # 移除行号元素
        for line_idx in snippet.select(".code-snippet__line-index"):
            line_idx.decompose()

        # 获取语言标签
        pre_el = snippet.select_one("pre[data-lang]")
        lang = pre_el.get("data-lang", "") if pre_el else ""

        # 收集代码内容，过滤垃圾文本
        lines: list[str] = []
        for code_el in snippet.select("code"):
            text = code_el.get_text()
            if not _is_css_garbage(text):
                lines.append(text)

        code = "\n".join(lines)
        if code.strip():
            blocks.append(CodeBlock(lang=str(lang), code=code))
            logger.debug(f"提取代码块: 语言={lang}, {len(code)} 字符")

        # 用占位符替换代码块元素
        placeholder = bs_obj.new_tag("p")
        placeholder.string = f"CODEBLOCK-PLACEHOLDER-{len(blocks) - 1}"
        snippet.replace_with(placeholder)

    return blocks


def _extract_media(content_el: Tag, bs_obj: BeautifulSoup) -> list[MediaReference]:
    """
    提取嵌入的音频/视频引用

    微信使用自定义元素 <mpvoice> 和 <mpvideo> 嵌入媒体。
    也支持 iframe 方式嵌入的视频（如腾讯视频、B站等）。

    Args:
        content_el: 文章内容容器元素
        bs_obj: BeautifulSoup 对象

    Returns:
        MediaReference 列表
    """
    refs: list[MediaReference] = []

    # 微信音频：<mpvoice> 自定义元素
    for voice in content_el.select("mpvoice"):
        name = voice.get("name", voice.get("voice_encode_fileid", "音频"))
        refs.append(MediaReference(media_type="audio", name=str(name)))
        placeholder = bs_obj.new_tag("p")
        placeholder.string = f"[音频: {name}]"
        voice.replace_with(placeholder)

    # 微信视频：<mpvideo> 自定义元素
    for video in content_el.select("mpvideo"):
        title = video.get("data-title", video.get("title", "视频"))
        src = video.get("data-src", video.get("src", ""))
        refs.append(MediaReference(media_type="video", name=str(title), src=str(src)))
        placeholder = bs_obj.new_tag("p")
        placeholder.string = f"[视频: {title}]"
        video.replace_with(placeholder)

    # iframe 嵌入的视频（腾讯视频、B站等）
    for iframe in content_el.select("iframe"):
        src = str(iframe.get("src", ""))
        if any(domain in src for domain in ("v.qq.com", "player.bilibili", "youku.com")):
            refs.append(MediaReference(media_type="video", name="嵌入视频", src=src))
            placeholder = bs_obj.new_tag("p")
            placeholder.string = f"[视频: 嵌入视频]({src})"
            iframe.replace_with(placeholder)

    return refs


def process_content(soup: BeautifulSoup) -> ParsedContent:
    """
    预处理文章 DOM

    执行以下步骤：
    1. 修复懒加载图片（data-src -> src）
    2. 提取代码块（替换为占位符）
    3. 提取音频/视频引用
    4. 移除噪音元素
    5. 收集图片 URL（去重，保持顺序）

    Args:
        soup: BeautifulSoup 解析对象

    Returns:
        ParsedContent 对象
    """
    logger = get_logger()

    # 获取文章内容容器
    content_el = soup.select_one("#js_content")
    if not content_el:
        logger.warning("页面中未找到 #js_content 元素")
        return ParsedContent()

    # 1. 修复懒加载图片
    # 微信使用 data-src 存储真实图片 URL
    for img in content_el.select("img[data-src]"):
        img["src"] = img["data-src"]

    # 2. 提取代码块（替换为占位符）
    code_blocks = _extract_code_blocks(content_el, soup)

    # 3. 提取音频/视频
    media_refs = _extract_media(content_el, soup)

    # 4. 移除噪音元素
    for selector in _NOISE_SELECTORS:
        for el in content_el.select(selector):
            el.decompose()

    # 5. 收集图片 URL（去重，保持顺序）
    seen: set[str] = set()
    image_urls: list[str] = []
    for img in content_el.select("img[src]"):
        src = str(img.get("src", ""))
        if src and src not in seen:
            seen.add(src)
            image_urls.append(src)

    logger.debug(f"找到 {len(image_urls)} 张唯一图片, {len(code_blocks)} 个代码块")

    return ParsedContent(
        content_html=str(content_el),
        code_blocks=code_blocks,
        image_urls=image_urls,
        media_references=media_refs,
    )
