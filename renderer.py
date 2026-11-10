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
