"""渲染核心: Markdown -> 各格式。

当前实现 PDF(用本机 Edge 无头模式, 支持中文, 无需额外下载浏览器)。
预留 Word / JPG / PNG 的扩展接口, 后续实现即可, 页面与调用方不用改。
"""

import io
import re
from pathlib import Path
from urllib.parse import quote

import markdown
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from playwright.sync_api import sync_playwright
from pptx import Presentation
from pptx.dml.color import RGBColor as PptRGB
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt as PptPt

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
# Word 导出: 轻量解析 Markdown 结构(标题/列表/表格/代码/引用), 用 python-docx
# 生成 .docx。中文字体统一微软雅黑, 行内 **加粗** / *斜体* / `代码` / [链接]。
# ---------------------------------------------------------------------------

_INLINE = re.compile(r"(\*\*(.+?)\*\*)|(\*(.+?)\*)|(`(.+?)`)|(\[(.+?)\]\((.+?)\))")


def _doc_set_cjk(run, font="Microsoft YaHei"):
    """让 run 使用中文字体(东亚字体), 否则 Word 默认西文字体无法渲染中文。"""
    run.font.name = font
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), font)


def _add_inline_runs(paragraph, text):
    """解析行内 Markdown(加粗/斜体/代码/链接), 往 paragraph 加 run。"""
    pos = 0
    for m in _INLINE.finditer(text):
        if m.start() > pos:
            r = paragraph.add_run(text[pos:m.start()])
            _doc_set_cjk(r)
        if m.group(2) is not None:      # **加粗**
            r = paragraph.add_run(m.group(2)); r.bold = True
            _doc_set_cjk(r)
        elif m.group(4) is not None:    # *斜体*
            r = paragraph.add_run(m.group(4)); r.italic = True
            _doc_set_cjk(r)
        elif m.group(6) is not None:    # `行内代码`
            r = paragraph.add_run(m.group(6))
            r.font.name = "Consolas"
            r.font.color.rgb = RGBColor(0xC7, 0x25, 0x4E)
            _doc_set_cjk(r, "Consolas")
        elif m.group(8) is not None:    # [文本](url)
            r = paragraph.add_run(m.group(8)); r.font.color.rgb = RGBColor(0x2F, 0x6F, 0xEB)
            _doc_set_cjk(r)
        pos = m.end()
    if pos < len(text):
        r = paragraph.add_run(text[pos:])
        _doc_set_cjk(r)


def _set_cell_borders(cell):
    """给表格单元格加细边框(默认无边框)。"""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), "D0D7DE")
        borders.append(el)
    tcPr.append(borders)


def _markdown_blocks_to_doc(doc, md_text: str) -> None:
    """把 Markdown 的块级结构写进 Word 文档。"""
    lines = md_text.splitlines()
    i = 0
    in_code = False
    code_buf: list[str] = []

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()

        # 代码块
        if line.lstrip().startswith("```"):
            if not in_code:
                in_code, code_buf = True, []
                i += 1
                continue
            else:
                in_code = False
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Pt(12)
                r = p.add_run("\n".join(code_buf))
                r.font.name = "Consolas"
                r.font.size = Pt(9)
                r.font.color.rgb = RGBColor(0x24, 0x29, 0x2F)
                _doc_set_cjk(r, "Consolas")
                i += 1
                continue
        if in_code:
            code_buf.append(raw)
            i += 1
            continue

        stripped = line.strip()
        # 空行
        if not stripped:
            i += 1
            continue
        # 标题
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = min(len(m.group(1)), 9)
            p = doc.add_heading(m.group(2).strip(), level=level)
            for run in p.runs:
                _doc_set_cjk(run)
            i += 1
            continue
        # 分隔线
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(6)
            i += 1
            continue
        # 表格
        if stripped.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|$", lines[i + 1].strip()):
            header_cells = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2  # 跳过表头与分隔行
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            table = doc.add_table(rows=1 + len(rows), cols=len(header_cells))
            table.style = "Table Grid"
            for ci, txt in enumerate(header_cells):
                cell = table.rows[0].cells[ci]
                cell.text = txt
                for pr in cell.paragraphs[0].runs:
                    pr.bold = True
                    _doc_set_cjk(pr)
            for ri, row in enumerate(rows):
                for ci in range(len(header_cells)):
                    cell = table.rows[ri + 1].cells[ci]
                    val = row[ci] if ci < len(row) else ""
                    cell.text = val
                    for pr in cell.paragraphs[0].runs:
                        _doc_set_cjk(pr)
            continue
        # 引用
        if stripped.startswith(">"):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(18)
            txt = stripped.lstrip("> ").strip()
            _add_inline_runs(p, txt)
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(4)
            i += 1
            continue
        # 列表
        m_li = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", raw)
        if m_li:
            indent = len(m_li.group(1))
            ordered = m_li.group(2)[0].isdigit()
            style = ("List Number" if ordered else "List Bullet")
            p = doc.add_paragraph(style=style)
            p.paragraph_format.left_indent = Pt(18 + indent * 10)
            _add_inline_runs(p, m_li.group(3).strip())
            i += 1
            continue
        # 普通段落
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Pt(24)
        p.paragraph_format.space_after = Pt(6)
        _add_inline_runs(p, stripped)
        i += 1

    # 若结尾仍在代码块内(未闭合), 兜底输出
    if in_code and code_buf:
        p = doc.add_paragraph()
        r = p.add_run("\n".join(code_buf))
        r.font.name = "Consolas"
        _doc_set_cjk(r, "Consolas")


def _new_word_doc() -> Document:
    """新建文档并设中文默认样式(微软雅黑正文 + 标题)。"""
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Microsoft YaHei"
    normal.font.size = Pt(11)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    for hs in doc.styles:
        if hs.name and hs.name.startswith("Heading"):
            try:
                hs.font.name = "Microsoft YaHei"
                if hs.element.rPr is not None and hs.element.rPr.rFonts is not None:
                    hs.element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
            except Exception:
                continue
    return doc


def markdown_to_word(md_text: str) -> tuple[bytes, str]:
    """Markdown -> Word(.docx), 返回 (docx 字节, 建议文件名)。"""
    doc = _new_word_doc()
    _markdown_blocks_to_doc(doc, md_text)
    buf = io.BytesIO()
    doc.save(buf)
    data = buf.getvalue()
    if not data.startswith(b"PK"):
        raise RuntimeError("生成的 docx 无效")
    return data, (extract_title(md_text) or "文档") + ".docx"


def markdown_to_jpg(md_text: str) -> tuple[bytes, str]:
    """Markdown -> JPG 图片, 返回 (图片字节, 建议文件名)。"""
    return _markdown_to_image(md_text, "jpeg")


def markdown_to_png(md_text: str) -> tuple[bytes, str]:
    """Markdown -> PNG 图片, 返回 (图片字节, 建议文件名)。"""
    return _markdown_to_image(md_text, "png")


_IMG_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  {css}
  html, body {{ margin: 0; padding: 0; background: #fff; }}
  .doc {{ padding: 36px 44px; }}
</style>
</head>
<body>
<div class="doc">{content}</div>
</body>
</html>"""


def _markdown_to_image(md_text: str, fmt: str) -> tuple[bytes, str]:
    """把 Markdown 渲染成一张长图(png/jpeg)。内容在固定宽度容器内排版。"""
    body = markdown_to_html_body(md_text)
    # 图片版用「容器内」作用域样式: 把 LAYOUT_CSS 选择器加到 .doc 下, 白底
    css = preview_css().replace("#preview", ".doc")
    html = _IMG_HTML_TEMPLATE.format(css=css, content=body)
    ext = "jpg" if fmt == "jpeg" else "png"
    mime = "jpeg" if fmt == "jpeg" else "png"
    with sync_playwright() as p:
        browser = _launch_browser(p)
        try:
            page = browser.new_page(viewport={"width": 900, "height": 1200})
            page.set_content(html)
            page.wait_for_timeout(200)
            if mime == "jpeg":
                img = page.screenshot(type="jpeg", full_page=True, quality=90)
            else:
                img = page.screenshot(type="png", full_page=True)
        finally:
            browser.close()
    magic = (b"\xff\xd8\xff" if fmt == "jpeg" else b"\x89PNG")
    if not img.startswith(magic):
        raise RuntimeError(f"生成的 {ext} 图片无效")
    return img, (extract_title(md_text) or "文档") + f".{ext}"


# ---------------------------------------------------------------------------
# PPT 导出: 把 Markdown 大纲转成 16:9 演示文稿(简约商务风, 白底深灰字蓝色强调)。
#   # 一级标题  -> 首个作封面页(标题+副标题+日期), 其后作分节页
#   ## 二级标题 -> 内容页(标题 + 要点)
#   列表/段落/代码/表格 -> 归入当前内容页要点; 要点过多自动拆「(续)」页
# ---------------------------------------------------------------------------

PPT_CJK = "Microsoft YaHei"
_PPT_MAX_BULLETS = 7


def _hex(rgb: str) -> PptRGB:
    h = rgb.lstrip("#")
    return PptRGB(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# 6 款 PPT 模板: 同一版式, 不同配色。key -> 颜色组。
# name 为展示名(不参与转 RGB), 其余为 16 进制色值。
PPT_TEMPLATES: dict[str, dict] = {
    "business":  {"name": "简约商务", "bg": "#FFFFFF", "title": "#1A1A1A",
                  "body": "#24292F", "accent": "#2F6FEB", "footer": "#8A8F98",
                  "subtitle": "#8A8F98"},
    "tech":      {"name": "科技深蓝", "bg": "#0F1B2D", "title": "#FFFFFF",
                  "body": "#E6F0FA", "accent": "#4FC3F7", "footer": "#7C8CA0",
                  "subtitle": "#9FB6CC"},
    "orange":    {"name": "活力橙",   "bg": "#FFF8F0", "title": "#3A2A1E",
                  "body": "#4A3B30", "accent": "#E8613C", "footer": "#B0988A",
                  "subtitle": "#B0988A"},
    "green":     {"name": "清新绿",   "bg": "#FFFFFF", "title": "#1F3D2E",
                  "body": "#2E3D36", "accent": "#2E9E5B", "footer": "#8A9A90",
                  "subtitle": "#8A9A90"},
    "blackgold": {"name": "黑金尊享", "bg": "#141414", "title": "#FFFFFF",
                  "body": "#E8E2D0", "accent": "#D4AF37", "footer": "#8A8A8A",
                  "subtitle": "#B8B8B8"},
    "purple":    {"name": "创意紫",   "bg": "#FFFFFF", "title": "#2A2140",
                  "body": "#33303F", "accent": "#7C4DFF", "footer": "#9A94B0",
                  "subtitle": "#9A94B0"},
}
PPT_DEFAULT_TEMPLATE = "business"
# 兜底颜色(模板解析失败时)
PPT_DEFAULT = _hex("#24292F")


def _ppt_theme(key: str | None) -> dict:
    """把模板 key 解析成 {颜色名: RGB} (去掉展示名 name)。未知 key 回退默认。"""
    raw = PPT_TEMPLATES.get(key or PPT_DEFAULT_TEMPLATE, PPT_TEMPLATES[PPT_DEFAULT_TEMPLATE])
    return {k: _hex(v) for k, v in raw.items() if k != "name"}


def _ppt_strip_inline(text: str) -> str:
    """去掉行内 Markdown 标记, 取纯文本。"""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", text)
    return text.strip()


def _ppt_set_run(run, text: str, size: int, bold: bool = False,
                 color=None, italic: bool = False, theme: dict | None = None):
    """往 run 写文本并统一中文字体(微软雅黑, 含东亚字体)。

    color 缺省取 theme['body']。
    """
    if color is None:
        color = theme.get("body") if theme else PPT_DEFAULT
    run.text = text
    run.font.size = PptPt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = PPT_CJK
    # 东亚字体需单独设置, 否则中文可能落到默认字体
    rPr = run._r.get_or_add_rPr()
    from pptx.oxml.ns import qn as _pq
    ea = rPr.find(_pq("a:ea"))
    if ea is None:
        ea = rPr.makeelement(_pq("a:ea"), {})
        rPr.append(ea)
    ea.set("typeface", PPT_CJK)


def _ppt_parse(md_text: str) -> list[dict]:
    """解析 Markdown 为幻灯片结构列表。"""
    lines = md_text.splitlines()
    slides: list[dict] = []
    i, n = 0, len(lines)
    cover_seen = False

    def last_content() -> dict | None:
        return slides[-1] if slides and slides[-1]["kind"] == "content" else None

    def ensure_content(title: str) -> dict:
        cur = last_content()
        if cur:
            return cur
        s = {"kind": "content", "title": title, "bullets": []}
        slides.append(s)
        return s

    while i < n:
        raw = lines[i]
        stripped = raw.strip()

        # 代码块: 作为一条要点
        if stripped.startswith("```"):
            i += 1
            code = []
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i].rstrip())
                i += 1
            snippet = "  ".join(c.strip() for c in code if c.strip())
            if snippet:
                ensure_content(slides[-1]["title"] if slides else "内容")["bullets"].append("» " + snippet[:80])
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            text = _ppt_strip_inline(m.group(2))
            if level == 1:
                if not cover_seen:
                    slides.append({"kind": "cover", "title": text, "subtitle": "", "date": ""})
                    cover_seen = True
                    i += 1
                    continue
                else:
                    slides.append({"kind": "section", "title": text, "bullets": []})
                    i += 1
                    continue
            # 二/三/四/五级标题 -> 内容页
            s = {"kind": "content", "title": text, "bullets": []}
            slides.append(s)
            i += 1
            continue

        # 空行
        if not stripped:
            i += 1
            continue

        # 表格: 取表头做要点
        if stripped.startswith("|") and i + 1 < n and re.match(r"^\|[\s\-:|]+\|$", lines[i + 1].strip()):
            header = [c.strip() for c in stripped.strip("|").split("|")]
            ensure_content("内容")["bullets"].append("· " + "  |  ".join(h for h in header if h))
            i += 2
            continue

        # 列表 / 引用 / 普通段落 -> 要点
        m_li = re.match(r"^\s*([-*+]|\d+\.)\s+(.*)$", raw)
        if m_li:
            depth = len(raw) - len(raw.lstrip())
            txt = _ppt_strip_inline(m_li.group(2))
            indent = "   " * min(depth // 2, 2)
            ensure_content("内容")["bullets"].append(indent + "• " + txt)
            i += 1
            continue
        m_q = re.match(r"^>\s*(.*)$", stripped)
        if m_q:
            ensure_content("内容")["bullets"].append("‖ " + _ppt_strip_inline(m_q.group(1)))
            i += 1
            continue
        ensure_content("内容")["bullets"].append(_ppt_strip_inline(stripped))
        i += 1

    # 封面副标题: 取封面后、第一个标题前的第一段正文
    if cover_seen and slides and slides[0]["kind"] == "cover":
        for s in slides[1:]:
            if s["kind"] == "content":
                if s["bullets"]:
                    slides[0]["subtitle"] = s["bullets"][0].lstrip("• ‖ »  ").strip()
                break

    # 拆分要点过多的内容页
    out: list[dict] = []
    for s in slides:
        if s["kind"] != "content":
            out.append(s)
            continue
        bullets = s["bullets"]
        chunks = [bullets[k:k + _PPT_MAX_BULLETS] for k in range(0, len(bullets), _PPT_MAX_BULLETS)] or [[]]
        for idx, chunk in enumerate(chunks):
            title = s["title"] if idx == 0 else f"{s['title']}（续）"
            out.append({"kind": "content", "title": title, "bullets": chunk})
    return out


def _ppt_add_textbox(slide, left, top, width, height):
    return slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))


def _ppt_build(slides: list[dict], template: str = PPT_DEFAULT_TEMPLATE) -> bytes:
    theme = _ppt_theme(template)
    bg, accent = theme["bg"], theme["accent"]
    title_c, foot_c, sub_c = theme["title"], theme["footer"], theme["subtitle"]

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]
    from datetime import date

    for num, s in enumerate(slides, start=1):
        slide = prs.slides.add_slide(blank)

        # 整页背景色(按模板)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = bg

        # 页码(右下角, 封面除外), 颜色随模板页脚色
        if s["kind"] != "cover":
            tb = _ppt_add_textbox(slide, 12.4, 7.0, 0.7, 0.3)
            p = tb.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.RIGHT
            _ppt_set_run(p.add_run(), str(num), 12, color=foot_c)

        if s["kind"] == "cover":
            # 左侧强调竖条
            bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.0), Inches(0.0), Inches(0.18), Inches(7.5))
            bar.fill.solid(); bar.fill.fore_color.rgb = accent
            bar.line.fill.background()
            tb = _ppt_add_textbox(slide, 1.0, 2.7, 11.3, 1.6)
            p = tb.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.LEFT
            _ppt_set_run(p.add_run(), s["title"] or "演示文稿", 44, bold=True, color=title_c)
            if s.get("subtitle"):
                tb2 = _ppt_add_textbox(slide, 1.0, 4.3, 11.3, 0.7)
                p2 = tb2.text_frame.paragraphs[0]
                _ppt_set_run(p2.add_run(), s["subtitle"], 22, color=sub_c)
            tb3 = _ppt_add_textbox(slide, 1.0, 6.4, 11.3, 0.5)
            p3 = tb3.text_frame.paragraphs[0]
            _ppt_set_run(p3.add_run(), date.today().strftime("%Y / %m / %d"), 16, color=foot_c)

        elif s["kind"] == "section":
            tb = _ppt_add_textbox(slide, 1.0, 3.0, 11.3, 1.4)
            p = tb.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
            _ppt_set_run(p.add_run(), s["title"], 40, bold=True, color=title_c)
            bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(5.667), Inches(4.4), Inches(2.0), Inches(0.06))
            bar.fill.solid(); bar.fill.fore_color.rgb = accent
            bar.line.fill.background()

        else:  # content
            # 标题
            tb = _ppt_add_textbox(slide, 0.7, 0.5, 11.9, 0.9)
            p = tb.text_frame.paragraphs[0]
            _ppt_set_run(p.add_run(), s["title"], 30, bold=True, color=title_c)
            # 标题下强调短线
            bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.75), Inches(1.45), Inches(1.6), Inches(0.07))
            bar.fill.solid(); bar.fill.fore_color.rgb = accent
            bar.line.fill.background()
            # 要点
            bullets = s["bullets"]
            if bullets:
                bt = _ppt_add_textbox(slide, 0.9, 1.9, 11.4, 5.0)
                tf = bt.text_frame
                tf.word_wrap = True
                size = 20 if len(bullets) <= 5 else 18
                for j, b in enumerate(bullets):
                    para = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
                    para.space_after = PptPt(10)
                    para.line_spacing = 1.1
                    _ppt_set_run(para.add_run(), b, size, color=theme["body"])

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def markdown_to_pptx(md_text: str, template: str = PPT_DEFAULT_TEMPLATE) -> tuple[bytes, str]:
    """Markdown -> PPT(.pptx), 返回 (pptx 字节, 建议文件名)。template 指定配色模板。"""
    if template not in PPT_TEMPLATES:
        template = PPT_DEFAULT_TEMPLATE
    slides = _ppt_parse(md_text)
    data = _ppt_build(slides, template)
    if not data.startswith(b"PK"):
        raise RuntimeError("生成的 pptx 无效")
    return data, (extract_title(md_text) or "演示文稿") + ".pptx"


# 格式名 -> 处理函数, 页面通过它按格式分发, 扩展时在此登记即可
FORMATS: dict[str, object] = {
    "pdf": markdown_to_pdf,
    "word": markdown_to_word,
    "jpg": markdown_to_jpg,
    "png": markdown_to_png,
    "pptx": markdown_to_pptx,
}
