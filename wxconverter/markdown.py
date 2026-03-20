"""
Markdown 转换模块

将处理后的 HTML 内容转换为 Markdown 格式：
- 使用 markdownify 库进行基础转换
- 恢复代码块占位符
- 生成 YAML frontmatter
- 替换图片 URL 为本地路径
"""

from __future__ import annotations

import re

import markdownify

from .html_parser import ArticleMetadata, CodeBlock, MediaReference

# 需要转换的 HTML 标签（其他标签会被移除）
_CONVERT_TAGS = [
    "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "b", "em", "i", "a", "img",
    "ul", "ol", "li", "blockquote", "br", "hr",
    "table", "thead", "tbody", "tr", "th", "td",
    "pre", "code", "sup", "sub", "del", "s",
]

# Markdown 图片语法正则：![alt](url)
_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
# 4 个或更多连续换行符（需要压缩）
_EXCESSIVE_NEWLINES = re.compile(r"\n{4,}")
# 行尾空格（需要移除）
_TRAILING_SPACES = re.compile(r"[ \t]+$", re.MULTILINE)


def convert_html_to_markdown(content_html: str, code_blocks: list[CodeBlock]) -> str:
    """
    将处理后的 HTML 转换为 Markdown

    转换后需要恢复代码块占位符为实际的代码块。

    Args:
        content_html: 处理后的 HTML 内容
        code_blocks: 提取的代码块列表

    Returns:
        Markdown 文本
    """
    # 使用 markdownify 进行基础转换
    md = markdownify.markdownify(
        content_html,
        heading_style="ATX",  # 使用 # 风格的标题
        bullets="-",          # 使用 - 作为无序列表标记
        convert=_CONVERT_TAGS,
    )

    # 恢复代码块占位符
    for i, block in enumerate(code_blocks):
        placeholder = f"CODEBLOCK-PLACEHOLDER-{i}"
        lang = block.lang or ""
        replacement = f"\n```{lang}\n{block.code}\n```\n"
        md = md.replace(placeholder, replacement)

    # 清理
    md = md.replace("\u00a0", " ")  # 非断行空格替换为普通空格
    md = _EXCESSIVE_NEWLINES.sub("\n\n\n", md)  # 压缩多余换行
    md = _TRAILING_SPACES.sub("", md)  # 移除行尾空格

    return md.strip()


def replace_image_urls(md: str, url_map: dict[str, str]) -> str:
    """
    将 Markdown 中的远程图片 URL 替换为本地路径

    Args:
        md: Markdown 文本
        url_map: {远程URL: 本地相对路径} 映射

    Returns:
        替换后的 Markdown 文本
    """
    def _replace(match: re.Match) -> str:
        alt = match.group(1)
        url = match.group(2)
        local_path = url_map.get(url)
        if local_path:
            return f"![{alt}]({local_path})"
        return match.group(0)

    return _IMAGE_PATTERN.sub(_replace, md)


def _escape_yaml_string(s: str) -> str:
    """
    转义 YAML frontmatter 中的字符串值

    如果字符串包含特殊字符，需要用双引号包裹并转义内部引号。

    Args:
        s: 原始字符串

    Returns:
        转义后的字符串
    """
    if not s:
        return '""'

    # 如果包含特殊字符，需要引号包裹
    if any(c in s for c in ':{}[]&*?|->!%@`#,"\n'):
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    return s


def build_frontmatter(meta: ArticleMetadata) -> str:
    """
    构建 YAML frontmatter 块

    格式：
    ---
    title: 文章标题
    author: 作者名称
    date: 发布时间
    source: 原文链接
    ---

    Args:
        meta: 文章元数据

    Returns:
        YAML frontmatter 字符串
    """
    lines = ["---"]
    if meta.title:
        lines.append(f"title: {_escape_yaml_string(meta.title)}")
    if meta.author:
        lines.append(f"author: {_escape_yaml_string(meta.author)}")
    if meta.publish_time:
        lines.append(f"date: {_escape_yaml_string(meta.publish_time)}")
    if meta.source_url:
        lines.append(f"source: {_escape_yaml_string(meta.source_url)}")
    lines.append("---")
    return "\n".join(lines)


def build_markdown(
    meta: ArticleMetadata,
    body_md: str,
    media_refs: list[MediaReference] | None = None,
    use_frontmatter: bool = True,
) -> str:
    """
    组装最终的 Markdown 文档

    根据参数选择元数据格式：
    - use_frontmatter=True: YAML frontmatter 格式
    - use_frontmatter=False: 引用块格式

    Args:
        meta: 文章元数据
        body_md: 正文 Markdown
        media_refs: 媒体引用列表
        use_frontmatter: 是否使用 YAML frontmatter

    Returns:
        完整的 Markdown 文档
    """
    parts: list[str] = []

    if use_frontmatter:
        # YAML frontmatter 格式
        parts.append(build_frontmatter(meta))
        parts.append("")
        if meta.title:
            parts.append(f"# {meta.title}")
            parts.append("")
    else:
        # 引用块格式（原始格式）
        if meta.title:
            parts.append(f"# {meta.title}")
            parts.append("")
        info_lines: list[str] = []
        if meta.author:
            info_lines.append(f"> 作者: {meta.author}")
        if meta.publish_time:
            info_lines.append(f"> 时间: {meta.publish_time}")
        if meta.source_url:
            info_lines.append(f"> 来源: {meta.source_url}")
        if info_lines:
            parts.extend(info_lines)
            parts.append("")
        parts.append("---")
        parts.append("")

    # 添加正文
    parts.append(body_md)

    # 添加媒体引用（如果有）
    if media_refs:
        parts.append("")
        parts.append("---")
        parts.append("")
        parts.append("## 媒体引用")
        parts.append("")
        for ref in media_refs:
            if ref.src:
                parts.append(f"- [{ref.media_type}: {ref.name}]({ref.src})")
            else:
                parts.append(f"- {ref.media_type}: {ref.name}")

    parts.append("")  # 文件末尾换行
    return "\n".join(parts)
