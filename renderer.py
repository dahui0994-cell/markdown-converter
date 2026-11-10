"""渲染核心: Markdown -> 各格式。

当前实现 PDF(用本机 Edge 无头模式, 支持中文, 无需额外下载浏览器)。
预留 Word / JPG / PNG 的扩展接口, 后续实现即可, 页面与调用方不用改。
"""

from pathlib import Path
from urllib.parse import quote

import markdown
from playwright.sync_api import sync_playwright

# 单一事实来源: 所有输出(PDF/预览)共用这一套样式, 保证所见即所得
LAYOUT_CSS = """
  @page { margin: 2.2cm 1.8cm; }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", SimSun, sans-serif;
    font-size: 11pt; line-height: 1.85; color: #24292f; letter-spacing: 0.2px;
  }
  p { margin: 0 0 0.75em; text-indent: 2em; text-align: justify; }
  h1 { font-size: 22pt; font-weight: 700; color: #1a1a1a; text-align: center;
       letter-spacing: 2px; border-bottom: 2px solid #333;
       padding-bottom: 10px; margin: 0.4em 0 0.8em; }
  h2 { font-size: 16pt; font-weight: 700; color: #1a1a1a; border-left: 5px solid #2f6feb;
       padding-left: 10px; margin: 1.6em 0 0.7em; }
  h3 { font-size: 13pt; font-weight: 700; color: #333; margin: 1.3em 0 0.5em; }
  h4, h5, h6 { font-size: 11pt; font-weight: 700; margin: 1.1em 0 0.4em; }
  ul, ol { margin: 0.5em 0 0.9em; padding-left: 1.6em; }
  li { margin-bottom: 0.35em; }
  li > ul, li > ol { margin: 0.2em 0; }
  code { font-family: Consolas, "Courier New", monospace; font-size: 9.5pt;
         background: #f4f4f4; border: 1px solid #e3e3e3; padding: 1px 5px; border-radius: 4px; }
  pre { background: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 8px;
        padding: 12px 14px; overflow-x: hidden; white-space: pre-wrap;
        font-size: 9.5pt; line-height: 1.6; margin: 0.8em 0; page-break-inside: avoid; }
  pre code { background: none; border: none; padding: 0; font-size: inherit; }
  table { border-collapse: collapse; width: 100%; margin: 0.9em 0; font-size: 10pt;
          page-break-inside: avoid; }
  th, td { border: 1px solid #d0d7de; padding: 6px 12px; }
  th { background: #f0f3f6; font-weight: 700; }
  tr:nth-child(even) td { background: #fafbfc; }
  blockquote { border-left: 4px solid #2f6feb; background: #f0f5ff; margin: 0.8em 0;
               padding: 8px 14px; color: #444; font-size: 10pt; page-break-inside: avoid; }
  blockquote p { text-indent: 0; margin: 0.3em 0; }
  hr { border: none; border-top: 1px solid #d8d8d8; margin: 1.4em 0; }
  img { max-width: 100%; border-radius: 4px; margin: 0.4em 0; }
  a { color: #2f6feb; text-decoration: none; }
  strong { font-weight: 700; color: #1a1a1a; }
  h1, h2, h3 { page-break-after: avoid; }
"""

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>{css}</style>
</head>
<body>
{content}
</body>
</html>"""


def markdown_to_html_body(md_text: str) -> str:
    """把 Markdown 转成渲染好的 HTML 正文(不含外壳), 预览与 PDF 共用。"""
    return markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "codehilite", "toc"],
    )


def build_html_doc(md_text: str) -> str:
    """生成完整 HTML 文档(带排版样式), 用于 PDF 渲染。"""
    body = markdown_to_html_body(md_text)
    return _HTML_TEMPLATE.format(css=LAYOUT_CSS, content=body)


def _prefix_selectors(selector_list: str, prefix: str) -> str:
    """给一组 CSS 选择器加前缀, 根容器(html/body)映射为 #preview 本身, 去重。"""
    out = []
    for sel in selector_list.split(","):
        s = sel.strip()
        if not s or s.startswith(":root"):
            continue
        if s.startswith("#"):
            out.append(s)
        elif s in ("html", "body"):
            out.append(prefix)          # 根容器 -> #preview 自身, 基础字体才生效
        elif s == "*":
            out.append(f"{prefix} *")
        else:
            out.append(f"{prefix} {s}")
    seen, dedup = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            dedup.append(x)
    return ", ".join(dedup)


def preview_css() -> str:
    """LAYOUT_CSS 的「#preview 作用域版」: 选择器全部加 #preview 前缀, 去掉 @page。

    这样中栏预览与 PDF 排版一致(所见即所得), 又不会污染页面其他区域(如顶栏)。
    前端把这段 CSS 注入即可。
    """
    """把整段 CSS 按「选择器 { 主体 }」规则切分, 每条选择器加 #preview 前缀。"""
    import re
    rule_re = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)
    css = LAYOUT_CSS
    pos = 0
    out_parts = []
    for m in rule_re.finditer(css):
        out_parts.append(css[pos:m.start()])  # 规则之间的空白/注释
        raw_sel = m.group(1).strip()
        # 丢弃 @page / @media 等 at-rule(预览用不到)
        if raw_sel.startswith("@"):
            pos = m.end()
            continue
        sel = _prefix_selectors(raw_sel, "#preview")
        body = m.group(2).strip()
        if body:
            out_parts.append(f"\n{sel} {{\n  {body}\n}}")
        pos = m.end()
    out_parts.append(css[pos:])
    return "".join(out_parts)


def extract_title(md_text: str) -> str | None:
    """取第一个一级标题作为文件名/文档标题, 没有则 None。"""
    for line in md_text.splitlines():
        if line.startswith("# "):
            return line.lstrip("# ").strip() or None
    return None


def _launch_browser(p):
    """优先本机 Edge, 没有则回退 Playwright Chromium。"""
    try:
        return p.chromium.launch(channel="msedge", headless=True)
    except Exception:
        return p.chromium.launch(headless=True)


def markdown_to_pdf(md_text: str) -> tuple[bytes, str]:
    """Markdown -> PDF, 返回 (PDF 字节, 建议文件名)。"""
    html = build_html_doc(md_text)
    with sync_playwright() as p:
        browser = _launch_browser(p)
        try:
            page = browser.new_page()
            page.set_content(html)
            pdf = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            )
        finally:
            browser.close()
    if not pdf.startswith(b"%PDF"):
        raise RuntimeError("生成的 PDF 无效")
    return pdf, (extract_title(md_text) or "文档") + ".pdf"


# ---------------------------------------------------------------------------
# 以下为后续扩展接口(当前抛出 NotImplementedError), 页面右栏格式按钮预留这些
# ---------------------------------------------------------------------------

def markdown_to_word(md_text: str) -> tuple[bytes, str]:
    raise NotImplementedError("Word 导出尚未实现(后续扩展)")


def markdown_to_jpg(md_text: str) -> tuple[bytes, str]:
    raise NotImplementedError("JPG 导出尚未实现(后续扩展)")


def markdown_to_png(md_text: str) -> tuple[bytes, str]:
    raise NotImplementedError("PNG 导出尚未实现(后续扩展)")


# 格式名 -> 处理函数, 页面通过它按格式分发, 扩展时在此登记即可
FORMATS: dict[str, object] = {
    "pdf": markdown_to_pdf,
    "word": markdown_to_word,
    "jpg": markdown_to_jpg,
    "png": markdown_to_png,
}
